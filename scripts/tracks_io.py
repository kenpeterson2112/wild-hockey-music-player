"""Shared helpers for reading and writing the window.TRACKS block in index.html.

The track list lives in index.html as a JS object literal, not JSON, so it can
stay readable and hand-editable. This module reads that block into a plain dict
and renders a dict back out in the same style.

The Spotify-link and start-time parsers deliberately mirror parseSpotifyTrackId
and parseStartTime in index.html, so anything the app accepts is accepted here.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "index.html"

# Category key -> button label shown in the app, mirroring CATEGORIES in index.html.
# The order here is the order the categories are written back out in.
CATEGORY_LABELS = {
    "pregame": "Pregame",
    "whistles": "Between Whistles",
    "goalFor": "Goal FOR",
    "goalAgainst": "Goal AGAINST",
    "penaltyFor": "Powerplay",
    "penaltyAgainst": "Penalty Kill",
    "endGame": "End Game Intensity",
}

TRACKS_RE = re.compile(r"(window\.TRACKS\s*=\s*)(\{.*?\})(\s*;)", re.DOTALL)

# A JS string, or a bare object key. Tokenizing this way keeps a colon inside a
# string (spotify:track:...) from being mistaken for a key separator.
_JS_TOKEN_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'"  # single-quoted string
    r"|\"(?:[^\"\\]|\\.)*\""  # double-quoted string
    r"|[A-Za-z_][A-Za-z0-9_]*(?=\s*:)"  # bare key
)


def _normalize_label(text):
    """Fold a category label to a comparable form: lowercase, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


# Accept either the button label ("Penalty Kill") or the internal key ("penaltyAgainst").
LABEL_TO_KEY = {}
for _key, _label in CATEGORY_LABELS.items():
    LABEL_TO_KEY[_normalize_label(_label)] = _key
    LABEL_TO_KEY[_normalize_label(_key)] = _key


def category_key(text):
    """Map a category label or key to its internal key, or None if unrecognized."""
    return LABEL_TO_KEY.get(_normalize_label(text))


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


def parse_start_time(text):
    """'m:ss', 'mm:ss', or plain seconds -> whole seconds. Blank/invalid -> 0.

    Mirrors parseStartTime in index.html.
    """
    if text is None:
        return 0
    s = str(text).strip()
    if not s:
        return 0
    if ":" not in s:
        try:
            n = int(float(s))
        except ValueError:
            return 0
        return max(n, 0)
    parts = s.split(":")
    try:
        mins, secs = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0
    return max(mins * 60 + secs, 0)


def format_start_time(start_sec):
    """Seconds -> 'm:ss'. Blank string when the track starts at the beginning."""
    if not start_sec:
        return ""
    seconds = int(start_sec)
    return f"{seconds // 60}:{seconds % 60:02d}"


def spotify_url(uri):
    """'spotify:track:ID' -> 'https://open.spotify.com/track/ID'."""
    if uri.startswith("spotify:track:"):
        return "https://open.spotify.com/track/" + uri.split(":")[-1]
    return uri


def extract_tracks(html):
    """Pull the window.TRACKS object literal out of index.html as a dict."""
    match = TRACKS_RE.search(html)
    if not match:
        raise SystemExit("Could not find the window.TRACKS block in index.html")

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


def render_tracks_block(tracks):
    """Render a tracks dict as the JS object literal, in index.html's style."""
    lines = ["{"]
    keys = [k for k in CATEGORY_LABELS if k in tracks]
    for i, key in enumerate(keys):
        entries = tracks[key]
        if not entries:
            lines.append(f"            {key}: []" + ("," if i < len(keys) - 1 else ""))
            continue
        lines.append(f"            {key}: [")
        for j, entry in enumerate(entries):
            parts = [
                f"uri: {_js_string(entry['uri'])}",
                f"name: {_js_string(entry['name'])}",
            ]
            if entry.get("startSec"):
                parts.append(f"startSec: {int(entry['startSec'])}")
            comma = "," if j < len(entries) - 1 else ""
            lines.append("                { " + ", ".join(parts) + " }" + comma)
        lines.append("            ]" + ("," if i < len(keys) - 1 else ""))
    lines.append("        }")
    return "\n".join(lines)


def replace_tracks_block(html, tracks):
    """Return index.html with its window.TRACKS block replaced by `tracks`."""
    block = render_tracks_block(tracks)
    # A function replacement is used verbatim, so the block needs no escaping.
    return TRACKS_RE.sub(lambda m: m.group(1) + block + m.group(3), html, count=1)
