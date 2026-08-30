#!/usr/bin/env python3
"""Generate the public track list page from the window.TRACKS block in index.html.

Writes tracklist/index.html, which GitHub Pages serves at
<site>/tracklist -- a read-only list of every song currently in the app,
grouped by button, so people can check what is already in before submitting
a request.

Re-run this after every import so the published list stays in sync:

    python scripts/build_tracklist.py
"""

import datetime
import html
from pathlib import Path

from tracks_io import (
    CATEGORY_LABELS,
    INDEX_HTML,
    REPO_ROOT,
    extract_tracks,
    format_start_time,
    spotify_url,
)

OUTPUT = REPO_ROOT / "tracklist" / "index.html"

# The song-request form, linked from a button on the page. Left blank, the button
# is omitted entirely.
#
# Keep this the bare /viewform URL. The link Google hands you when you copy it
# carries a `ouid=` parameter identifying the Google account that copied it,
# which has no business on a public page.
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeUBFtplwfdpaIjogPkoqI0tpRBn2GSETPbXL9H5Ox-5JuFIA/viewform"

# Emoji and accent colour per category, matching the app's buttons in index.html.
CATEGORY_STYLE = {
    "pregame": ("📣", "#1DB954"),
    "whistles": ("🎵", "#a855f7"),
    "goalFor": ("🚨", "#1DB954"),
    "goalAgainst": ("🥅", "#e0455e"),
    "penaltyFor": ("💪", "#3b82f6"),
    "penaltyAgainst": ("⚠️", "#f59e0b"),
    "endGame": ("🔥", "#fb7139"),
}

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Track List &middot; Wild Soundboard</title>
<meta name="description" content="Every song currently loaded in the Wild hockey soundboard, by game situation.">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: radial-gradient(circle at 50% 0%, #1a2036 0%, #0d0f16 60%) fixed;
    color: #fff;
    margin: 0;
    padding: 20px 16px 60px;
    line-height: 1.5;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: clamp(1.5rem, 5vw, 2rem); margin: 0 0 6px; }}
  .lede {{ color: #aab; margin: 0 0 20px; font-size: 0.95rem; }}
  .meta {{ color: #778; font-size: 0.8rem; margin: 0 0 20px; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
  .btn {{
    display: inline-block; padding: 10px 16px; border-radius: 10px;
    background: #1DB954; color: #fff; text-decoration: none; font-weight: 700;
    font-size: 0.9rem;
  }}
  .btn.secondary {{ background: #262b3d; }}
  #search {{
    width: 100%; padding: 12px 14px; border-radius: 10px; margin-bottom: 8px;
    border: 1px solid #2c3348; background: #161a27; color: #fff;
    font-size: 1rem; font-family: inherit;
  }}
  #search:focus {{ outline: 2px solid #1DB954; outline-offset: 1px; }}
  #count {{ color: #778; font-size: 0.8rem; min-height: 1.2em; margin-bottom: 18px; }}
  section {{ margin-bottom: 26px; }}
  h2 {{
    font-size: 1rem; text-transform: uppercase; letter-spacing: 0.06em;
    margin: 0 0 10px; padding-left: 10px; border-left: 4px solid var(--accent);
    display: flex; align-items: center; gap: 8px;
  }}
  h2 .n {{ color: #778; font-weight: 400; letter-spacing: 0; text-transform: none; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{
    display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
    padding: 9px 12px; border-radius: 8px; background: #161a27;
    margin-bottom: 5px; border-left: 3px solid var(--accent);
  }}
  li a {{ color: #fff; text-decoration: none; font-weight: 600; }}
  li a:hover {{ text-decoration: underline; }}
  .start {{
    color: #8b93a8; font-size: 0.78rem; font-variant-numeric: tabular-nums;
    background: #0f131e; padding: 2px 7px; border-radius: 20px;
  }}
  /* An author `display` rule outranks the UA style for [hidden], so the filter's
     hidden attribute needs this to actually take items off the page. */
  li[hidden], section[hidden] {{ display: none !important; }}
  .empty {{ color: #778; font-style: italic; padding: 9px 12px; }}
  #noresults {{ display: none; color: #778; font-style: italic; padding: 20px 0; }}
  footer {{ color: #667; font-size: 0.8rem; margin-top: 36px; border-top: 1px solid #232839; padding-top: 16px; }}
  footer a {{ color: #8b93a8; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🏒 Soundboard Track List</h1>
  <p class="lede">Every song currently loaded, by game situation. Have a look before
  submitting a request &mdash; if it is already here, no need to ask for it again.</p>
  <p class="meta">{total} songs &middot; updated {updated}</p>

  <div class="actions">{form_button}
    <a class="btn secondary" href="../">Open the soundboard</a>
  </div>

  <input id="search" type="search" placeholder="Search songs…" autocomplete="off" aria-label="Search songs">
  <div id="count" aria-live="polite"></div>

{sections}
  <p id="noresults">No songs match that search.</p>

  <footer>
    Start times mark where a song begins playing, so it opens on the good part.
    Songs with no time listed play from the beginning.<br>
    Generated from the soundboard's own track list &mdash; <a href="../">back to the app</a>.
  </footer>
</div>

<script>
  // Filter the list as you type. Sections with no remaining matches hide entirely,
  // so the page collapses to just what you searched for.
  (function () {{
    var search = document.getElementById('search');
    var count = document.getElementById('count');
    var noresults = document.getElementById('noresults');
    var sections = Array.prototype.slice.call(document.querySelectorAll('section'));
    var items = Array.prototype.slice.call(document.querySelectorAll('li[data-name]'));

    function apply() {{
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      items.forEach(function (li) {{
        var hit = !q || li.getAttribute('data-name').indexOf(q) !== -1;
        li.hidden = !hit;
        if (hit) shown++;
      }});
      sections.forEach(function (s) {{
        var hits = s.querySelectorAll('li[data-name]:not([hidden])').length;
        s.hidden = !!q && !hits;
        // While filtering, the per-category badge counts matches rather than the
        // category total, so it never reads as "2" beside a single result.
        var badge = s.querySelector('h2 .n');
        if (badge) badge.textContent = q ? hits : badge.getAttribute('data-total');
      }});
      count.textContent = q ? (shown + (shown === 1 ? ' match' : ' matches')) : '';
      noresults.style.display = (q && shown === 0) ? 'block' : 'none';
    }}

    search.addEventListener('input', apply);
    apply();
  }})();
</script>
</body>
</html>
"""


def render_section(key, entries):
    emoji, accent = CATEGORY_STYLE.get(key, ("🎵", "#1DB954"))
    label = html.escape(CATEGORY_LABELS[key])
    lines = [
        f'  <section style="--accent: {accent}">',
        f"    <h2><span>{emoji}</span>{label} "
        f'<span class="n" data-total="{len(entries)}">{len(entries)}</span></h2>',
    ]
    if not entries:
        lines += ['    <p class="empty">Nothing here yet.</p>', "  </section>", ""]
        return "\n".join(lines)

    lines.append("    <ul>")
    for entry in entries:
        name = html.escape(entry["name"])
        url = html.escape(spotify_url(entry["uri"]), quote=True)
        start = format_start_time(entry.get("startSec"))
        badge = f'<span class="start">from {start}</span>' if start else ""
        lines.append(
            f'      <li data-name="{html.escape(entry["name"].lower(), quote=True)}">'
            f'<a href="{url}" target="_blank" rel="noopener">{name}</a>{badge}</li>'
        )
    lines += ["    </ul>", "  </section>", ""]
    return "\n".join(lines)


def main():
    tracks = extract_tracks(INDEX_HTML.read_text(encoding="utf-8"))
    sections = "\n".join(
        render_section(key, tracks.get(key, [])) for key in CATEGORY_LABELS
    )
    total = sum(len(v) for v in tracks.values())
    form_button = (
        f'\n    <a class="btn" href="{html.escape(FORM_URL, quote=True)}" '
        'target="_blank" rel="noopener">Request a song</a>'
        if FORM_URL
        else ""
    )

    page = PAGE.format(
        total=total,
        updated=datetime.date.today().strftime("%B %-d, %Y"),
        sections=sections,
        form_button=form_button,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {total} songs to {OUTPUT}")
    if not FORM_URL:
        print("(FORM_URL is unset — the 'Request a song' button is omitted)")


if __name__ == "__main__":
    main()
