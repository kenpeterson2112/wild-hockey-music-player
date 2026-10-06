# Rules for AI agents working in this repo

This repo is a hockey soundboard web app (`index.html`, served by GitHub Pages).
It is used live at games, so a broken push means no music at the rink.
Read this whole file before changing anything.

## Who does what

- **Song updates** (Muse or any agent): adding or removing songs, fixing
  Spotify links, start times, and tags. These edits happen **only** inside the
  `window.SONGS = [ ... ];` block of `index.html`, plus the regenerated
  `tracklist/index.html`.
- **App changes** (layout, buttons, settings, scripts, styles, anything outside
  the `window.SONGS` block): done by Claude through a pull request that Ken
  reviews. If a song update seems to need an app change, stop and ask Ken
  instead of making it.

## Before every edit

1. Pull the latest `main` **immediately before** editing. Never work from a copy
   of `index.html` you fetched earlier.
2. Make a targeted edit to the lines you mean to change. **Never replace or
   re-upload the whole `index.html`.** A whole-file write from an old copy has
   already wiped out merged features once (Oct 5, commit `3c526f2`).

## Song format

Each song is one line inside `window.SONGS`:

```js
{ uri: 'spotify:track:1A2B3C4D5E6F7G8H9I0J1K', name: 'Song Title', startSec: 92, tags: ['Goal For'] },
```

- `uri`: `spotify:track:` followed by the 22-character ID from the share link
  (`https://open.spotify.com/track/<ID>?si=...`). Drop the `?si=` part.
- `name`: the title as it should appear in the app.
- `startSec` (optional): whole seconds to skip into the song (1:32 is `92`).
  Leave it out to start at the beginning.
- `tags` (optional): a list. Leave it out for a between-whistles song.
- Every song line ends with a comma except the last one.
- A song must appear only once. To give it several tags, put them all in its
  one `tags` list.

### Tags (exact spelling and capitals)

`Power Play`, `Goal For`, `Goal Against`, `Penalty Kill`, `End Game`,
`Puck Drop`, `Wild`

There is no "Between Whistles" tag: a song with no tags is a between-whistles
song. Don't invent new tags without Ken asking; a new tag also needs a colour
and script support, which is an app change.

## After every edit, before pushing

```sh
python3 scripts/build_tracklist.py   # refresh the public track list page
sh scripts/check.sh                  # must print OK and "0 failed"
```

**If `check.sh` fails, do not push.** Fix what it reports. If it says a feature
is missing from `index.html`, the file was overwritten from an old copy: discard
your change, pull the latest `main`, and redo the edit on that.

## Commits

- One commit per batch of song changes, with a message listing the songs
  (for example: `Add 3 songs: YYZ, Vogue, September`).
- Don't edit files in `scripts/`, `tests/`, `docs/`, or `audio/`, or the
  workflow and settings files, as part of a song update.
- Leave `wild-hockey-songs.xlsx` alone. It's a binary file that Claude
  regenerates with `scripts/export_songs_xlsx.py` as part of its PRs, so it
  can lag a few songs behind; that's expected.
