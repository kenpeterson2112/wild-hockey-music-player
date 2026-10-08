# Song submissions

How to collect song requests from players and families with a Google Form and
get them into the app's built-in track list.

## 1. The form

| # | Question | Type | Required |
|---|---|---|---|
| 1 | Song name | Short answer | Yes |
| 2 | Spotify link | Short answer | No* |
| 3 | When should it play? | Checkboxes | No |
| 4 | Start time (optional) | Short answer | No |
| 5 | Your name (optional) | Short answer | No |

\* Optional on the form if you plan to look the links up yourself after
submission — the importer skips any row without a usable link and tells you
which ones it skipped, so a half-filled sheet is safe to run.

**Question 3 is a tick-all-that-apply list** (Checkboxes, not required). Use
these exact options so nothing has to be guessed at import time:

```
Power Play
Goal For
Goal Against
Penalty Kill
End Game
Puck Drop
Wild
Intensity
```

A song with nothing ticked is a between-whistles song. The importer also reads
comma-separated answers like `Goal For, Power Play`, and the old category names
still work.

Put the disambiguation in the question's description, since a list can't hold
per-option help text:

> Goal For = we scored. Goal Against = they scored. Power Play = they're in the
> box. Penalty Kill = we're in the box. Puck Drop = before the puck drops.
> Wild = songs with "wild" in the title. Intensity = high-energy songs. Leave blank for a song that fits any stoppage.

**Question 2 validation** — Response validation → Regular expression →
*Contains*:

```
open\.spotify\.com/track/[A-Za-z0-9]{22}
```

Error text: "Please paste the Spotify share link (Song → Share → Copy Song
Link)."

**Question 4 description:** "Leave blank to start at the beginning. Otherwise
the timestamp where the good part kicks in — `1:32` or `92` both work."

Consider adding a **Clean version?** question (Yes / No / Not sure) if this is a
youth or family rink — Spotify's explicit tracks play uncensored over the PA,
and it is much easier to catch at submission time.

## 2. The import

Download the response sheet as TSV or CSV (File → Download), or copy the cells
and save them to a file, then:

```bash
python scripts/import_songs_tsv.py responses.tsv --dry-run   # preview
python scripts/import_songs_tsv.py responses.tsv             # apply
```

Keep the header row in whatever you feed it — columns are matched by header
name, so column order doesn't matter and Google's `Timestamp` column is ignored.

The importer appends to `window.SONGS` in `index.html` and prints what it did:

```
Goal For:
  + Renegade  (starts 0:48)

Skipped:
  row 6: Thunderstruck: already in the list
  row 7: Some Song: no usable Spotify link ('https://youtube.com/watch?v=abc')
  row 8: Mystery Track: no usable Spotify link ('')

1 added, 3 skipped. 27 -> 28 songs.
```

Rows are skipped, never guessed at, when the song name is blank, the Spotify
link is missing or unusable, or
that track is already in the list. Fix those rows and re-run — songs
already imported are detected as duplicates, so re-running the same sheet is
safe. Pass `--allow-duplicates` to add a track that is already in the list
anyway.

Links may be a share link (with or without a `?si=` suffix), a
`spotify:track:...` URI, or a bare 22-character track ID. Start times may be
`m:ss` or plain seconds, with one optional decimal place for a finer start
(`1:32.5` or `92.5`). These are the same rules the app itself uses for
on-device custom songs.

Before writing, the importer re-parses the block it is about to save and
refuses to write if it doesn't round-trip, so a malformed edit can't take the
app down on load.

## 3. Refresh the public track list

After every import, regenerate the page people browse before submitting:

```bash
python scripts/build_tracklist.py
```

This writes `tracklist/index.html`, which GitHub Pages serves at
`<site>/tracklist` — every song grouped by tag, with a search box so people
can check whether something is already in before requesting it. It is generated
from `window.SONGS`, so it can't drift out of sync with the app as long as you
re-run it (the importer prints a reminder).

To show a "Request a song" button linking to the form, set `FORM_URL` at the top
of `scripts/build_tracklist.py` and re-run. Left blank, the button is omitted.

## 4. Export the current list

To get the current songs back out as a spreadsheet (for review, or to share
with the coaching staff):

```bash
python scripts/export_songs_xlsx.py
```

Writes `wild-hockey-songs.xlsx` — one row per song with name, Spotify link,
tags, and start time.

Both scripts need `openpyxl` (`pip install openpyxl`); the importer alone needs
only the standard library.
