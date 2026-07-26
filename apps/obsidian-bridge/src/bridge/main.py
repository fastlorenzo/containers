"""Entry point: periodic sync loop plus the HTTP/MCP surface."""

import argparse
import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from .chats import export_chats
from .config import Config, load_config
from .state import load_state, save_state
from .sync import sync_all
from .webui import WebUIClient

LOG = logging.getLogger("obsidian-bridge")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
        stream=sys.stdout,
    )


async def run_once(cfg: Config, client: WebUIClient, state: Any) -> None:
    # Chats land in the vault first, so the export has to precede the walk
    # that uploads them. Dry runs skip it: it is purely a write path.
    if cfg.export_chats and not cfg.dry_run:
        await export_chats(client, cfg, state)
        save_state(cfg.state_path, state)
    await sync_all(client, cfg, state)


async def sync_loop(cfg: Config, client: WebUIClient, state: Any) -> None:
    """Run passes forever, surviving individual failures.

    A pass that raises must not kill the loop: the vault keeps changing and
    the next pass re-derives everything it needs from content hashes.
    """
    while True:
        try:
            await run_once(cfg, client, state)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive across bad passes
            LOG.exception("sync pass failed")
        await asyncio.sleep(cfg.sync_interval)


def build_app(cfg: Config) -> Any:
    from .server import RUNTIME, create_app, mcp

    RUNTIME.cfg = cfg

    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        client = WebUIClient(cfg.webui_url, cfg.webui_key, max_retries=cfg.max_retries)
        state = load_state(cfg.state_path)
        RUNTIME.client, RUNTIME.state = client, state

        # FastMCP's streamable-HTTP transport needs its session manager
        # running for the mounted app to serve anything.
        async with mcp.session_manager.run():
            task = asyncio.create_task(sync_loop(cfg, client, state))
            try:
                yield
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                await client.aclose()

    return create_app(lifespan)


def main() -> None:
    parser = argparse.ArgumentParser(prog="obsidian-bridge")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single sync pass and exit (no HTTP server)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without calling Open WebUI or writing the vault",
    )
    args = parser.parse_args()

    setup_logging()
    cfg = load_config(require_webui=not args.dry_run)
    if args.dry_run:
        cfg.dry_run = True

    if args.once or cfg.dry_run:
        asyncio.run(_run_once_standalone(cfg))
        return

    import uvicorn

    uvicorn.run(build_app(cfg), host=cfg.bind_host, port=cfg.bind_port, log_config=None)


async def _run_once_standalone(cfg: Config) -> None:
    client = WebUIClient(cfg.webui_url, cfg.webui_key, max_retries=cfg.max_retries)
    state = load_state(cfg.state_path)
    try:
        await run_once(cfg, client, state)
    finally:
        await client.aclose()


if __name__ == "__main__":
    main()
