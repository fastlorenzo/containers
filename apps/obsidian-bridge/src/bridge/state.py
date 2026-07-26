"""Sync bookkeeping, persisted outside the vault.

Deliberately not under VAULT_PATH: `ob sync --continuous` replicates anything
in the vault to every Obsidian device, and two bridges sharing a state file
would fight over Open WebUI file ids. The predecessor shell script kept its
state in the vault root; this does not.
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("obsidian-bridge.state")

STATE_VERSION = 1


@dataclass
class FileRecord:
    sha: str
    file_id: str


@dataclass
class CollectionState:
    kid: str = ""
    files: dict[str, FileRecord] = field(default_factory=dict)


@dataclass
class State:
    collections: dict[str, CollectionState] = field(default_factory=dict)
    chats: dict[str, dict[str, Any]] = field(default_factory=dict)

    def collection(self, name: str) -> CollectionState:
        return self.collections.setdefault(name, CollectionState())

    def to_json(self) -> dict[str, Any]:
        return {
            "version": STATE_VERSION,
            "collections": {
                name: {
                    "kid": entry.kid,
                    "files": {
                        path: {"sha": rec.sha, "file_id": rec.file_id}
                        for path, rec in entry.files.items()
                    },
                }
                for name, entry in self.collections.items()
            },
            "chats": self.chats,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "State":
        collections: dict[str, CollectionState] = {}
        for name, entry in (payload.get("collections") or {}).items():
            files = {
                path: FileRecord(sha=rec.get("sha", ""), file_id=rec.get("file_id", ""))
                for path, rec in (entry.get("files") or {}).items()
                if rec.get("file_id")
            }
            collections[name] = CollectionState(kid=entry.get("kid", ""), files=files)
        return cls(collections=collections, chats=payload.get("chats") or {})


def load_state(path: str) -> State:
    """Read state, treating any unreadable file as empty.

    A corrupt state file must not wedge the bridge: the sync is idempotent by
    content hash, so the worst case of starting empty is one redundant pass
    that re-uploads notes and re-registers their ids.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return State()
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("unreadable state at %s (%s); starting empty", path, exc)
        return State()

    if payload.get("version") != STATE_VERSION:
        LOG.warning("state version %r != %d; starting empty", payload.get("version"), STATE_VERSION)
        return State()

    return State.from_json(payload)


def save_state(path: str, state: State) -> None:
    """Write state atomically so a crash mid-write cannot truncate it."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, prefix=".state-", suffix=".tmp", delete=False
    )
    try:
        with handle:
            json.dump(state.to_json(), handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
