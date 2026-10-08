#!/usr/bin/env python3
"""Safety check to run before every push. Exits non-zero if something is wrong.

Checks:
  1. The window.SONGS block parses, with no duplicate or malformed links,
     no blank names, sane start times, and no misspelled tags.
  2. Every <script> block in index.html is valid JavaScript (needs node; the
     check is skipped with a warning if node isn't installed).
  3. Key app features are still in index.html. If one of these disappears, the
     file was almost certainly overwritten from an old copy.
  4. tracklist/index.html matches the song list (warning only: fix it with
     `python3 scripts/build_tracklist.py`).

Usage:
    python3 scripts/check_app.py        (or: sh scripts/check.sh)
"""

import collections
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_tracklist import OUTPUT as TRACKLIST_HTML
from build_tracklist import build_page
from tracks_io import INDEX_HTML, TAG_ORDER, _compact, extract_songs

# Features that must survive any edit. Each was lost once when index.html was
# overwritten from a stale copy; the check makes that impossible to miss.
LANDMARKS = {
    "openClearModal": "Clear button (played list / soundboard)",
    "nowPlayingTap": "red 'No Spotify' Now Playing bar",
    "openAddSong": "Add a song window",
    "settings-grid": "Settings Game Tools grid",
    "track-modal-content": "fixed-size song picker",
    "chip-clear": "tag chip clear (X) button",
    "QUEUE_SLOTS": "soundboard tiles",
    "TAG_COLORS": "tag colours",
}

URI_RE = re.compile(r"spotify:track:[A-Za-z0-9]{22}")


def check_songs(html, errors, warnings):
    try:
        songs = extract_songs(html)
    except Exception as exc:  # SystemExit from extract_songs, or a JSON error
        errors.append(f"window.SONGS block does not parse: {exc}")
        return []

    uris = collections.Counter(s.get("uri") for s in songs)
    for uri, n in uris.items():
        if n > 1:
            name = next(s.get("name") for s in songs if s.get("uri") == uri)
            errors.append(f"duplicate song: {name!r} ({uri}) appears {n} times")

    known = {_compact(t): t for t in TAG_ORDER}
    for i, s in enumerate(songs, 1):
        label = f"song {i} ({s.get('name')!r})"
        if not URI_RE.fullmatch(str(s.get("uri", ""))):
            errors.append(f"{label}: link must look like spotify:track:<22 characters>, got {s.get('uri')!r}")
        if not str(s.get("name", "")).strip():
            errors.append(f"{label}: blank name")
        start = s.get("startSec")
        ok_number = isinstance(start, (int, float)) and not isinstance(start, bool)
        if start is not None and (
            not ok_number or start < 0 or start > 900 or round(start * 10) != start * 10
        ):
            errors.append(
                f"{label}: startSec should be seconds between 0 and 900, "
                f"at most one decimal place (62 or 62.5), got {start!r}"
            )
        tags = s.get("tags", [])
        if not isinstance(tags, list):
            errors.append(f"{label}: tags must be a list like ['Goal For']")
            continue
        for tag in tags:
            exact = known.get(_compact(tag))
            if exact and tag != exact:
                errors.append(f"{label}: tag {tag!r} should be spelled {exact!r}")
            elif not exact:
                warnings.append(f"{label}: new tag {tag!r} (not in TAG_ORDER; add it there if it's meant to stay)")
    return songs


def check_scripts(html, errors, warnings):
    node = shutil.which("node")
    if not node:
        warnings.append("node not installed: skipped the JavaScript syntax check")
        return
    blocks = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    for i, block in enumerate(blocks, 1):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(block)
            path = f.name
        result = subprocess.run([node, "--check", path], capture_output=True, text=True)
        Path(path).unlink()
        if result.returncode != 0:
            lines = result.stderr.strip().splitlines()
            detail = next((ln for ln in lines if "Error" in ln), "syntax error")
            where = next((ln.rsplit(":", 1)[-1] for ln in lines if ln.endswith(tuple("0123456789"))), "?")
            errors.append(f"index.html <script> block {i} is not valid JavaScript (line {where} of the block): {detail}")


def check_landmarks(html, errors):
    for needle, feature in LANDMARKS.items():
        if needle not in html:
            errors.append(
                f"'{needle}' is missing from index.html ({feature}). index.html was probably "
                "overwritten from an old copy: pull the latest main and redo the edit."
            )


def check_tracklist(songs, warnings):
    if not songs or not TRACKLIST_HTML.exists():
        return
    strip_date = lambda text: re.sub(r"updated [^<]*", "updated", text)
    current = strip_date(TRACKLIST_HTML.read_text(encoding="utf-8"))
    fresh = strip_date(build_page(songs, updated="x"))
    if current != fresh:
        warnings.append("tracklist/index.html is out of date: run `python3 scripts/build_tracklist.py`")


def main():
    html = INDEX_HTML.read_text(encoding="utf-8")
    errors, warnings = [], []
    songs = check_songs(html, errors, warnings)
    check_scripts(html, errors, warnings)
    check_landmarks(html, errors)
    check_tracklist(songs, warnings)

    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"\nFAILED: {len(errors)} problem(s). Do not push until these are fixed.")
        sys.exit(1)
    tagged = sum(1 for s in songs if s.get("tags"))
    print(f"OK: {len(songs)} songs ({tagged} tagged), all checks passed.")


if __name__ == "__main__":
    main()
