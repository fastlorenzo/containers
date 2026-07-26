"""Turn Obsidian markdown into something worth embedding.

The vault is ~530 notes averaging 626 bytes, so a retrieved chunk is usually a
whole note. That makes per-note noise expensive: a Dataview query block is a
large fraction of a small note, and it carries no meaning for retrieval. 234 of
the 529 notes contain one.

Import-safe: pure functions, no I/O.
"""

import re
from typing import Any

import yaml

# Fenced blocks whose contents are queries or UI declarations rather than
# prose. Dataview/Tasks render tables at view time; Meta Bind renders widgets.
# Embedding any of them injects code noise into a corpus of short notes.
QUERY_LANGUAGES = frozenset(
    {
        "dataview",
        "dataviewjs",
        "tasks",
        "meta-bind",
        "meta-bind-button",
        "meta-bind-js-view",
    }
)

# Embedded binaries: `![[diagram.png]]` contributes nothing to a text index.
ATTACHMENT_SUFFIXES = frozenset(
    {
        "png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "ico",
        "pdf", "mp3", "mp4", "wav", "webm", "mov", "ogg",
        "zip", "canvas", "excalidraw",
    }
)

_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([^\s`~]*)")
_WIKILINK_RE = re.compile(r"(!?)\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter mapping, body). Malformed YAML yields an empty dict.

    A note whose frontmatter does not parse is still worth indexing, so parse
    failures degrade to "no frontmatter" rather than dropping the note.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    body = text[match.end():]
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, body

    return (parsed, body) if isinstance(parsed, dict) else ({}, body)


def strip_query_blocks(text: str) -> str:
    """Remove fenced blocks written in a query/widget language.

    Tracks fence state so that a ```dataview inside a wider ````markdown fence,
    or a stray ``` in prose, does not desynchronise the parse. A fence closes
    only on a marker of the same character and at least the same length.
    """
    out: list[str] = []
    fence_char = ""
    fence_len = 0
    dropping = False

    for line in text.splitlines(keepends=True):
        match = _FENCE_RE.match(line)

        if fence_char:
            # Inside a fence: only a matching closer ends it.
            if match and match.group(2)[0] == fence_char and len(match.group(2)) >= fence_len:
                if not dropping:
                    out.append(line)
                fence_char, fence_len, dropping = "", 0, False
                continue
            if not dropping:
                out.append(line)
            continue

        if match:
            fence_char = match.group(2)[0]
            fence_len = len(match.group(2))
            dropping = match.group(3).strip().lower() in QUERY_LANGUAGES
            if not dropping:
                out.append(line)
            continue

        out.append(line)

    return "".join(out)


def _render_wikilink(match: re.Match[str]) -> str:
    embed, target = match.group(1), match.group(2).strip()

    if "|" in target:
        target, _, alias = target.partition("|")
        alias = alias.strip()
        if alias:
            return alias
        target = target.strip()

    # `[[Note#Heading]]` / `[[Note#^blockid]]`
    note, _, anchor = target.partition("#")
    note, anchor = note.strip(), anchor.strip().lstrip("^").strip()

    # "Links resolve by name, not path" (Second Brain Guide) — the basename is
    # the identity, and the folder prefix is noise in a retrieved chunk.
    note = note.rsplit("/", 1)[-1]

    suffix = note.rsplit(".", 1)[-1].lower() if "." in note else ""
    if embed and suffix in ATTACHMENT_SUFFIXES:
        return ""

    if suffix in ATTACHMENT_SUFFIXES:
        note = note.rsplit(".", 1)[0]
    if note.endswith(".md"):
        note = note[: -len(".md")]

    if note and anchor:
        return f"{note} › {anchor}"
    return note or anchor


def flatten_wikilinks(text: str) -> str:
    """`[[Target|alias]]` -> `alias`, so link targets survive as searchable text.

    Bracket syntax is dead weight in an embedding, and worse in BM25 where the
    brackets fragment the token. The target names are frequently the exact
    proper nouns a query is looking for.
    """
    return _WIKILINK_RE.sub(_render_wikilink, text)


def _flatten_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_flatten_value(v) for v in value if v is not None)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_flatten_value(v)}" for k, v in value.items())
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def format_frontmatter(meta: dict[str, Any]) -> str:
    """Render frontmatter as plain `key: value` lines.

    `type`, `tags`, `company` and `birthdate` on the 292 entity notes are
    exactly the terms a lookup keys on, but YAML punctuation tokenises badly.
    """
    lines = []
    for key, value in meta.items():
        if value is None or value == [] or value == "":
            continue
        rendered = _flatten_value(value).strip()
        if rendered:
            lines.append(f"{key}: {rendered}")
    return "\n".join(lines)


# How far into a note to look for the redundant title heading. The vault's
# templates emit inline Dataview fields (`tags::`, `Date:`) between the
# frontmatter and the H1, so it is not always the first line.
_TITLE_SCAN_LINES = 6


def _strip_leading_title(body: str, title: str) -> str:
    """Drop a leading `# Title` that repeats the heading we prepend.

    Most notes open with an H1 matching their filename, so keeping both wastes
    a line of every chunk and makes one note look like two documents. Bounded
    to the opening lines so a genuine mid-note heading is never removed.
    """
    lines = body.split("\n")
    wanted = title.strip()
    seen = 0

    for index, line in enumerate(lines):
        # Markdown tolerates leading spaces before the hashes, and the vault
        # has notes that use them.
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("# ") and candidate[2:].strip() == wanted:
            return "\n".join(lines[:index] + lines[index + 1:])
        seen += 1
        if seen >= _TITLE_SCAN_LINES:
            break
    return body


def render_note(relpath: str, text: str, *, banner: str = "") -> str:
    """Produce the document body uploaded to Open WebUI for one vault note.

    Every chunk carries provenance: retrieval returns fragments, and a fragment
    with no title or folder is hard to cite and easy to misattribute.
    """
    meta, body = split_frontmatter(text)

    title = relpath.rsplit("/", 1)[-1]
    if title.endswith(".md"):
        title = title[: -len(".md")]
    folder = relpath.rsplit("/", 1)[0] if "/" in relpath else ""

    body = flatten_wikilinks(strip_query_blocks(body))
    body = _strip_leading_title(body, title)

    parts = [f"# {title}", ""]
    if banner:
        parts += [banner, ""]
    parts.append(f"path: {relpath}")
    if folder:
        parts.append(f"folder: {folder}")

    # Frontmatter carries wikilinks too (`company: [[ESET]]`), and those
    # values are exactly the entity names a lookup keys on.
    meta_block = flatten_wikilinks(format_frontmatter(meta))
    if meta_block:
        parts.append(meta_block)

    parts += ["", body.strip()]
    return "\n".join(parts).strip() + "\n"
