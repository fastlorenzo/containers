"""Backup the XigmaNAS configuration to an S3-compatible bucket.

Logs into the XigmaNAS web GUI, downloads the encrypted configuration
backup (System > Backup Configuration), verifies that the payload
decrypts to valid configuration XML, uploads it to S3 and prunes old
backups beyond a retention count.

The container is a run-to-completion job: scheduling is external
(Kubernetes CronJob, systemd timer, ...). See README.md for the full
environment variable reference and exit codes.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_LOGIN = 3
EXIT_DOWNLOAD = 4
EXIT_VERIFY = 5
EXIT_UPLOAD = 6
EXIT_PRUNE = 7

BACKUP_KEY_RE = re.compile(r"config-[A-Za-z0-9._-]+-\d{14}\.gz")

log = logging.getLogger("xigmanas-backup")


class ConfigError(Exception):
    """Invalid or missing configuration."""


class LoginError(Exception):
    """Authentication against the XigmaNAS GUI failed."""


class DownloadError(Exception):
    """Fetching the backup (or the CSRF token) failed."""


class VerificationError(Exception):
    """The downloaded backup does not decrypt to valid configuration XML."""


class UploadError(Exception):
    """Uploading the backup to S3 failed."""


class PruneError(Exception):
    """Pruning old backups failed (the new backup was already uploaded)."""


def env(name: str, *, required: bool = False, default: str | None = None) -> str | None:
    """Read NAME_FILE (path to a mounted secret) or NAME from the environment."""
    file_var = f"{name}_FILE"
    path = os.environ.get(file_var)
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().rstrip("\n")
        except OSError as exc:
            raise ConfigError(f"{file_var}={path} could not be read: {exc}") from exc
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    if required:
        raise ConfigError(f"{name} (or {file_var}) is required")
    return default


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    if value.lower() in ("1", "true", "yes", "on"):
        return True
    if value.lower() in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"{name} must be a boolean, got {value!r}")


@dataclass
class Config:
    url: str
    username: str
    password: str
    encryption_password: str
    s3_endpoint_url: str | None
    s3_bucket: str | None
    s3_access_key_id: str | None
    s3_secret_access_key: str | None
    s3_prefix: str
    s3_region: str | None
    retention_count: int
    tls_verify: bool
    ca_bundle: str | None
    http_timeout: float
    dry_run: bool

    @property
    def s3_configured(self) -> bool:
        return all(
            (self.s3_endpoint_url, self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key)
        )


def load_config() -> Config:
    errors: list[str] = []

    def get(name: str, *, required: bool = False, default: str | None = None) -> str | None:
        try:
            return env(name, required=required, default=default)
        except ConfigError as exc:
            errors.append(str(exc))
            return None

    url = get("XIGMANAS_URL", required=True)
    username = get("XIGMANAS_USERNAME", required=True)
    password = get("XIGMANAS_PASSWORD", required=True)
    encryption_password = get("BACKUP_ENCRYPTION_PASSWORD", required=True)

    dry_run = False
    tls_verify = True
    try:
        dry_run = env_bool("DRY_RUN", False)
    except ConfigError as exc:
        errors.append(str(exc))
    try:
        tls_verify = env_bool("TLS_VERIFY", True)
    except ConfigError as exc:
        errors.append(str(exc))

    s3_endpoint_url = get("S3_ENDPOINT_URL", required=not dry_run)
    s3_bucket = get("S3_BUCKET", required=not dry_run)
    s3_access_key_id = get("S3_ACCESS_KEY_ID", required=not dry_run)
    s3_secret_access_key = get("S3_SECRET_ACCESS_KEY", required=not dry_run)

    prefix = get("S3_PREFIX", default="xigmanas/") or ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    retention_count = 8
    raw_retention = os.environ.get("RETENTION_COUNT", "8")
    try:
        retention_count = int(raw_retention)
        if retention_count < 0:
            raise ValueError
    except ValueError:
        errors.append(f"RETENTION_COUNT must be a non-negative integer, got {raw_retention!r}")

    http_timeout = 30.0
    raw_timeout = os.environ.get("HTTP_TIMEOUT", "30")
    try:
        http_timeout = float(raw_timeout)
        if http_timeout <= 0:
            raise ValueError
    except ValueError:
        errors.append(f"HTTP_TIMEOUT must be a positive number, got {raw_timeout!r}")

    ca_bundle = get("CA_BUNDLE")
    if ca_bundle and not os.path.isfile(ca_bundle):
        errors.append(f"CA_BUNDLE={ca_bundle} does not exist or is not a file")

    if url:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            errors.append(f"XIGMANAS_URL must be an http(s) URL, got {url!r}")

    if errors:
        raise ConfigError("; ".join(errors))

    assert url and username and password and encryption_password
    return Config(
        url=url.rstrip("/"),
        username=username,
        password=password,
        encryption_password=encryption_password,
        s3_endpoint_url=s3_endpoint_url,
        s3_bucket=s3_bucket,
        s3_access_key_id=s3_access_key_id,
        s3_secret_access_key=s3_secret_access_key,
        s3_prefix=prefix,
        s3_region=get("S3_REGION"),
        retention_count=retention_count,
        tls_verify=tls_verify,
        ca_bundle=ca_bundle,
        http_timeout=http_timeout,
        dry_run=dry_run,
    )


def make_session(cfg: Config):
    import requests

    session = requests.Session()
    if cfg.ca_bundle:
        session.verify = cfg.ca_bundle
    elif not cfg.tls_verify:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session.verify = False
        log.warning("TLS_VERIFY=false: NAS certificate verification is DISABLED")
    return session


def login(session, cfg: Config) -> None:
    """Authenticate against login.php; success is a redirect away from it."""
    resp = session.post(
        f"{cfg.url}/login.php",
        data={"username": cfg.username, "password": cfg.password},
        timeout=cfg.http_timeout,
        allow_redirects=False,
    )
    location = resp.headers.get("Location", "")
    if resp.status_code in (301, 302, 303, 307) and "login.php" not in location:
        log.info("logged in to %s as %s", cfg.url, cfg.username)
        return
    if resp.status_code == 200:
        raise LoginError("login.php re-rendered the login form: wrong username or password?")
    raise LoginError(f"unexpected login response: HTTP {resp.status_code} Location={location!r}")


def fetch_authtoken(session, cfg: Config) -> str:
    """Read the CSRF authtoken hidden field from the backup page."""
    resp = session.get(
        f"{cfg.url}/system_backup.php", timeout=cfg.http_timeout, allow_redirects=False
    )
    if resp.status_code in (301, 302, 303, 307):
        raise DownloadError(
            f"system_backup.php redirected to {resp.headers.get('Location')!r}: session not accepted"
        )
    resp.raise_for_status()
    match = re.search(
        r'<input[^>]*name="authtoken"[^>]*value="([^"]+)"', resp.text
    ) or re.search(r'<input[^>]*value="([^"]+)"[^>]*name="authtoken"', resp.text)
    if not match:
        raise DownloadError("no authtoken field found on system_backup.php")
    return match.group(1)


def download_backup(session, cfg: Config, authtoken: str) -> tuple[bytes, str | None]:
    """POST the backup form; returns (payload, server-suggested filename)."""
    resp = session.post(
        f"{cfg.url}/system_backup.php",
        files={
            "authtoken": (None, authtoken),
            "submit": (None, "download"),
            "encryption": (None, "yes"),
            "encrypt_password": (None, cfg.encryption_password),
            "encrypt_password_confirm": (None, cfg.encryption_password),
        },
        timeout=cfg.http_timeout,
        allow_redirects=False,
    )
    content_type = resp.headers.get("Content-Type", "")
    disposition = resp.headers.get("Content-Disposition", "")
    if resp.status_code != 200 or not (
        "application/octet-stream" in content_type or "attachment" in disposition
    ):
        preview = resp.text[:200].replace("\n", " ")
        raise DownloadError(
            f"expected a file download, got HTTP {resp.status_code} "
            f"Content-Type={content_type!r}: {preview}"
        )
    filename = None
    fn_match = re.search(r'filename="?([^";]+)', disposition)
    if fn_match:
        filename = fn_match.group(1)
    log.info("downloaded backup: %d bytes, filename=%s", len(resp.content), filename)
    return resp.content, filename


def _evp_bytes_to_key(password: bytes, salt: bytes, length: int) -> bytes:
    """OpenSSL EVP_BytesToKey with MD5 and one round, as used by XigmaNAS."""
    material = b""
    digest = b""
    while len(material) < length:
        digest = hashlib.md5(digest + password + salt).digest()
        material += digest
    return material[:length]


def verify_backup(blob: bytes, password: str) -> None:
    """Decrypt the backup in-process; raise VerificationError on any mismatch.

    Format (see XigmaNAS config_encrypt): gzip(base64(openssl-salted
    AES-256-CBC(config.xml))).
    """
    try:
        armored = gzip.decompress(blob)
    except (OSError, EOFError) as exc:
        raise VerificationError(f"gunzip: payload is not valid gzip data ({exc})") from exc
    try:
        raw = base64.b64decode(armored)
    except (binascii.Error, ValueError) as exc:
        raise VerificationError(f"base64: payload is not base64-armored ({exc})") from exc
    if len(raw) < 32 or raw[:8] != b"Salted__":
        raise VerificationError("magic: missing OpenSSL 'Salted__' header")
    salt = raw[8:16]
    ciphertext = raw[16:]
    if len(ciphertext) % 16 != 0:
        raise VerificationError("cipher: ciphertext length is not a multiple of the block size")

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    material = _evp_bytes_to_key(password.encode("utf-8"), salt, 48)
    key, iv = material[:32], material[32:48]
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    pad = plaintext[-1] if plaintext else 0
    if not 1 <= pad <= 16 or plaintext[-pad:] != bytes([pad]) * pad:
        raise VerificationError("padding: bad PKCS#7 padding (wrong encryption password?)")
    document = plaintext[:-pad]

    if not document.lstrip().startswith(b"<?xml"):
        raise VerificationError("xml: decrypted data does not start with an XML declaration")
    try:
        root = ET.fromstring(document)
    except ET.ParseError as exc:
        raise VerificationError(f"xml: decrypted data is not well-formed XML ({exc})") from exc
    if root.tag not in ("xigmanas", "nas4free"):
        raise VerificationError(f"xml: unexpected root element <{root.tag}>")
    log.info("backup verified: decrypts to <%s> configuration XML", root.tag)


def object_key(cfg: Config, server_filename: str | None) -> str:
    if server_filename and BACKUP_KEY_RE.fullmatch(server_filename):
        name = server_filename
    else:
        host = urlparse(cfg.url).hostname or "xigmanas"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        name = f"config-{host}-{stamp}.gz"
    return f"{cfg.s3_prefix}{name}"


def make_s3(cfg: Config):
    import boto3
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint_url,
        region_name=cfg.s3_region or None,
        aws_access_key_id=cfg.s3_access_key_id,
        aws_secret_access_key=cfg.s3_secret_access_key,
        config=BotoConfig(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60,
        ),
    )


def upload(s3, cfg: Config, blob: bytes, key: str) -> str:
    digest = hashlib.sha256(blob).hexdigest()
    try:
        s3.put_object(
            Bucket=cfg.s3_bucket,
            Key=key,
            Body=blob,
            ContentType="application/octet-stream",
            Metadata={"sha256": digest},
        )
    except Exception as exc:
        raise UploadError(f"put_object s3://{cfg.s3_bucket}/{key} failed: {exc}") from exc
    log.info("uploaded s3://%s/%s (%d bytes, sha256=%s)", cfg.s3_bucket, key, len(blob), digest)
    return digest


def list_backups(s3, cfg: Config) -> list[dict]:
    """All objects under the prefix that look like our backups, newest first."""
    key_re = re.compile(rf"^{re.escape(cfg.s3_prefix)}{BACKUP_KEY_RE.pattern}$")
    objects = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cfg.s3_bucket, Prefix=cfg.s3_prefix):
        for obj in page.get("Contents", []):
            if key_re.match(obj["Key"]):
                objects.append(obj)
    objects.sort(key=lambda o: (o["LastModified"], o["Key"]), reverse=True)
    return objects


def prune(s3, cfg: Config, just_uploaded_key: str) -> tuple[int, int]:
    """Keep the newest retention_count backups; returns (kept, deleted)."""
    if cfg.retention_count == 0:
        log.info("RETENTION_COUNT=0: pruning disabled")
        return 0, 0
    try:
        objects = list_backups(s3, cfg)
        stale = [
            o for o in objects[cfg.retention_count :] if o["Key"] != just_uploaded_key
        ]
        for chunk_start in range(0, len(stale), 1000):
            chunk = stale[chunk_start : chunk_start + 1000]
            s3.delete_objects(
                Bucket=cfg.s3_bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in chunk], "Quiet": True},
            )
            for obj in chunk:
                log.info("pruned s3://%s/%s (%s)", cfg.s3_bucket, obj["Key"], obj["LastModified"])
    except Exception as exc:
        raise PruneError(f"pruning old backups failed: {exc}") from exc
    return len(objects) - len(stale), len(stale)


def run(cfg: Config) -> int:
    session = make_session(cfg)
    try:
        try:
            login(session, cfg)
        except LoginError:
            raise
        except Exception as exc:
            raise LoginError(f"login request failed: {exc}") from exc

        try:
            authtoken = fetch_authtoken(session, cfg)
            blob, server_filename = download_backup(session, cfg, authtoken)
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(f"backup download failed: {exc}") from exc
    finally:
        session.close()

    verify_backup(blob, cfg.encryption_password)
    key = object_key(cfg, server_filename)

    if cfg.dry_run:
        bucket = cfg.s3_bucket or "<bucket>"
        log.info("DRY_RUN: would upload %d bytes as s3://%s/%s", len(blob), bucket, key)
        if cfg.s3_configured:
            s3 = make_s3(cfg)
            objects = list_backups(s3, cfg)
            stale = objects[cfg.retention_count :] if cfg.retention_count else []
            for obj in stale:
                log.info("DRY_RUN: would prune s3://%s/%s", cfg.s3_bucket, obj["Key"])
            log.info(
                "DRY_RUN: %d existing backups, %d would be pruned", len(objects), len(stale)
            )
        else:
            log.info("DRY_RUN: S3 not configured, skipping bucket inspection")
        return EXIT_OK

    s3 = make_s3(cfg)
    upload(s3, cfg, blob, key)
    try:
        kept, deleted = prune(s3, cfg, key)
    except PruneError:
        log.error("backup WAS uploaded successfully to s3://%s/%s", cfg.s3_bucket, key)
        raise
    log.info(
        "backup complete: s3://%s/%s (%d bytes, %d kept, %d pruned)",
        cfg.s3_bucket,
        key,
        len(blob),
        kept,
        deleted,
    )
    return EXIT_OK


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        cfg = load_config()
    except ConfigError as exc:
        log.error("configuration error: %s", exc)
        return EXIT_CONFIG

    try:
        return run(cfg)
    except LoginError as exc:
        log.error("login failed: %s", exc)
        return EXIT_LOGIN
    except DownloadError as exc:
        log.error("download failed: %s", exc)
        return EXIT_DOWNLOAD
    except VerificationError as exc:
        log.error("verification failed, nothing uploaded: %s", exc)
        return EXIT_VERIFY
    except UploadError as exc:
        log.error("upload failed: %s", exc)
        return EXIT_UPLOAD
    except PruneError as exc:
        log.error("prune failed: %s", exc)
        return EXIT_PRUNE


if __name__ == "__main__":
    sys.exit(main())
