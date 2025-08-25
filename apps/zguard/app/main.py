"""Entry point for the zguard application."""

import os
import ipaddress
import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import redis

TTL_SECONDS = int(os.getenv("TTL_SECONDS", "28800"))  # 8h default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CLIENT_IP_HEADER = "x-forwarded-for"
AUTHORIZED_DOMAIN = os.getenv("AUTHORIZED_DOMAIN", "localhost")

try:
    PORT = int(os.getenv("PORT", "8080"))
except ValueError:
    print("Invalid PORT environment variable; defaulting to 8080")
    PORT = 8080

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI()


def get_client_ip(req: Request) -> str:
    """
    Use the first IP in X-Forwarded-For; fall back to peer
    """
    xff = req.headers.get(CLIENT_IP_HEADER)
    if xff:
        ip = xff.split(",")[0].strip()
    elif req.client and req.client.host:
        ip = req.client.host
    else:
        raise HTTPException(400, "Cannot determine client IP")
    ip = ip.split("%")[0]
    # Normalize (also handles IPv6)
    return str(ipaddress.ip_address(ip))


def is_authorized_redirect(url: str) -> bool:
    """
    Check if the redirect URL is authorized (same domain or subdomain).
    """
    if not AUTHORIZED_DOMAIN:
        return False

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return False

        # Allow exact domain match or subdomain
        return hostname == AUTHORIZED_DOMAIN or hostname.endswith(
            f".{AUTHORIZED_DOMAIN}"
        )
    except (ValueError, TypeError):
        return False


@app.get("/check")
def check(request: Request):
    """Check if the client IP is whitelisted."""
    ip = get_client_ip(request)
    if r.get(f"whitelist:{ip}"):
        # Optionally refresh TTL (“sliding window”):
        r.expire(f"whitelist:{ip}", TTL_SECONDS)
        return Response(status_code=200)
    # Tell ingress this needs signin; body can be empty
    return Response(status_code=401)


@app.get("/allow")
def allow(request: Request):
    """
    Allow the client IP to be whitelisted.
    This endpoint must be behind OIDC (oauth2-proxy) to ensure only
    authenticated users can grant themselves access.
    After whitelisting, redirects to the 'rd' parameter if provided and
    authorized.
    """
    ip = get_client_ip(request)
    r.setex(f"whitelist:{ip}", TTL_SECONDS, "1")

    # Check for redirect parameter
    rd = request.query_params.get("rd")
    if rd:
        if is_authorized_redirect(rd):
            return RedirectResponse(url=rd, status_code=302)
        else:
            raise HTTPException(400, "Unauthorized redirect domain")

    return Response(status_code=204)


@app.get("/disallow")
def disallow(request: Request):
    """
    Disallow the client IP from being whitelisted.
    This endpoint must be behind OIDC (oauth2-proxy) to ensure only
    authenticated users can revoke their access.
    """
    ip = get_client_ip(request)
    r.delete(f"whitelist:{ip}")
    return Response(status_code=204)


@app.get("/healthz")
def healthz():
    """
    Check the health of the application.
    """
    try:
        r.ping()
        return {"ok": True, "time": int(time.time())}
    except Exception as e:
        raise HTTPException(500, str(e)) from e
