# Future Plan: Setup Builder + Song Library

Status: **Planned, not built.** Filed for future work. The current app
(hardcoded `window.TRACKS` block + localStorage settings) works and is
being used as-is.

## Goal

Let a user build their own set of songs through a form instead of hand-editing
the `TRACKS` block in `index.html`, save it as a named "setup," and share it
with other coaches/parents who load it into their own phone.

## Decisions already made

- **Audience:** Me + share with others. Each person still runs their own copy
  of the app; setups travel between phones.
- **No backend.** Stays fully client-side on free GitHub Pages. "Setups" live
  in `localStorage`; sharing is done with encoded links and/or files, not a
  server.
- **Sharing:** support **both** a share link *and* a file export/import.
- **Song URIs come from Spotify Search, never hand-written.** We must NOT
  hardcode a catalog of `spotify:track:...` IDs from memory — wrong IDs would
  play the wrong song mid-game. Instead, search Spotify live and let the user
  pick the real result. This also powers a "popular songs" starter list.

## Build sequence (one PR each, so every piece is testable)

### PR 1 — Setup Builder + in-app Spotify search
- New "Setup Builder" screen/modal (own button or under ⚙️).
- Form with the existing categories (pregame, whistles, goalFor, goalAgainst,
  penaltyFor, penaltyAgainst, endGame). Categories stay fixed for now; making
  them user-definable (dynamic buttons) is a separate, bigger change.
- Add a song by **searching Spotify**: type a name → show real results (name,
  artist, album art) → tap to add. Auto-fills the correct URI. Optional
  per-song start time (mm:ss → seconds), reusing existing conversion.
- Save/name multiple setups; pick one to make active.
- Data model: a setup is `{ name, tracks: { <category>: [{uri, name, startSec}] } }`.
- Storage keys: `custom_setups` (list/map of setups), `active_setup` (name or
  null = use built-in `window.TRACKS`).
- Resolve active tracks: change `const tracks = window.TRACKS || {}` to a
  `let` that loads the active custom setup if one is set, else the built-in
  defaults. All `tracks[category]` reads then pick it up.
- Spotify Search API: `GET https://api.spotify.com/v1/search?type=track&q=...`
  with the existing bearer token. **No new OAuth scope needed** — search only
  needs a valid token. Handle 401 the same way playback does (clear token,
  re-auth).

### PR 2 — Share via link + file
- **Export link:** encode the active setup as
  `#setup=<base64(encodeURIComponent(JSON))>` appended to the app URL.
- **Import link:** on load, detect a `#setup=` hash, decode, and offer to save
  + activate it. Stash it immediately (before the Spotify auth redirect can
  drop the hash), then apply after login. Note the auth flow uses the query
  string (`?code=`), so the hash won't collide.
- **Export file:** download the setup as a `.json` file.
- **Import file:** file-picker upload that parses and saves the setup.
- Keep both paths tolerant of bad input (wrap parse in try/catch, show a clear
  message) so a bad link/file can never break the app.

### PR 3 — Popular songs starter list
- A curated list of song **names/artists** (from the stadium/pump-up lists the
  user shared: Thunderstruck, Believer, Crazy Train, Back in Black, Highway to
  Hell, Paint It Black, Seven Nation Army, All I Do Is Win, Lose Yourself,
  etc. — names only, no fabricated IDs).
- Render them as one-tap chips that run the Spotify search from PR 1, so the
  user still picks the verified result. Zero hardcoded URIs.

## Notes / gotchas
- Isolate any new track data the same way `window.TRACKS` is isolated so a typo
  can't kill the app.
- Verify with the existing headless-Chromium/CDP approach used in prior PRs
  (drive the form, stub `fetch` for search/playback, assert on state + layout).
- Watch localStorage size if setups ever embed audio; setups only hold URIs +
  text, so they stay tiny (fine for links and storage).
