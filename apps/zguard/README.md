# ZGuard

A FastAPI-based IP whitelisting middleware service for Kubernetes ingress controllers.

## Overview

ZGuard provides a simple IP whitelisting service that integrates with OIDC authentication (like oauth2-proxy) to allow authenticated users to grant themselves temporary access to protected services. It uses Redis as a backend to store whitelisted IPs with configurable TTL.

## Features

- **IP Whitelisting**: Temporary IP-based access control
- **OIDC Integration**: Works with oauth2-proxy for authentication
- **Redis Backend**: Fast, distributed storage with TTL support
- **IPv4/IPv6 Support**: Handles both IP versions
- **Health Checks**: Built-in health monitoring
- **Configurable TTL**: Sliding window access expiration

## API Endpoints

### `GET /check`

Check if the client IP is whitelisted.

- **Returns**: 200 if whitelisted, 401 if not
- **Usage**: Called by ingress controller for access control

### `POST /allow`

Whitelist the client IP for the configured TTL period.

- **Returns**: 204 on success
- **Auth**: Must be behind OIDC authentication
- **Usage**: Allow authenticated users to grant themselves access

### `POST /disallow`

Remove the client IP from the whitelist.

- **Returns**: 204 on success
- **Auth**: Must be behind OIDC authentication
- **Usage**: Allow users to revoke their own access

### `GET /healthz`

Health check endpoint.

- **Returns**: JSON with status and timestamp
- **Usage**: Kubernetes health probes

## Configuration

Environment variables:

| Variable      | Default                    | Description                   |
| ------------- | -------------------------- | ----------------------------- |
| `TTL_SECONDS` | `28800` (8 hours)          | How long IPs stay whitelisted |
| `REDIS_URL`   | `redis://localhost:6379/0` | Redis connection URL          |

## Development

### Prerequisites

- Python 3.12+
- Redis server
- uv (recommended) or pip

### Running locally

1. **Setup virtual environment:**

   ```bash
   cd /path/to/zguard
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install "fastapi[standard]" redis
   ```

3. **Start Redis:**

   ```bash
   redis-server
   ```

4. **Run the application:**

   ```bash
   python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

Access the API at:

- Health check: <http://localhost:8000/healthz>
- Interactive docs: <http://localhost:8000/docs>

## Deployment

This service is designed to be deployed in Kubernetes with:

- Redis as a backend service
- oauth2-proxy for OIDC authentication
- Ingress controller integration for access control

See the `Dockerfile` for containerized deployment.

## Architecture

```text
User Request → Ingress → oauth2-proxy → ZGuard → Protected Service
                                    ↓
                                  Redis
```
