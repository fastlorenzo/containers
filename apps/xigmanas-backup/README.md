# xigmanas-backup

Run-to-completion job that backs up a [XigmaNAS](https://www.xigmanas.com/)
configuration to an S3-compatible bucket. On each run it:

1. Logs into the XigmaNAS web GUI (`login.php`).
2. Fetches the CSRF token from `system_backup.php` and requests an
   **encrypted** configuration backup (same as System > Backup Configuration
   with *Enable encryption* checked).
3. Verifies the download in-process: gunzip, base64-decode, AES-256-CBC
   decrypt with the encryption password, and parses the result as
   configuration XML. A corrupt or wrongly-encrypted backup is never uploaded.
4. Uploads the (still encrypted) backup to S3 with a `sha256` metadata tag.
5. Prunes old backups under the prefix, keeping the newest `RETENTION_COUNT`.

Scheduling is external: run it from a Kubernetes CronJob, systemd timer or
host cron. The container exits non-zero on failure.

## Environment variables

Every secret variable also accepts a `*_FILE` variant pointing at a mounted
file (takes precedence over the plain variable).

| Variable | Required | Default | Description |
|---|---|---|---|
| `XIGMANAS_URL` | yes | — | Base URL of the GUI, e.g. `https://nas.example.com` |
| `XIGMANAS_USERNAME` / `_FILE` | yes | — | GUI admin username |
| `XIGMANAS_PASSWORD` / `_FILE` | yes | — | GUI admin password |
| `BACKUP_ENCRYPTION_PASSWORD` / `_FILE` | yes | — | Config encryption password; also used to verify the download |
| `S3_ENDPOINT_URL` | yes¹ | — | S3-compatible endpoint, e.g. `https://s3.eu-central-003.backblazeb2.com` |
| `S3_BUCKET` | yes¹ | — | Bucket name |
| `S3_ACCESS_KEY_ID` / `_FILE` | yes¹ | — | Access key |
| `S3_SECRET_ACCESS_KEY` / `_FILE` | yes¹ | — | Secret key |
| `S3_PREFIX` | no | `xigmanas/` | Key prefix (normalized to end with `/`) |
| `S3_REGION` | no | — | Region, if the endpoint needs one |
| `RETENTION_COUNT` | no | `8` | Newest N backups to keep; `0` disables pruning |
| `TLS_VERIFY` | no | `true` | `false` disables NAS certificate verification (warning logged) |
| `CA_BUNDLE` | no | — | Path to a mounted PEM bundle for the NAS certificate |
| `HTTP_TIMEOUT` | no | `30` | Timeout in seconds for every NAS request |
| `DRY_RUN` | no | `false` | Login, download and verify only; log what would be uploaded/pruned |
| `LOG_LEVEL` | no | `INFO` | Python logging level |

¹ Optional when `DRY_RUN=true`.

Pruning only ever touches keys matching `<prefix>config-*-YYYYmmddHHMMSS.gz`;
anything else under the prefix is left alone.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (including dry run) |
| `2` | Configuration error (missing/invalid environment variables) |
| `3` | GUI login failed |
| `4` | Backup download (or CSRF token fetch) failed |
| `5` | Verification failed — nothing was uploaded |
| `6` | S3 upload failed |
| `7` | Pruning failed (the new backup **was** uploaded) |

## Usage

### docker run (dry run)

```sh
docker run --rm --read-only --tmpfs /tmp \
    -e DRY_RUN=true \
    -e XIGMANAS_URL=https://nas.example.com \
    -e XIGMANAS_USERNAME=admin \
    -e XIGMANAS_PASSWORD=... \
    -e BACKUP_ENCRYPTION_PASSWORD=... \
    ghcr.io/fastlorenzo/xigmanas-backup:0.1.0
```

### docker compose

```yaml
services:
  xigmanas-backup:
    image: ghcr.io/fastlorenzo/xigmanas-backup:0.1.0
    read_only: true
    tmpfs: [/tmp]
    environment:
      XIGMANAS_URL: https://nas.example.com
      S3_ENDPOINT_URL: https://s3.eu-central-003.backblazeb2.com
      S3_BUCKET: my-backup-bucket
      RETENTION_COUNT: "8"
      XIGMANAS_USERNAME_FILE: /run/secrets/nas_username
      XIGMANAS_PASSWORD_FILE: /run/secrets/nas_password
      BACKUP_ENCRYPTION_PASSWORD_FILE: /run/secrets/enc_password
      S3_ACCESS_KEY_ID_FILE: /run/secrets/s3_access_key
      S3_SECRET_ACCESS_KEY_FILE: /run/secrets/s3_secret_key
    secrets: [nas_username, nas_password, enc_password, s3_access_key, s3_secret_key]
```

Schedule it with host cron / a systemd timer (`docker compose run --rm xigmanas-backup`).

### Kubernetes CronJob (condensed)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: xigmanas-backup
spec:
  schedule: "30 3 * * 0"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 900
      template:
        spec:
          restartPolicy: Never
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 65534
            runAsGroup: 65534
            seccompProfile: {type: RuntimeDefault}
          containers:
            - name: xigmanas-backup
              image: ghcr.io/fastlorenzo/xigmanas-backup:0.1.0
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: true
                capabilities: {drop: ["ALL"]}
              envFrom:
                - secretRef: {name: xigmanas-backup-secret}
              env:
                - {name: XIGMANAS_URL, value: "https://nas.example.com"}
                - {name: S3_ENDPOINT_URL, value: "https://s3.eu-central-003.backblazeb2.com"}
                - {name: S3_BUCKET, value: "my-backup-bucket"}
              volumeMounts:
                - {name: tmp, mountPath: /tmp}
          volumes:
            - name: tmp
              emptyDir: {medium: Memory, sizeLimit: 64Mi}
```

## TLS to the NAS

Prefer a proper certificate on the NAS. If it uses a private CA, mount the CA
bundle and set `CA_BUNDLE=/path/to/ca.pem`. `TLS_VERIFY=false` is a last
resort — the admin password would be sent over an unverified connection.

## Restoring / manual decryption

Backups are stored exactly as XigmaNAS produces them, so they can be restored
directly via System > Restore Configuration. To inspect one manually:

```sh
gunzip -c config-nas.example.com-20260718030000.gz \
    | openssl enc -d -aes-256-cbc -a -md md5 -pass pass:<encryption-password>
```
