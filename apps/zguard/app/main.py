"""Entry point for the zguard application."""

import os
import ipaddress
import socket
import threading
import time
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import redis

TTL_SECONDS = int(os.getenv("TTL_SECONDS", "28800"))  # 8h default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CLIENT_IP_HEADER = "x-forwarded-for"
AUTHORIZED_DOMAIN = os.getenv("AUTHORIZED_DOMAIN", "localhost")
# Comma-separated hostnames (e.g. a dynamic-DNS name for home) whose current
# addresses are always allowed, with no sign-in. Re-resolved every
# TRUSTED_REFRESH_SECONDS so they follow a changing IP.
TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()]
TRUSTED_REFRESH_SECONDS = int(os.getenv("TRUSTED_REFRESH_SECONDS", "60"))

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


_trusted: dict[str, set[str]] = {}
_trusted_at = 0.0
_trusted_lock = threading.Lock()


def trusted_ips() -> set[str]:
    """
    Current addresses of TRUSTED_HOSTS, cached for TRUSTED_REFRESH_SECONDS.
    A host that fails to resolve keeps its last known addresses, so a DNS
    blip does not log everyone out.
    """
    global _trusted_at
    if not TRUSTED_HOSTS:
        return set()
    with _trusted_lock:
        if time.monotonic() - _trusted_at >= TRUSTED_REFRESH_SECONDS:
            for host in TRUSTED_HOSTS:
                try:
                    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
                    _trusted[host] = {
                        str(ipaddress.ip_address(i[4][0].split("%")[0])) for i in infos
                    }
                except (OSError, ValueError) as e:
                    print(f"Cannot resolve trusted host {host}: {e}")
            _trusted_at = time.monotonic()
        return set().union(*_trusted.values())


def is_allowed(ip: str) -> bool:
    """Trusted-host address, or whitelisted (sliding TTL refreshed)."""
    if ip in trusted_ips():
        return True
    if r.get(f"whitelist:{ip}"):
        # Optionally refresh TTL (“sliding window”):
        r.expire(f"whitelist:{ip}", TTL_SECONDS)
        return True
    return False


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
    """Check if the client IP is whitelisted or a trusted host's."""
    if is_allowed(get_client_ip(request)):
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


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
def check_ext_authz(request: Request, full_path: str):
    """
    Catch-all for the Istio ext-authz flow. The gateway forwards the original
    request method and path here (envoyExtAuthzHttp keeps both), so every
    method must be accepted: a GET-only route made FastAPI answer 405 to any
    POST/PUT/DELETE and Envoy relayed that as a deny to the client.
    On deny, redirect to /allow so the user can sign in
    (instead of the bare 401 the nginx auth-url expects from /check).
    """
    if is_allowed(get_client_ip(request)):
        return Response(status_code=200)

    # Original URL, provided by the gateway via
    # includeAdditionalHeadersInCheck: X-Auth-Request-Redirect.
    rd = request.headers.get("x-auth-request-redirect")
    if not rd:
        host = request.headers.get("host", "")
        rd = f"https://{host}/" if not full_path else f"https://{host}/{full_path}"

    signin = f"https://zguard.{AUTHORIZED_DOMAIN}/allow"
    if rd:
        signin += f"?{urlencode({'rd': rd})}"
    return RedirectResponse(url=signin, status_code=302)
