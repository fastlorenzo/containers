"""HTTP surface: OpenAPI for Open WebUI, MCP for OpenClaw.

The same three operations are exposed over two protocols because the two
consumers speak different ones — Open WebUI registers OpenAPI tool servers,
OpenClaw registers MCP servers.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from . import vault
from .config import INBOX_DIR, Config
from .state import State
from .webui import WebUIClient

LOG = logging.getLogger("obsidian-bridge.server")

# Routes reachable without the bearer token. Everything else — capture and the
# whole MCP surface — is authenticated, since the service is exposed through
# the LAN gateway for Open WebUI's benefit.
_PUBLIC_PATHS = frozenset({"/healthz", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"})


class Runtime:
    """Process-wide handles the request handlers need."""

    def __init__(self) -> None:
        self.cfg: Config | None = None
        self.client: WebUIClient | None = None
        self.state: State | None = None

    def require(self) -> tuple[Config, WebUIClient, State]:
        if self.cfg is None or self.client is None or self.state is None:
            raise HTTPException(status_code=503, detail="bridge is still starting")
        return self.cfg, self.client, self.state


RUNTIME = Runtime()
mcp = FastMCP(name="second-brain", stateless_http=True, streamable_http_path="/")


class CaptureRequest(BaseModel):
    title: str = Field(description="Short title for the note.")
    content: str = Field(description="Markdown body of the note.")
    source_url: str | None = Field(
        default=None, description="Optional URL this was captured from."
    )


class CaptureResponse(BaseModel):
    path: str
    created: bool


async def _resolve_kid(client: WebUIClient, state: State, name: str) -> str:
    """Find a collection id by name without creating it.

    Never creates: a typo'd collection name from a tool call should be an
    error, not a new empty collection that silently returns nothing.
    """
    entry = state.collections.get(name)
    if entry and entry.kid and entry.kid != "dry-run":
        return entry.kid

    for candidate in await client.list_knowledge():
        if candidate.get("name") == name:
            return str(candidate["id"])

    raise ValueError(f"no collection named {name!r}")


def _capture(cfg: Config, title: str, content: str, source_url: str | None) -> str:
    """Write a new note to the Inbox. Never edits an existing file.

    The vault's two-writer rule keeps Alix and the user from clobbering each
    other; capture stays inside it by only ever creating.
    """
    now = datetime.now(tz=timezone.utc)
    slug = vault.slugify(title)
    relpath = vault.unique_path(cfg.vault_path, f"{INBOX_DIR}/{now.date().isoformat()} {slug}.md")

    front = [
        "---",
        "type: capture",
        f"created: {now.date().isoformat()}",
        "tags: [capture, inbox]",
    ]
    if source_url:
        front.append(f"source: {source_url}")
    front += ["---", "", f"# {title.strip()}", "", content.strip(), ""]

    vault.write_note(cfg.vault_path, relpath, "\n".join(front))
    LOG.info("captured %s", relpath)
    return relpath


# -- MCP tools -------------------------------------------------------------


@mcp.tool()
async def second_brain_search(
    query: str,
    k: int = 6,
    collection: str = "",
) -> list[dict[str, Any]]:
    """Search the second brain and return matching notes with their vault paths.

    Defaults to curated notes. Pass the conversations collection to search
    past chat transcripts instead — those record what was said, not what is
    known, and should be cited as such.
    """
    cfg, client, state = RUNTIME.require()
    name = collection or cfg.collection_vault
    kid = await _resolve_kid(client, state, name)

    payload = await client.query_collection(kid, query, k=max(k * 2, 8), k_reranker=k)

    documents = (payload.get("documents") or [[]])[0]
    metadatas = (payload.get("metadatas") or [[]])[0]
    distances = (payload.get("distances") or [[]])[0]

    results: list[dict[str, Any]] = []
    for index, text in enumerate(documents):
        meta = metadatas[index] if index < len(metadatas) else {}
        name_field = ""
        if isinstance(meta, dict):
            name_field = str(meta.get("name") or meta.get("source") or "")
        results.append(
            {
                "path": name_field.replace("__", "/"),
                "score": distances[index] if index < len(distances) else None,
                "content": text,
                "collection": name,
            }
        )
    return results


@mcp.tool()
async def second_brain_read(path: str) -> str:
    """Read a whole note from the vault by its vault-relative path.

    Search returns chunks; this returns the entire note. Use it to follow a
    link by name or to read a note that was split across chunks.
    """
    cfg, _, _ = RUNTIME.require()
    try:
        full = vault.resolve_in_vault(cfg.vault_path, path)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if not os.path.isfile(full):
        raise ValueError(f"no such note: {path!r}")
    with open(full, encoding="utf-8", errors="replace") as handle:
        return handle.read()


@mcp.tool()
async def second_brain_capture(title: str, content: str, source_url: str = "") -> str:
    """Save a new note to the Inbox for later triage. Returns its vault path."""
    cfg, _, _ = RUNTIME.require()
    return _capture(cfg, title, content, source_url or None)


# -- HTTP app --------------------------------------------------------------


def create_app(lifespan: Any) -> FastAPI:
    app = FastAPI(
        title="Second Brain Bridge",
        description="Search and capture against Lorenzo's Obsidian vault.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def require_token(request: Request, call_next: Any) -> Any:
        cfg = RUNTIME.cfg
        if request.url.path in _PUBLIC_PATHS or cfg is None or not cfg.capture_token:
            return await call_next(request)

        header = request.headers.get("authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if token != cfg.capture_token:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/capture", response_model=CaptureResponse, operation_id="capture_note")
    async def capture(payload: CaptureRequest = Body(...)) -> CaptureResponse:
        """Save a note to the second brain's Inbox for later triage."""
        cfg, _, _ = RUNTIME.require()
        relpath = _capture(cfg, payload.title, payload.content, payload.source_url)
        return CaptureResponse(path=relpath, created=True)

    app.mount("/mcp", mcp.streamable_http_app())
    return app
