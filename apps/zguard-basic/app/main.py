"""Entry point for zguard-basic: an Istio ext-authz that enforces HTTP Basic
authentication per host.

Each protected host maps to a list of ``username:hash`` htpasswd-style entries
(see :file:`/config/credentials.json`). The gateway forwards the original
``authorization`` header and the original host (as ``X-Original-Host``) to this
service; on a valid match we return 200 (allow), otherwise 401 with a
``WWW-Authenticate`` challenge so browsers show the Basic Auth dialog.
"""

import base64
import hashlib
import hmac
import json
import os

import bcrypt
from fastapi import FastAPI, Request, Response

CREDS_FILE = os.getenv("CREDS_FILE", "/config/credentials.json")
REALM = os.getenv("REALM", "Authentication Required")

try:
    PORT = int(os.getenv("PORT", "8080"))
except ValueError:
    print("Invalid PORT environment variable; defaulting to 8080")
    PORT = 8080

app = FastAPI()

_creds: dict = {}
_creds_mtime: float | None = None


def load_creds() -> dict:
    """Load the host -> [user:hash] mapping, reloading on mtime change."""
    global _creds, _creds_mtime
    try:
        mtime = os.path.getmtime(CREDS_FILE)
    except OSError:
        return _creds
    if mtime == _creds_mtime:
        return _creds
    with open(CREDS_FILE, encoding="utf-8") as fh:
        _creds = json.load(fh)
    _creds_mtime = mtime
    return _creds


def _to_entries(host: str) -> dict[str, str]:
    """Normalise the list of ``username:hash`` strings for a host."""
    users: dict[str, str] = {}
    for entry in load_creds().get(host, []):
        username, sep, hsh = entry.partition(":")
        if not sep or not username:
            continue
        # Python's bcrypt expects the $2b$ prefix; $2y$ is PHP's alias.
        if hsh.startswith("$2y$"):
            hsh = "$2b$" + hsh[4:]
        users[username] = hsh
    return users


def _check_password(password: str, hsh: str) -> bool:
    if hsh.startswith("{SHA}"):
        digest = hashlib.sha1(password.encode("utf-8")).digest()
        return hmac.compare_digest(
            base64.b64encode(digest).decode(), hsh[len("{SHA}") :]
        )
    if hsh.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hsh.encode("utf-8"))
        except ValueError:
            return False
    # Plaintext fallback.
    return hmac.compare_digest(password, hsh)


def _verify(request: Request) -> bool:
    host = request.headers.get("x-original-host") or request.headers.get("host", "")
    host = host.split(":", 1)[0] if host else host
    entries = _to_entries(host)
    if not entries:
        # No credentials configured for this host. Deny closed by default.
        return False

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth[len("Basic ") :]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    username, sep, password = decoded.partition(":")
    if not sep:
        return False

    hsh = entries.get(username)
    if hsh is None:
        return False
    return _check_password(password, hsh)


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe."""
    return {"ok": True}


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
def ext_authz(request: Request, full_path: str):
    """Catch-all for the Istio ext-authz flow."""
    if _verify(request):
        return Response(status_code=200)
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{REALM}"'},
    )
