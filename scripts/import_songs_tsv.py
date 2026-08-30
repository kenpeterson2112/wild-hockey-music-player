#!/usr/bin/env python3
"""Import Google Form song submissions into the window.TRACKS block in index.html.

Paste the response sheet (headers included) into a file or pipe it in. Columns
are matched by header name, so column order does not matter and the Timestamp
column Google adds is ignored.

Expected headers (matched loosely -- case and punctuation are ignored):
    Song name          the track title
    Spotify link       share link, spotify:track: URI, or bare 22-char ID
    When should it     the button label: Pregame, Between Whistles, Goal FOR,
      play?            Goal AGAINST, Powerplay, Penalty Kill, End Game Intensity
    Start time         optional; m:ss or plain seconds

Usage:
    python scripts/import_songs_tsv.py responses.tsv
    pbpaste | python scripts/import_songs_tsv.py
    python scripts/import_songs_tsv.py responses.tsv --dry-run
"""

import argparse
import csv
import io
import re
import sys

from tracks_io import (
    CATEGORY_LABELS,
    INDEX_HTML,
    category_key,
    extract_tracks,
    format_start_time,
    parse_spotify_uri,
    parse_start_time,
    replace_tracks_block,
)

# Header aliases, checked in order. The first column whose normalized header
# contains one of these substrings wins, so put the specific ones first.
HEADER_ALIASES = {
    "name": ["songname", "songtitle", "song", "title", "track"],
    "link": ["spotify", "link", "url"],
    "category": ["whenshoulditplay", "when", "category", "button", "playduring"],
    "start": ["starttime", "start", "timestampinsong"],
}

# Headers that must never be matched, whatever they look like. "Timestamp" is
# Google's submission time and would otherwise be grabbed as a start time, and
# "Your name" would be grabbed as the song name.
HEADER_BLOCKLIST = ["timestamp", "yourname", "submittedby", "emailaddress"]


def normalize_header(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def sniff_reader(text):
    """Return a csv reader for the pasted text, tab- or comma-separated."""
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    delimiter = "\t" if "\t" in first_line else ","
    return csv.reader(io.StringIO(text), delimiter=delimiter)


def map_columns(header_row):
    """Map each needed field to a column index in the header row."""
    normalized = [normalize_header(h) for h in header_row]
    mapping = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            for i, header in enumerate(normalized):
                if i in mapping.values() or not header:
                    continue
                if any(bad in header for bad in HEADER_BLOCKLIST):
                    continue
                if alias in header:
                    mapping[field] = i
                    break
            if field in mapping:
                break
    return mapping


def cell(row, index):
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def read_rows(text):
    """Parse the pasted sheet into (row_number, entry_or_None, problem_or_None)."""
    reader = sniff_reader(text)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise SystemExit("No rows found in the input.")

    mapping = map_columns(rows[0])
    missing = [f for f in ("name", "link", "category") if f not in mapping]
    if missing:
        raise SystemExit(
            "Could not find a column for: "
            + ", ".join(missing)
            + "\nHeaders seen: "
            + ", ".join(repr(h) for h in rows[0])
            + "\nMake sure the header row is included in what you paste."
        )

    results = []
    for line_no, row in enumerate(rows[1:], start=2):
        name = cell(row, mapping.get("name"))
        link = cell(row, mapping.get("link"))
        category = cell(row, mapping.get("category"))
        start_raw = cell(row, mapping.get("start"))

        if not name:
            results.append((line_no, None, "no song name"))
            continue
        uri = parse_spotify_uri(link)
        if not uri:
            results.append(
                (line_no, None, f"{name}: no usable Spotify link ({link!r})")
            )
            continue
        key = category_key(category)
        if not key:
            results.append(
                (line_no, None, f"{name}: unrecognized category ({category!r})")
            )
            continue

        entry = {"uri": uri, "name": name, "key": key}
        start_sec = parse_start_time(start_raw)
        if start_sec > 0:
            entry["startSec"] = start_sec
        results.append((line_no, entry, None))
    return results


def merge(tracks, parsed, allow_duplicates=False):
    """Append parsed entries to the tracks dict. Returns (added, skipped)."""
    added, skipped = [], []
    for line_no, entry, problem in parsed:
        if problem:
            skipped.append((line_no, problem))
            continue
        key = entry.pop("key")
        bucket = tracks.setdefault(key, [])
        if not allow_duplicates and any(t["uri"] == entry["uri"] for t in bucket):
            skipped.append(
                (line_no, f"{entry['name']}: already in {CATEGORY_LABELS[key]}")
            )
            continue
        bucket.append(entry)
        added.append((key, entry))
    return added, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", nargs="?", help="TSV/CSV file; reads stdin when omitted"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without touching index.html",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="add a song even if that track is already in the same category",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    html = INDEX_HTML.read_text(encoding="utf-8")
    tracks = extract_tracks(html)
    before = sum(len(v) for v in tracks.values())

    parsed = read_rows(text)
    added, skipped = merge(tracks, parsed, args.allow_duplicates)

    for key in CATEGORY_LABELS:
        entries = [e for k, e in added if k == key]
        if not entries:
            continue
        print(f"{CATEGORY_LABELS[key]}:")
        for entry in entries:
            start = format_start_time(entry.get("startSec"))
            print(f"  + {entry['name']}" + (f"  (starts {start})" if start else ""))

    if skipped:
        print("\nSkipped:")
        for line_no, problem in skipped:
            print(f"  row {line_no}: {problem}")

    if not added:
        print("\nNothing to add.")
        return

    after = sum(len(v) for v in tracks.values())
    print(f"\n{len(added)} added, {len(skipped)} skipped. {before} -> {after} songs.")

    if args.dry_run:
        print("Dry run — index.html not modified.")
        return

    updated = replace_tracks_block(html, tracks)

    # Re-parse what we are about to write, so a malformed block never lands in
    # index.html: a broken TRACKS block would take the app down on load.
    roundtrip = extract_tracks(updated)
    if sum(len(v) for v in roundtrip.values()) != after:
        raise SystemExit("Refusing to write: the rewritten block did not round-trip.")

    INDEX_HTML.write_text(updated, encoding="utf-8")
    print(f"Updated {INDEX_HTML}")
    print("\nNext: python scripts/build_tracklist.py   (refresh the public track list)")


if __name__ == "__main__":
    main()
