#!/usr/bin/env python3
"""Export the song list from index.html into a simple spreadsheet.

Reads the window.TRACKS block in index.html (the "EDIT YOUR TRACKS HERE"
section) and writes one row per track with the song name, its Spotify link,
the button/category it belongs to, and the start time.

Usage:
    python scripts/export_songs_xlsx.py [output.xlsx]
"""

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "index.html"
DEFAULT_OUTPUT = REPO_ROOT / "wild-hockey-songs.xlsx"

# Category key -> label shown on the buttons, mirroring CATEGORIES in index.html.
CATEGORY_LABELS = {
    "pregame": "Pregame",
    "whistles": "Between Whistles",
    "goalFor": "Goal FOR",
    "goalAgainst": "Goal AGAINST",
    "penaltyFor": "Powerplay",
    "penaltyAgainst": "Penalty Kill",
    "endGame": "End Game Intensity",
}

HEADERS = ["Song Name", "Spotify Link", "Category", "Start Time"]


def extract_tracks(html: str) -> dict:
    """Pull the window.TRACKS object literal out of index.html as a dict."""
    match = re.search(r"window\.TRACKS\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        raise SystemExit("Could not find the window.TRACKS block in index.html")

    body = match.group(1)

    # The block is JS, not JSON: single-quoted strings and bare keys. Tokenize so
    # a colon inside a string (spotify:track:...) is never mistaken for a key.
    token = re.compile(
        r"'(?:[^'\\]|\\.)*'"  # single-quoted string
        r"|\"(?:[^\"\\]|\\.)*\""  # double-quoted string
        r"|[A-Za-z_][A-Za-z0-9_]*(?=\s*:)"  # bare key
    )

    def normalize(m):
        text = m.group(0)
        if text[0] == "'":
            return json.dumps(text[1:-1].replace("\\'", "'"))
        if text[0] == '"':
            return text
        return json.dumps(text)

    body = token.sub(normalize, body)
    body = re.sub(r",(\s*[}\]])", r"\1", body)  # drop trailing commas
    return json.loads(body)


def spotify_link(uri: str) -> str:
    """spotify:track:ID -> https://open.spotify.com/track/ID"""
    if uri.startswith("spotify:track:"):
        return "https://open.spotify.com/track/" + uri.split(":")[-1]
    return uri


def format_start(start_sec) -> str:
    """Seconds -> m:ss, blank when the track starts at the beginning."""
    if start_sec in (None, "", 0):
        return ""
    seconds = int(start_sec)
    return f"{seconds // 60}:{seconds % 60:02d}"


def build_rows(tracks: dict) -> list:
    rows = []
    for key, entries in tracks.items():
        label = CATEGORY_LABELS.get(key, key)
        for entry in entries:
            rows.append(
                [
                    entry.get("name", ""),
                    spotify_link(entry.get("uri", "")),
                    label,
                    format_start(entry.get("startSec")),
                ]
            )
    return rows


def write_workbook(rows: list, output: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Songs"

    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="154734")  # Wild green
    body_font = Font(name="Arial")
    link_font = Font(name="Arial", color="0563C1", underline="single")

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="left")

    for r, row in enumerate(rows, start=2):
        for c, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.font = body_font
        link_cell = ws.cell(row=r, column=2)
        if link_cell.value:
            link_cell.hyperlink = link_cell.value
            link_cell.font = link_font
        ws.cell(row=r, column=4).alignment = Alignment(horizontal="left")

    note_row = len(rows) + 3
    note = ws.cell(
        row=note_row,
        column=1,
        value=(
            "Exported from the window.TRACKS block in index.html. Start Time is shown as "
            "m:ss and corresponds to the startSec value (in seconds); a blank means the "
            "track plays from the beginning."
        ),
    )
    note.font = Font(name="Arial", italic=True, size=9)

    widths = [30, 52, 22, 12]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{len(rows) + 1}"

    wb.save(output)


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    tracks = extract_tracks(INDEX_HTML.read_text(encoding="utf-8"))
    rows = build_rows(tracks)
    write_workbook(rows, output)
    print(f"Wrote {len(rows)} songs to {output}")


if __name__ == "__main__":
    main()
