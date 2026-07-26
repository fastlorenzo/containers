"""Vault -> Open WebUI knowledge collections.

Idempotent by content hash of the *rendered* document, so a change to the
preprocessing in markdown.py correctly invalidates every note rather than
leaving stale text in the index.
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field

from . import vault
from .config import AGENT_NAMESPACE, TRANSCRIPT_DIRS, Config
from .markdown import render_note
from .state import FileRecord, State, save_state
from .webui import WebUIClient

LOG = logging.getLogger("obsidian-bridge.sync")

# Prepended to every transcript. Retrieval returns a fragment stripped of its
# collection, so the provenance has to travel inside the text where the model
# actually reads it.
TRANSCRIPT_BANNER = (
    "> Conversation transcript. A record of what was said, not curated "
    "knowledge — do not treat statements here as established fact."
)

# Persist every N changes: often enough that a crash costs little rework,
# rarely enough to avoid rewriting the whole state file per note.
_CHECKPOINT_EVERY = 25


@dataclass
class CollectionSpec:
    name: str
    description: str
    includes: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    banner: str = ""
    # Absolute source root. Empty means the vault; extra sources (e.g. the
    # infra repo's docs/) set their own.
    root: str = ""


@dataclass
class SyncStats:
    added: int = 0
    updated: int = 0
    removed: int = 0
    failed: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        base = f"{self.added} added, {self.updated} updated, {self.removed} removed"
        return f"{base}, {len(self.failed)} failed" if self.failed else base


def collection_specs(cfg: Config) -> list[CollectionSpec]:
    """The two collections, and what feeds each.

    Transcripts are kept out of the curated collection on purpose: indexing
    the model's own prior output into the collection that grounds its future
    answers turns a wrong assertion into retrievable "knowledge". They are
    also far longer than the 626-byte average note, so in a shared collection
    one chat could occupy most of the top-k slots.
    """
    specs = [
        CollectionSpec(
            name=cfg.collection_vault,
            description="Obsidian vault — curated notes (synced by obsidian-bridge)",
            excludes=cfg.excludes + (AGENT_NAMESPACE,),
        ),
        CollectionSpec(
            name=cfg.collection_conversations,
            description="Conversation transcripts from OpenClaw and Open WebUI",
            includes=TRANSCRIPT_DIRS,
            excludes=cfg.excludes,
            banner=TRANSCRIPT_BANNER,
        ),
    ]
    specs += [
        CollectionSpec(
            name=name,
            description=f"Markdown from {path} (synced by obsidian-bridge)",
            root=path,
        )
        for name, path in cfg.extra_sources
    ]
    return specs


def upload_name(relpath: str) -> str:
    """Flatten a vault path into an Open WebUI filename.

    Open WebUI cites documents by filename, so the full path is kept (with
    separators folded) rather than just the basename — 292 entity notes make
    bare filenames ambiguous.
    """
    return relpath.replace("/", "__")


async def sync_collection(
    client: WebUIClient,
    cfg: Config,
    state: State,
    spec: CollectionSpec,
) -> SyncStats:
    stats = SyncStats()
    entry = state.collection(spec.name)

    if not entry.kid:
        if cfg.dry_run:
            LOG.info("[dry-run] would create collection %r", spec.name)
            entry.kid = "dry-run"
        else:
            entry.kid = await client.ensure_collection(spec.name, spec.description)

    seen: set[str] = set()
    pending = 0
    root = spec.root or cfg.vault_path

    if not os.path.isdir(root):
        LOG.warning("source root %s for %r does not exist; skipping", root, spec.name)
        return stats

    for relpath in vault.iter_notes(root, excludes=spec.excludes, includes=spec.includes):
        seen.add(relpath)
        try:
            raw = vault.read_note(root, relpath)
        except OSError as exc:
            LOG.warning("unreadable %s: %s", relpath, exc)
            stats.failed.append(relpath)
            continue

        rendered = render_note(relpath, raw, banner=spec.banner)
        sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        previous = entry.files.get(relpath)
        if previous and previous.sha == sha:
            continue

        if cfg.dry_run:
            LOG.info("[dry-run] would %s %s", "update" if previous else "add", relpath)
            stats.updated += 1 if previous else 0
            stats.added += 0 if previous else 1
            continue

        try:
            # Detach the superseded version first so a mid-flight failure
            # cannot leave two copies of the same note in the collection.
            if previous:
                await client.remove_file_from_collection(entry.kid, previous.file_id)
                await client.delete_file(previous.file_id)

            file_id = await client.upload_file(upload_name(relpath), rendered.encode("utf-8"))
            await client.add_file_to_collection(entry.kid, file_id)
        except Exception as exc:  # noqa: BLE001 - one bad note must not stop the pass
            LOG.warning("sync failed for %s: %s", relpath, exc)
            stats.failed.append(relpath)
            entry.files.pop(relpath, None)
            continue

        entry.files[relpath] = FileRecord(sha=sha, file_id=file_id)
        stats.updated += 1 if previous else 0
        stats.added += 0 if previous else 1

        pending += 1
        if pending >= _CHECKPOINT_EVERY:
            save_state(cfg.state_path, state)
            pending = 0

        # Open WebUI embeds inline on file/add; pace to stay under the
        # gateway key's rpm ceiling.
        if cfg.upload_delay_ms:
            await asyncio.sleep(cfg.upload_delay_ms / 1000)

    for relpath in [p for p in entry.files if p not in seen]:
        record = entry.files[relpath]
        if cfg.dry_run:
            LOG.info("[dry-run] would remove %s", relpath)
        else:
            await client.remove_file_from_collection(entry.kid, record.file_id)
            await client.delete_file(record.file_id)
        del entry.files[relpath]
        stats.removed += 1

    return stats


async def sync_all(client: WebUIClient, cfg: Config, state: State) -> dict[str, SyncStats]:
    if not cfg.dry_run:
        vault.prune_expired(cfg.vault_path, TRANSCRIPT_DIRS, cfg.transcript_retention_days)

    results: dict[str, SyncStats] = {}
    for spec in collection_specs(cfg):
        stats = await sync_collection(client, cfg, state, spec)
        results[spec.name] = stats
        LOG.info("%s: %s", spec.name, stats)

    if not cfg.dry_run:
        save_state(cfg.state_path, state)
    return results
