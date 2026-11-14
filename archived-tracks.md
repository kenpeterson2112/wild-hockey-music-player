# Archived tracks

Songs taken out of the app's track list. They no longer appear in `window.SONGS`
in `index.html`, so they don't show in the app or on the public track list.

To bring one back, copy its line from the code block into the `window.SONGS`
block of `index.html` (see `AGENTS.md` for the song format), then run
`python3 scripts/build_tracklist.py` and `sh scripts/check.sh`.

## Halloween (archived Nov 14, 2026)

The Halloween-tagged songs, minus Beat It, which stays in the app.

| Song | Start | Spotify |
| --- | --- | --- |
| Thriller | 0:36 | [open](https://open.spotify.com/track/2LlQb7Uoj1kKyGhlkBf9aC) |
| Monster Mash | 0:56.2 | [open](https://open.spotify.com/track/0xxZY5C9xxij3D1HkzbnfC) |
| Dracula | 2:40.4 | [open](https://open.spotify.com/track/5adNBXEoLla10lGJcGzRIL) |
| Somebody's Watching Me | 1:36.2 | [open](https://open.spotify.com/track/7jwQlYGpOml9ETGre1HqGA) |
| Spooky Scary Skeletons | 0:07.2 | [open](https://open.spotify.com/track/2CfCbFpHnL3BYuV3VaY8Pl) |
| Hedwig's Theme | 1:18 | [open](https://open.spotify.com/track/1n8NKQRg8LVHy7oUhUgbFF) |
| Ghostbusters | — | [open](https://open.spotify.com/track/569uHYIB0X324FZOBEhvit) |
| This Is Halloween | 1:51.4 | [open](https://open.spotify.com/track/3mhsDyQpX2L8sJMdWUHOi3) |
| The Addams Family | — | [open](https://open.spotify.com/track/00oHVAstyM08Q82e2XYvkS) |
| Halloween Theme | 1:20.1 | [open](https://open.spotify.com/track/7swocJUCUWTCiRUAU9oerC) |
| Smooth Criminal | 1:31.7 | [open](https://open.spotify.com/track/2bCQHF9gdG5BNDVuEIEnNk) |

```js
{ uri: 'spotify:track:2LlQb7Uoj1kKyGhlkBf9aC', name: 'Thriller', startSec: 36, tags: ['Halloween'] },
{ uri: 'spotify:track:0xxZY5C9xxij3D1HkzbnfC', name: 'Monster Mash', startSec: 56.2, tags: ['Halloween'] },
{ uri: 'spotify:track:5adNBXEoLla10lGJcGzRIL', name: 'Dracula', startSec: 160.4, tags: ['Halloween'] },
{ uri: 'spotify:track:7jwQlYGpOml9ETGre1HqGA', name: "Somebody's Watching Me", startSec: 96.2, tags: ['Halloween'] },
{ uri: 'spotify:track:2CfCbFpHnL3BYuV3VaY8Pl', name: 'Spooky Scary Skeletons', startSec: 7.2, tags: ['Halloween'] },
{ uri: 'spotify:track:1n8NKQRg8LVHy7oUhUgbFF', name: "Hedwig's Theme", startSec: 78, tags: ['Halloween'] },
{ uri: 'spotify:track:569uHYIB0X324FZOBEhvit', name: 'Ghostbusters', tags: ['Halloween'] },
{ uri: 'spotify:track:3mhsDyQpX2L8sJMdWUHOi3', name: 'This Is Halloween', startSec: 111.4, tags: ['Halloween'] },
{ uri: 'spotify:track:00oHVAstyM08Q82e2XYvkS', name: 'The Addams Family', tags: ['Halloween'] },
{ uri: 'spotify:track:7swocJUCUWTCiRUAU9oerC', name: 'Halloween Theme', startSec: 80.1, tags: ['Halloween'] },
{ uri: 'spotify:track:2bCQHF9gdG5BNDVuEIEnNk', name: 'Smooth Criminal', startSec: 91.7, tags: ['Halloween'] },
```
