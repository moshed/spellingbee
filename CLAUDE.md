# Honeycomb — Spelling Hive

A single-file, static hexagonal word game (NYT Spelling Bee style) with a
shareable real-time multiplayer scoreboard. Everything lives in `index.html`
(HTML + CSS + vanilla JS, no build step).

## Structure
- `index.html` — the entire game. Setup screen → 7-hex flower → word entry,
  scoring, ranks, found-words list, and a live scoreboard side panel.
- `CNAME` — `games.dancykier.com`.
- Repo: `moshed/games` (public). Game was originally on branch
  `claude/hexagon-word-game-multiplayer-6d318g`; merged into `main`.

## Hosting
- GitHub Pages, served from `main` at repo root (`/`).
- Custom domain `games.dancykier.com` — Namecheap CNAME → `moshed.github.io.`
  (added alongside geo/jukebox/etc. via the `namecheap.domains.dns.setHosts`
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
