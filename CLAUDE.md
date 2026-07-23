# Honeycomb — Spelling Hive

A single-file, static hexagonal word game (NYT Spelling Bee style) with a
shareable real-time multiplayer scoreboard. Everything lives in `index.html`
(HTML + CSS + vanilla JS, no build step).

## Structure
- `index.html` — the entire game. Setup screen → 7-hex flower → word entry,
  scoring, ranks, found-words list, and a live scoreboard.

## UI / layout
- **Fit-to-screen** (no scroll on mobile): `.wrap` is a flex column,
  `#game` fills height. Rows top→bottom: header (score strip + ⋯ menu),
  collapsible "Your words …" dropdown (label = rank · pts · words),
  flash+entry line, hex flower (`flex:1`, centered), pill controls
  (Delete / ↻ / Enter). `body.playing` hides the footer + logo word.
- **Flat-top hexagons** (flat edge on top/bottom, points left/right) —
  clip-path `polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)`.
  Flower positions in `layoutFlower()`: top/bottom at ±HEXH, four diagonals at
  (±0.75·HEXW, ±0.5·HEXH), spacing factor `S=1.04` for a hairline gap.
- **Leaderboard = number line** (`#lbTrack`): players placed left→right by
  score (`left = score/maxScore`), score number with initials stacked beneath.
  Only ONE milestone marked — **Genius at 70%**, yellow tick + label. Tied
  players merge into one bubble (`.lbnum`) showing all their initials. Number
  bubbles are STATIC vertically (on the line), move only horizontally by score;
  close bubbles overlap with the leader on top (z-index = f(pct)). Only the
  initials labels (`.lbname`) move — spread horizontally (forward-push + clamp
  to [0,1], `GAP`) so they never overlap. Tap → `#boardSheet`. Header = logo+⋯.
- **No identity claiming.** There is deliberately NO "take over this player"
  action — it would let anyone in a room hijack another player. Cross-device
  resume = the **handoff link** (Continue on another device) generated on the
  original device (`&me`,`&n`), which `pullMine()` restores. Player_id is a PK
  visible to room members, so a UI claim button can't be made secure.
- **Overflow menu** (`#btnMenu` ⋯): Invite/copy link, Continue on another
  device, New puzzle, How to play. Scoring: 4-letter=1pt, +1/extra letter,
  pangram +7 (`wordScore` = `len-3` +7).
- **Share = auto-copy** (`onShare`→`copyLink`): writes the link straight to the
  clipboard + toast; NO `navigator.share`/native sheet/popup. `ensureRoom()`
  lazily opens the shared room on first share.
- **Join flow**: a plain invite link opens `#joinDlg` so the joiner sets their
  own name before being announced (no "Player"). A **handoff** link (`&me`,`&n`)
  skips the prompt and resumes as the same player. Re-opening your OWN invite
  link in the same browser (local progress for that room exists) also skips the
  prompt and resumes you — no duplicate player.
- **Found-words sort**: `#wordSort` toggle A–Z / Recent (order gotten, newest
  first), persisted in `hc_foundSort`. **Change name**: `#btnRename` → `#nameDlg`;
  live-syncs to board + cloud via `pushScore()`.
- **Touch UX**: `touch-action:manipulation` on body kills double-tap-zoom (pinch
  still works); `-webkit-tap-highlight-color:transparent` on `.hex`/buttons +
  a clipped `:active` brightness so the hex press state follows the hexagon
  shape (no square grey box).

## Portable identity (player ID as an account key)
- Identity = `hc_playerId` in localStorage (per browser, persists until the user
  clears site data — the standard). ⋯ menu **My player ID** (`#idDlg`): copy your
  ID, or paste one from another browser (`#useIdBtn`) to adopt it and reload as
  that player. No accounts/passwords.
- `hive_scores` now stores `letters`/`center` too, so a cloud row fully
  reconstructs a board. `fetchCloudGames()` queries all rows for `player_id` and
  `renderResume()` merges them with local boards (`mergeBoards` dedups by room /
  puzzle). Net effect: paste your ID in a fresh browser → all your games appear
  and resume on either device. Deliberately no in-room "claim" button (insecure).

## Resume / recent boards
Every board's progress is saved in localStorage (`hc_game_<sig>`, sig = sorted
letters + center). The home screen shows a **Resume a game** list
(`#resume`/`renderResume()`) built from all `hc_game_*` keys, newest first
(`updated` stamp), so the browser links you back to any prior board — starting a
New puzzle no longer strands the old one. Cross-*device* resume is the separate
handoff link (identity in `&me`).

## Where the words come from
NOT the DB. The word bank is `an-array-of-english-words` (~275k) fetched from a
CDN at runtime, filtered per board, cached in the browser (localStorage `v2` +
HTTP cache). Misc DB only holds scoreboard rows. If a word like `fend`/`confound`
is rejected, it's the stale fallback cache — fixed by the dictionary robustness
changes above.
- `CNAME` — `spellingbee.dancykier.com`.
- Repo: `moshed/spellingbee` (public, renamed from `games`). Game was originally on branch
  `claude/hexagon-word-game-multiplayer-6d318g`; merged into `main`.

## Hosting
- GitHub Pages, served from `main` at repo root (`/`).
- Custom domain `spellingbee.dancykier.com` — Namecheap CNAME → `moshed.github.io.`
  (added alongside geo/jukebox/spellingbee/etc. via the `namecheap.domains.dns.setHosts`
  API; remember `EmailType=OX` or email breaks).
- HTTPS enforced auto-provisions once DNS propagates (same pattern as Pinpoint).

## Multiplayer (Supabase)
See config near the top of the `<script>` in `index.html`:
- Project: **Misc** (`atqhfbaurrmivjarowco`), public anon key hard-coded
  (safe — RLS governs access).
- Table: **`public.hive_scores`** (follows the per-app prefix convention in
  Misc: `bus_`, `fec_`, `fin_`, `pin_`, … → this game owns `hive_`).
- One row per `(room, player_id)`; realtime publication enabled so scores
  stream to every player. Open policies (read/insert/update `using(true)`)
  — it's a public party game, no auth.
- **Live sync = realtime + polling.** `REPLICA IDENTITY FULL` is set for clean
  postgres_changes payloads; on top of the realtime subscription, `Net.refresh()`
  re-pulls the room every 3.5s as a safety net so phone/desktop stay in sync
  even if a realtime event is dropped on a flaky network.
- **Cross-device handoff.** `hive_scores.found jsonb` stores the player's word
  list. `Net.upsert()` writes it; `Net.pullMine()` (called on join) adopts a
  further-along cloud copy and recomputes score. "Continue on another device"
  copies a link with `&me=<player_id>&n=<name>`; `adoptIdentityFromHash()` runs
  BEFORE `PLAYER_ID` is read so the new device resumes as the same player.
- Falls back to offline link-share mode if Supabase is unreachable.

## Dictionary (the "confound not in word list" fix)
- Word list fetched from `an-array-of-english-words` (~275k words) via jsDelivr/
  unpkg. Earlier bug: one failed fetch → permanent fallback to a ~60-word list,
  cached per board. Now: `fetchFullDict()` coalesces + retries (no permanent
  give-up), `computeValidWords()` NEVER caches a fallback result and uses cache
  key `v2`, and `ensureDictThenRecompute()` upgrades the board in the background
  once the real dictionary loads. Letters may repeat freely (only membership is
  checked), so `confound`/`confounded` validate normally.

### Schema (already provisioned)
```sql
create table public.hive_scores (
  room text not null, player_id text not null, name text,
  score int not null default 0, words int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (room, player_id));
alter table public.hive_scores enable row level security;
-- open read/insert/update policies; added to supabase_realtime publication.
```
Cleanup old rooms: `delete from public.hive_scores where updated_at < now() - interval '30 days';`
