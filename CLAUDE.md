# Honeycomb — Spelling Hive

A single-file, static hexagonal word game (NYT Spelling Bee style) with a
shareable real-time multiplayer scoreboard. Everything lives in `index.html`
(HTML + CSS + vanilla JS, no build step).

## Structure
- `index.html` — the entire game. Setup screen → 7-hex flower → word entry,
  scoring, ranks, found-words list, and a live scoreboard.

## UI / layout
- **Fit-to-screen** (no scroll on mobile): `.wrap` is a flex column,
  `#game` fills height. Rows top→bottom: rank-dot progress bar, collapsible
  "Your words …" dropdown, flash+entry line, hex flower (`flex:1`, centered),
  pill controls (Delete / ↻ / Enter). `body.playing` hides the footer.
- **Flat-top hexagons** (flat edge on top/bottom, points left/right) —
  clip-path `polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)`.
  Flower positions in `layoutFlower()`: top/bottom at ±HEXH, four diagonals at
  (±0.75·HEXW, ±0.5·HEXH), spacing factor `S=1.04` for a hairline gap.
- **Collapsed scoreboard**: player initials as overlapping avatars in the
  top-right (`#crew`), leader first, "+N" overflow. Tap opens `#boardSheet`
  (full standings + timer + Invite/Share).
- **Join flow**: arriving via an invite link opens `#joinDlg` so the joiner
  sets their own name before being announced to the room (no more "Player").
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
- Falls back to offline link-share mode if Supabase is unreachable.

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
