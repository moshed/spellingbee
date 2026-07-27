# Reconstructed crossword grids

The upstream source carries clues, answers and clue numbers — but no grid: no
black squares, no coordinates. These files add the grid back.

It's recoverable because the clue numbers fix the reading-order of every entry,
the answer lengths fix how much room each one needs, and every crossing forces
an across and a down letter to agree. Together that pins the layout down.

Nothing here is a guess. A puzzle is only written out if the rebuilt grid is
re-numbered from scratch and reads back **every** across and down entry exactly
as the source has them. Puzzles that don't reconstruct are skipped rather than
approximated — 387 of 5,874, almost all of them source rows where the across and
down cell totals disagree (entries missing from the scrape) or rebus puzzles,
where one square holds several letters so lengths no longer match cells.

`index.json` lists what's available. Each `YYYY-MM-DD.json` has `grid` (rows of
letters, `#` for black), plus `across`/`down` as `{n, c, a}` — number, clue,
answer.
