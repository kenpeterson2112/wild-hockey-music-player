#!/usr/bin/env python3
"""Import Google Form song submissions into the window.SONGS block in index.html.

Paste the response sheet (headers included) into a file or pipe it in. Columns
are matched by header name, so column order does not matter and the Timestamp
column Google adds is ignored.

Expected headers (matched loosely -- case and punctuation are ignored):
    Song name          the track title
    Spotify link       share link, spotify:track: URI, or bare 22-char ID
    When should it     optional; tags for the song, comma separated: Goal For,
      play?            Goal Against, Power Play, Penalty Kill, End Game. Blank
                       or "Between Whistles" means no tag (a between-whistles
                       song). Old category names still work.
    Start time         optional; m:ss, m:ss.s, or plain seconds (to the tenth)

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
    INDEX_HTML,
    TAG_ORDER,
    extract_songs,
    format_start_time,
    parse_spotify_uri,
    parse_start_time,
    replace_songs_block,
    sort_tags,
    split_tags,
)

# Header aliases, checked in order. The first column whose normalized header
# contains one of these substrings wins, so put the specific ones first.
HEADER_ALIASES = {
    "name": ["songname", "songtitle", "song", "title", "track"],
    "link": ["spotify", "link", "url"],
    "category": ["whenshoulditplay", "when", "tags", "tag", "category", "button", "playduring"],
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
    missing = [f for f in ("name", "link") if f not in mapping]
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
        entry = {"uri": uri, "name": name}
        tags = split_tags(category)
        if tags:
            entry["tags"] = tags
        start_sec = parse_start_time(start_raw)
        if start_sec > 0:
            entry["startSec"] = start_sec
        results.append((line_no, entry, None))
    return results


def merge(songs, parsed, allow_duplicates=False, allow_new_tags=False):
    """Append parsed entries to the songs list. Returns (added, skipped).

    A tag the library has never used is treated as a typo and the row is
    skipped, unless allow_new_tags is set. A song already in the list (same
    Spotify track) is skipped, unless allow_duplicates is set.
    """
    known = {t.lower() for t in TAG_ORDER}
    for song in songs:
        known.update(t.lower() for t in song.get("tags", []))
    added, skipped = [], []
    for line_no, entry, problem in parsed:
        if problem:
            skipped.append((line_no, problem))
            continue
        new_tags = [t for t in entry.get("tags", []) if t.lower() not in known]
        if new_tags and not allow_new_tags:
            skipped.append(
                (line_no, f"{entry['name']}: unknown tag {', '.join(map(repr, new_tags))}"
                 " (use --allow-new-tags to create it)")
            )
            continue
        if not allow_duplicates and any(s["uri"] == entry["uri"] for s in songs):
            skipped.append((line_no, f"{entry['name']}: already in the list"))
            continue
        songs.append(entry)
        added.append(entry)
        known.update(t.lower() for t in entry.get("tags", []))
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
        help="add a song even if that track is already in the list",
    )
    parser.add_argument(
        "--allow-new-tags",
        action="store_true",
        help="create a tag the library has not used before instead of skipping the row",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    html = INDEX_HTML.read_text(encoding="utf-8")
    songs = extract_songs(html)
    before = len(songs)

    parsed = read_rows(text)
    added, skipped = merge(songs, parsed, args.allow_duplicates, args.allow_new_tags)

    for entry in added:
        start = format_start_time(entry.get("startSec"))
        tags = ", ".join(sort_tags(entry.get("tags", []))) or "no tags (between whistles)"
        print(f"  + {entry['name']}  [{tags}]" + (f"  (starts {start})" if start else ""))

    if skipped:
        print("\nSkipped:")
        for line_no, problem in skipped:
            print(f"  row {line_no}: {problem}")

    if not added:
        print("\nNothing to add.")
        return

    after = len(songs)
    print(f"\n{len(added)} added, {len(skipped)} skipped. {before} -> {after} songs.")

    if args.dry_run:
        print("Dry run — index.html not modified.")
        return

    updated = replace_songs_block(html, songs)

    # Re-parse what we are about to write, so a malformed block never lands in
    # index.html: a broken SONGS block would take the app down on load.
    roundtrip = extract_songs(updated)
    if len(roundtrip) != after:
        raise SystemExit("Refusing to write: the rewritten block did not round-trip.")

    INDEX_HTML.write_text(updated, encoding="utf-8")
    print(f"Updated {INDEX_HTML}")
    print("\nNext: python scripts/build_tracklist.py   (refresh the public track list)")


if __name__ == "__main__":
    main()
