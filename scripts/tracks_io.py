"""Shared helpers for reading and writing the window.SONGS block in index.html.

The song list lives in index.html as a JS array literal, not JSON, so it can
stay readable and hand-editable. This module reads that block into a plain list
and renders a list back out in the same style.

Each song is { uri, name, startSec?, tags? }. Tags are plain words such as
"Goal For". A song with no tags is a between-whistles song.

The Spotify-link and start-time parsers deliberately mirror parseSpotifyTrackId
and parseStartTime in index.html, so anything the app accepts is accepted here.
"""

import json
import math
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "index.html"

# The tags the app and these scripts know by name, in the order they are shown.
# Any other tag a song carries is kept and shown too.
TAG_ORDER = ["Power Play", "Goal For", "Goal Against", "Penalty Kill", "End Game", "Puck Drop", "Wild", "Intensity"]

# Old spellings and category names -> the tag they mean. Keys are compact
# (lowercase letters and digits only), so "Goal FOR", "goalFor" and "goal for"
# all land on "Goal For".
LEGACY_TAGS = {
    "powerplay": "Power Play",
    "penaltyfor": "Power Play",
    "goalfor": "Goal For",
    "goalagainst": "Goal Against",
    "penaltykill": "Penalty Kill",
    "penaltyagainst": "Penalty Kill",
    "endgame": "End Game",
    "endgameintensity": "End Game",
    "puckdrop": "Puck Drop",
    "pregame": "Pregame",
}

# Words that mean "no tag": the untagged default is a between-whistles song.
NO_TAG_WORDS = {"whistles", "betweenwhistles", "whistle", "none", "untagged"}

SONGS_RE = re.compile(r"(window\.SONGS\s*=\s*)(\[.*?\])(\s*;)", re.DOTALL)

# A JS string, or a bare object key. Tokenizing this way keeps a colon inside a
# string (spotify:track:...) from being mistaken for a key separator.
_JS_TOKEN_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'"  # single-quoted string
    r"|\"(?:[^\"\\]|\\.)*\""  # double-quoted string
    r"|[A-Za-z_][A-Za-z0-9_]*(?=\s*:)"  # bare key
)


def _compact(text):
    """Fold text to lowercase letters and digits only, for comparing names."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def clean_tag(text):
    """A tag as typed -> its display name, or None when it means 'no tag'.

    Old category names and spellings resolve to the current tag names; anything
    else is kept as written (whitespace tidied).
    """
    tidy = re.sub(r"\s+", " ", str(text or "").strip())
    if not tidy:
        return None
    compact = _compact(tidy)
    if compact in NO_TAG_WORDS:
        return None
    return LEGACY_TAGS.get(compact, tidy)


def split_tags(text):
    """'Goal For, Power Play' -> ['Goal For', 'Power Play'] (comma or semicolon)."""
    tags = []
    for part in re.split(r"[;,]", str(text or "")):
        tag = clean_tag(part)
        if tag and tag.lower() not in [t.lower() for t in tags]:
            tags.append(tag)
    return tags


def sort_tags(tags):
    """Known tags first in TAG_ORDER, then any others A-Z."""
    known = [t for t in TAG_ORDER if t in tags]
    others = sorted((t for t in tags if t not in TAG_ORDER), key=str.lower)
    return known + others


def parse_spotify_uri(text):
    """Any form the app accepts -> 'spotify:track:ID'. None if unrecognized.

    Mirrors parseSpotifyTrackId in index.html: share link, URI, or bare ID.
    """
    if not text:
        return None
    s = str(text).strip()
    m = re.search(r"open\.spotify\.com/track/([A-Za-z0-9]+)", s)
    if m:
        return "spotify:track:" + m.group(1)
    m = re.search(r"spotify:track:([A-Za-z0-9]+)", s)
    if m:
        return "spotify:track:" + m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]{22}", s):
        return "spotify:track:" + s
    return None


def tidy_seconds(value):
    """Round to tenths of a second; whole numbers come back as int (62.0 -> 62)."""
    # floor(x + 0.5) rounds halves up, matching Math.round in index.html
    value = math.floor(float(value) * 10 + 0.5) / 10
    return int(value) if value == int(value) else value


def parse_start_time(text):
    """'m:ss', 'm:ss.s', or plain seconds ('92', '92.5') -> seconds, to the tenth.

    Blank/invalid -> 0. Whole values are ints. Mirrors parseStartTime in index.html.
    """
    if text is None:
        return 0
    s = str(text).strip()
    if not s:
        return 0
    try:
        if ":" not in s:
            total = float(s)
        else:
            parts = s.split(":")
            total = int(parts[0]) * 60 + float(parts[1])
    except (ValueError, IndexError):
        return 0
    return tidy_seconds(total) if total > 0 else 0


def format_start_time(start_sec):
    """Seconds -> 'm:ss' or 'm:ss.s'. Blank string when the track starts at the beginning."""
    if not start_sec:
        return ""
    start_sec = tidy_seconds(start_sec)
    mins, secs = divmod(start_sec, 60)
    if isinstance(start_sec, int):
        return f"{int(mins)}:{int(secs):02d}"
    return f"{int(mins)}:{secs:04.1f}"


def spotify_url(uri):
    """'spotify:track:ID' -> 'https://open.spotify.com/track/ID'."""
    if uri.startswith("spotify:track:"):
        return "https://open.spotify.com/track/" + uri.split(":")[-1]
    return uri


def extract_songs(html):
    """Pull the window.SONGS array literal out of index.html as a list of dicts."""
    match = SONGS_RE.search(html)
    if not match:
        raise SystemExit("Could not find the window.SONGS block in index.html")

    def normalize(m):
        text = m.group(0)
        if text[0] == "'":
            return json.dumps(text[1:-1].replace("\\'", "'"))
        if text[0] == '"':
            return text
        return json.dumps(text)

    body = _JS_TOKEN_RE.sub(normalize, match.group(2))
    body = re.sub(r",(\s*[}\]])", r"\1", body)  # drop trailing commas
    return json.loads(body)


def _js_string(value):
    """Render a Python string as a JS literal, matching the file's quoting style.

    Single quotes normally; double quotes when the text contains an apostrophe,
    so names like "Let's Go" read the way they already do in index.html.
    """
    if "'" in value and '"' not in value:
        return '"' + value.replace("\\", "\\\\") + '"'
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def render_songs_block(songs):
    """Render a songs list as the JS array literal, in index.html's style."""
    if not songs:
        return "[]"
    lines = ["["]
    for i, entry in enumerate(songs):
        parts = [
            f"uri: {_js_string(entry['uri'])}",
            f"name: {_js_string(entry['name'])}",
        ]
        if entry.get("startSec"):
            parts.append(f"startSec: {tidy_seconds(entry['startSec'])}")
        if entry.get("tags"):
            tag_list = ", ".join(_js_string(str(t)) for t in entry["tags"])
            parts.append(f"tags: [{tag_list}]")
        comma = "," if i < len(songs) - 1 else ""
        lines.append("            { " + ", ".join(parts) + " }" + comma)
    lines.append("        ]")
    return "\n".join(lines)


def replace_songs_block(html, songs):
    """Return index.html with its window.SONGS block replaced by `songs`."""
    block = render_songs_block(songs)
    # A function replacement is used verbatim, so the block needs no escaping.
    return SONGS_RE.sub(lambda m: m.group(1) + block + m.group(3), html, count=1)


def songs_by_section(songs):
    """Group songs into the game-situation sections the track list page shows.

    Returns {section_key: [songs]} for every key in SECTION_LABELS. A song with
    several tags appears in each of its sections; a song with none is a
    between-whistles song. Used by the spreadsheet export and the track list page.
    """
    sections = {key: [] for key in SECTION_LABELS}
    for song in songs:
        keys = [TAG_TO_SECTION[t] for t in song.get("tags", []) if t in TAG_TO_SECTION]
        for key in dict.fromkeys(keys) or ["whistles"]:
            sections[key].append(song)
    return sections


# Section key -> heading, in the order the track list page shows them.
SECTION_LABELS = {
    "whistles": "Between Whistles",
    "puckDrop": "Puck Drop",
    "goalFor": "Goal For",
    "goalAgainst": "Goal Against",
    "penaltyFor": "Power Play",
    "penaltyAgainst": "Penalty Kill",
    "endGame": "End Game",
    "wild": "Wild",
    "intensity": "Intensity",
}
TAG_TO_SECTION = {
    "Power Play": "penaltyFor",
    "Goal For": "goalFor",
    "Goal Against": "goalAgainst",
    "Penalty Kill": "penaltyAgainst",
    "End Game": "endGame",
    "Puck Drop": "puckDrop",
    "Wild": "wild",
    "Intensity": "intensity",
}
