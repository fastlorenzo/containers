# zguard-basic

An Istio ext-authz service that enforces HTTP Basic authentication per host.

## Overview

`zguard-basic` is a FastAPI service used as an Istio `extensionProvider` (via
`AuthorizationPolicy` `action: CUSTOM`). The gateway forwards the original
`Authorization` header and the original host, and the service validates the
Basic credentials against a per-host list of htpasswd-style entries.

## Features

- **Per-host credentials**: each host maps to its own list of `user:hash` entries.
- **htpasswd-compatible hashes**: bcrypt (`$2y$`/`$2b$`/`$2a$`), `{SHA}`, and plaintext.
- **Browser challenge**: returns `401` + `WWW-Authenticate` on failure.

## Configuration

Mount a JSON file at `/config/credentials.json` (env `CREDS_FILE`):

```json
{
  "mimir.bernardi.online": ["k8s-home:$2y$05$…", "admin:{SHA}…"],
  "prom-rw.bernardi.online": ["k8s-home:$2y$05$…"]
}
```

The file is reloaded on change (mtime), so credentials can be updated without a
restart.

## API Endpoints

- `GET /healthz` — liveness/readiness probe.
- `/{path}` (all methods) — ext-authz check; returns `200` (allow) or `401`
  (deny with `WWW-Authenticate`).
