"""Export Open WebUI chats into the vault as transcripts.

Written into `8. OpenClaw/sessions/webui/`, from where the normal sync pass
picks them up like any other note — there is no separate ingestion path. The
vault stays the one durable store, so `ob sync --continuous` carries chats to
every Obsidian device alongside everything else.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from . import vault
from .config import WEBUI_SESSIONS_DIR, Config
from .state import State
from .webui import WebUIClient

LOG = logging.getLogger("obsidian-bridge.chats")

_ROLE_HEADINGS = {"user": "🧑 User", "assistant": "🤖 Assistant", "system": "⚙️ System"}

# Guards against a malformed parent chain looping forever.
_MAX_DEPTH = 10_000


def _as_datetime(value: Any) -> datetime | None:
    """Open WebUI has used both seconds and milliseconds for these fields."""
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    seconds = value / 1000 if value > 1e11 else value
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def active_messages(chat_body: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the conversation along the currently-selected branch.

    `history.messages` is a *tree* keyed by message id, with parentId and
    childrenIds — regenerating a reply adds a sibling rather than replacing
    it. Iterating the dict directly interleaves abandoned branches with the
    real conversation, so walk from the active leaf back to the root instead.
    """
    history = chat_body.get("history")
    if isinstance(history, dict):
        messages = history.get("messages")
        current_id = history.get("currentId")
        if isinstance(messages, dict) and messages:
            if current_id not in messages:
                # No active leaf recorded: fall back to the most recent message
                # that nothing else claims as a parent.
                parents = {
                    msg.get("parentId") for msg in messages.values() if isinstance(msg, dict)
                }
                leaves = [mid for mid in messages if mid not in parents]
                current_id = leaves[-1] if leaves else None

            chain: list[dict[str, Any]] = []
            seen: set[str] = set()
            node_id = current_id
            while node_id and node_id in messages and node_id not in seen:
                if len(chain) > _MAX_DEPTH:
                    LOG.warning("message chain exceeded %d nodes; truncating", _MAX_DEPTH)
                    break
                seen.add(node_id)
                node = messages[node_id]
                if isinstance(node, dict):
                    chain.append(node)
                node_id = node.get("parentId") if isinstance(node, dict) else None
            if chain:
                return list(reversed(chain))

    flat = chat_body.get("messages")
    return [m for m in flat if isinstance(m, dict)] if isinstance(flat, list) else []


def render_transcript(chat: dict[str, Any], messages: list[dict[str, Any]]) -> str:
    chat_body = chat.get("chat") if isinstance(chat.get("chat"), dict) else chat
    created = _as_datetime(chat.get("created_at"))
    updated = _as_datetime(chat.get("updated_at"))

    models = chat_body.get("models")
    if not isinstance(models, list):
        models = []

    front = [
        "---",
        "type: transcript",
        "source: open-webui",
        f"chat_id: {chat.get('id', '')}",
        f"title: {str(chat.get('title', 'Untitled')).replace(chr(10), ' ')}",
    ]
    if created:
        front.append(f"created: {created.date().isoformat()}")
    if updated:
        front.append(f"updated: {updated.date().isoformat()}")
    if models:
        front.append(f"models: {', '.join(str(m) for m in models)}")
    front += ["tags: [transcript, open-webui]", "---", ""]

    body: list[str] = []
    for message in messages:
        role = str(message.get("role", "")).lower()
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        heading = _ROLE_HEADINGS.get(role, role.title() or "Message")
        model = message.get("model")
        if role == "assistant" and model:
            heading = f"{heading} ({model})"
        body += [f"## {heading}", "", content.strip(), ""]

    return "\n".join(front + body).strip() + "\n"


def _transcript_relpath(chat: dict[str, Any]) -> str:
    stamp = _as_datetime(chat.get("created_at")) or _as_datetime(chat.get("updated_at"))
    date = (stamp or datetime.now(tz=timezone.utc)).date().isoformat()
    slug = vault.slugify(str(chat.get("title") or "Untitled"))
    return f"{WEBUI_SESSIONS_DIR}/{date} {slug}.md"


async def export_chats(client: WebUIClient, cfg: Config, state: State) -> int:
    """Write new/changed chats into the vault. Returns the number written."""
    try:
        summaries = await client.list_chats()
    except Exception as exc:  # noqa: BLE001 - export is best-effort, sync must still run
        LOG.warning("chat listing failed, skipping export: %s", exc)
        return 0

    written = 0
    for summary in summaries:
        chat_id = str(summary.get("id") or "")
        if not chat_id:
            continue

        updated_at = summary.get("updated_at") or 0
        known = state.chats.get(chat_id) or {}
        if known.get("updated_at") == updated_at and known.get("relpath"):
            continue

        try:
            chat = await client.get_chat(chat_id)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("could not fetch chat %s: %s", chat_id, exc)
            continue

        chat.setdefault("id", chat_id)
        chat.setdefault("title", summary.get("title"))
        chat.setdefault("created_at", summary.get("created_at"))
        chat.setdefault("updated_at", updated_at)

        chat_body = chat.get("chat") if isinstance(chat.get("chat"), dict) else chat
        messages = active_messages(chat_body)
        turns = sum(1 for m in messages if m.get("role") in ("user", "assistant"))
        if turns < cfg.chat_min_turns:
            LOG.debug("skipping chat %s: %d turns", chat_id, turns)
            # Remember it so a throwaway chat is not re-fetched every cycle.
            state.chats[chat_id] = {"updated_at": updated_at, "relpath": ""}
            continue

        relpath = _transcript_relpath(chat)
        previous = known.get("relpath")
        if previous and previous != relpath:
            # The chat was renamed; drop the stale file so the sync pass
            # removes it from the collection instead of leaving a duplicate.
            try:
                os.unlink(os.path.join(cfg.vault_path, previous))
            except OSError:
                pass

        content = render_transcript(chat, messages)
        if cfg.dry_run:
            LOG.info("[dry-run] would export chat %s -> %s", chat_id, relpath)
        else:
            vault.write_note(cfg.vault_path, relpath, content)

        state.chats[chat_id] = {"updated_at": updated_at, "relpath": relpath}
        written += 1

    if written:
        LOG.info("exported %d chat(s)", written)
    return written
