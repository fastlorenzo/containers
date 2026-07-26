"""Vault filesystem access: walking, routing, path safety, retention."""

import logging
import os
import re
import time
import unicodedata
from collections.abc import Iterator

LOG = logging.getLogger("obsidian-bridge.vault")

_SLUG_STRIP_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SLUG_SPACE_RE = re.compile(r"[\s_-]+", re.UNICODE)


def is_under(relpath: str, prefix: str) -> bool:
    """True if `relpath` is `prefix` itself or sits beneath it.

    Compares whole path segments so that "8. OpenClaw" does not match a
    sibling directory whose name merely starts with it.
    """
    norm = relpath.replace(os.sep, "/").strip("/")
    pref = prefix.replace(os.sep, "/").strip("/")
    return norm == pref or norm.startswith(pref + "/")


def iter_notes(
    vault_path: str,
    *,
    excludes: tuple[str, ...] = (),
    includes: tuple[str, ...] = (),
) -> Iterator[str]:
    """Yield vault-relative paths of markdown notes.

    `includes`, when non-empty, restricts the walk to those subtrees;
    `excludes` always wins. Directories are pruned in place so excluded
    subtrees are never descended into.
    """
    for dirpath, dirnames, filenames in os.walk(vault_path):
        rel_dir = os.path.relpath(dirpath, vault_path)
        rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")

        dirnames[:] = sorted(
            name
            for name in dirnames
            if not any(is_under(f"{rel_dir}/{name}".lstrip("/"), ex) for ex in excludes)
        )

        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            relpath = f"{rel_dir}/{filename}".lstrip("/")
            if any(is_under(relpath, ex) for ex in excludes):
                continue
            if includes and not any(is_under(relpath, inc) for inc in includes):
                continue
            yield relpath


def read_note(vault_path: str, relpath: str) -> str:
    with open(os.path.join(vault_path, relpath), encoding="utf-8", errors="replace") as handle:
        return handle.read()


def resolve_in_vault(vault_path: str, relpath: str) -> str:
    """Resolve `relpath` inside the vault, refusing anything that escapes it.

    Guards the read tool: the path arrives from an LLM, so `../` and absolute
    paths have to be rejected rather than trusted.
    """
    root = os.path.realpath(vault_path)
    candidate = os.path.realpath(os.path.join(root, relpath))
    if candidate != root and not candidate.startswith(root + os.sep):
        raise ValueError(f"path escapes the vault: {relpath!r}")
    return candidate


def slugify(title: str, *, max_length: int = 80) -> str:
    """Filesystem-safe note name, preserving unicode letters.

    Obsidian note titles are the human identity of a note, so this keeps
    accented characters rather than transliterating them away.
    """
    normalised = unicodedata.normalize("NFC", title).strip()
    cleaned = _SLUG_STRIP_RE.sub("", normalised)
    cleaned = _SLUG_SPACE_RE.sub(" ", cleaned).strip()
    cleaned = cleaned[:max_length].strip()
    return cleaned or "untitled"


def unique_path(vault_path: str, relpath: str) -> str:
    """Return `relpath`, or the first free `name (n).md` variant.

    Capture never overwrites: the vault's two-writer rule means the bridge only
    ever creates files, so a title collision has to become a new note.
    """
    if not os.path.exists(os.path.join(vault_path, relpath)):
        return relpath

    stem, ext = os.path.splitext(relpath)
    for index in range(2, 1000):
        candidate = f"{stem} ({index}){ext}"
        if not os.path.exists(os.path.join(vault_path, candidate)):
            return candidate
    raise RuntimeError(f"could not find a free filename for {relpath!r}")


def write_note(vault_path: str, relpath: str, content: str) -> None:
    full = os.path.join(vault_path, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(content)


def prune_expired(vault_path: str, directories: tuple[str, ...], retention_days: int) -> list[str]:
    """Delete transcripts older than the retention window; return their relpaths.

    Transcripts are the component that grows without bound — they reached
    1.7 GB under the previous memory backend. The vault itself is 331 KiB, so
    an unbounded transcript history would dominate both the vault and the
    embedding budget. Deleting here lets the normal sync pass propagate the
    removal to the collection.
    """
    if retention_days <= 0:
        return []

    cutoff = time.time() - retention_days * 86400
    removed: list[str] = []

    for directory in directories:
        for relpath in iter_notes(vault_path, includes=(directory,)):
            full = os.path.join(vault_path, relpath)
            try:
                if os.path.getmtime(full) >= cutoff:
                    continue
                os.unlink(full)
            except OSError as exc:
                LOG.warning("could not expire %s: %s", relpath, exc)
                continue
            removed.append(relpath)

    if removed:
        LOG.info("expired %d transcript(s) past %d days", len(removed), retention_days)
    return removed
