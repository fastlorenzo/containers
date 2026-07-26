"""Configuration for the Obsidian <-> Open WebUI bridge.

Import-safe: no environment reads or side effects happen at import time.
All configuration parsing happens inside load_config().
"""

import os
from dataclasses import dataclass, field

# Vault-relative directories that never reach any collection: Obsidian's own
# state, deleted notes, unrendered Templater sources, and runbook drafts.
DEFAULT_EXCLUDES = (
    ".obsidian",
    ".trash",
    "Templates",
    "4. Projects/Runbooks/drafts",
)

# Agent plumbing. Excluded from the curated collection wholesale; the
# transcript subdirectories below are routed to the conversations collection
# instead. Keep in sync with "8. OpenClaw/README.md" in the vault.
AGENT_NAMESPACE = "8. OpenClaw"

# Transcript sources, one per producer. Both land in the conversations
# collection; the subdirectory name becomes the `source` frontmatter key.
TRANSCRIPT_DIRS = (
    f"{AGENT_NAMESPACE}/sessions/openclaw",
    f"{AGENT_NAMESPACE}/sessions/webui",
)

# Where Open WebUI chat exports are written before the sync loop picks them up.
WEBUI_SESSIONS_DIR = f"{AGENT_NAMESPACE}/sessions/webui"

# Quick capture. The Guide defines this as "Unsorted. Emptied weekly."
INBOX_DIR = "0. Inbox"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_sources(name: str) -> tuple[tuple[str, str], ...]:
    """Parse `Collection Name=/abs/path` entries, one per line or comma."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return ()

    sources = []
    for chunk in raw.replace(",", "\n").splitlines():
        entry = chunk.strip()
        if not entry:
            continue
        collection, sep, path = entry.partition("=")
        if not sep or not collection.strip() or not path.strip():
            raise SystemExit(f"{name} entries must be 'Collection=/abs/path', got {entry!r}")
        sources.append((collection.strip(), path.strip()))
    return tuple(sources)


@dataclass
class Config:
    vault_path: str
    state_path: str

    webui_url: str
    webui_key: str

    collection_vault: str
    collection_conversations: str

    sync_interval: int
    upload_delay_ms: int
    max_retries: int

    export_chats: bool
    chat_min_turns: int
    transcript_retention_days: int

    capture_token: str
    bind_host: str
    bind_port: int

    dry_run: bool
    # Markdown trees outside the vault that should also be searchable, as
    # (collection name, absolute path). OpenClaw's qmd indexed the infra repo's
    # docs/ alongside the vault, so dropping qmd without this would silently
    # lose that source.
    extra_sources: tuple[tuple[str, str], ...] = ()
    excludes: tuple[str, ...] = field(default=DEFAULT_EXCLUDES)


def load_config(*, require_webui: bool = True) -> Config:
    """Build config from the environment.

    `require_webui` is relaxed for dry runs, which render the vault locally
    and never call Open WebUI, so they need no credentials.
    """
    webui_url = os.environ.get("WEBUI_URL", "").rstrip("/")
    if not webui_url and require_webui:
        raise SystemExit("WEBUI_URL is required")

    webui_key = os.environ.get("WEBUI_KEY", "")
    if not webui_key and require_webui:
        raise SystemExit("WEBUI_KEY is required (Open WebUI > Settings > Account > API keys)")

    return Config(
        vault_path=os.environ.get("VAULT_PATH", "/home/node/.openclaw/workspace/obsidian"),
        state_path=os.environ.get(
            # Deliberately outside the vault: anything under VAULT_PATH is
            # replicated to every Obsidian device by `ob sync --continuous`,
            # and two syncers sharing a state file would fight over file ids.
            "STATE_PATH",
            "/home/node/.openclaw/state/obsidian-bridge/state.json",
        ),
        webui_url=webui_url,
        webui_key=webui_key,
        collection_vault=os.environ.get("COLLECTION_VAULT", "Second Brain"),
        collection_conversations=os.environ.get("COLLECTION_CONVERSATIONS", "Conversations"),
        sync_interval=_env_int("SYNC_INTERVAL", 900),
        # Open WebUI embeds synchronously on file/add, one request per file,
        # and the open-webui gateway key is capped at rpm 120. 600ms between
        # uploads keeps a full 529-note pass under that ceiling.
        upload_delay_ms=_env_int("UPLOAD_DELAY_MS", 600),
        max_retries=_env_int("MAX_RETRIES", 5),
        export_chats=_env_bool("EXPORT_CHATS", True),
        chat_min_turns=_env_int("CHAT_MIN_TURNS", 4),
        transcript_retention_days=_env_int("TRANSCRIPT_RETENTION_DAYS", 90),
        capture_token=os.environ.get("BRAIN_CAPTURE_TOKEN", ""),
        bind_host=os.environ.get("BIND_HOST", "0.0.0.0"),
        bind_port=_env_int("BIND_PORT", 8770),
        dry_run=_env_bool("DRY_RUN", False),
        extra_sources=_env_sources("EXTRA_SOURCES"),
    )
