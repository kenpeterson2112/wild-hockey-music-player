# CLAUDE.md

Read `AGENTS.md` first: it has the rules every agent follows here (song format,
valid tags, pull-before-edit, never re-upload the whole `index.html`).

For Claude doing app changes:

- Work on a branch and open a draft PR; Ken merges.
- Run `sh scripts/check.sh` before every push. It validates the song list,
  syntax-checks `index.html`, confirms key features are present, and runs
  `tests/app.test.mjs` (a Node VM harness that drives the real app script).
- If you add or remove an app feature, update `LANDMARKS` in
  `scripts/check_app.py` and the tests to match.
- Adding a tag means touching `TAG_COLORS`/`DEFAULT_TAGS` and the `.tc-*` CSS in
  `index.html`, `TAG_ORDER`/`SECTION_LABELS`/`TAG_TO_SECTION` in
  `scripts/tracks_io.py`, `CATEGORY_STYLE` in `scripts/build_tracklist.py`, and
  the tag list in `AGENTS.md` and `docs/song-submissions.md`.
- After song data changes, regenerate `tracklist/index.html`
  (`build_tracklist.py`) and `wild-hockey-songs.xlsx` (`export_songs_xlsx.py`).
