# Performance: what a zoom out costs, and what was done

`tools/offline-test/perf.py` counts what a zoom out makes the client do. It can't give frames per
second: fill and layout are the game's, so `/openmap bench` (in game) is the measure of a change.
The test's world is built from the repo's own zone and overlay data (about 40 zones, 480 base tiles,
800 overlays: a player's is 49 / 516 / 937), with made-up positions and file IDs.

## Where the work is, in the order it was cheapest to take away

| # | Cause | Seen as | Done |
|---|-------|---------|------|
| 1 | Fading tiles set their opacity on every frame (Stitch.lua, the file loader), 700 and more at once while a zoom out brings the continents' tiles in | up to 3000 calls in a step | 8 steps a fade: a third to a half fewer calls |
| 2 | All names' lettering made in one frame at the first zoom out (a name is hundreds of font strings) | 351 regions made in one step | one name a call: 144 at most |
| 3 | The live zone art (Unexplored areas: hide, Classic, a client that isn't English) instead of the baked tiles | up to 667 textures drawn at once (231 baked) and 3.7k calls a step | not done: needs baked art for that setting |
| 4 | Culled continent tiles stay anchored while their layer is hidden | about 200 placed, not drawn | not done: unverified that the client lays out regions under a hidden frame; measure in game first |
| 5 | The blur copies stay anchored while hidden | about 230 placed, not drawn | not done: as 4 |

A view that hasn't changed makes no calls (tested), so the cost is in the steps of a zoom, not at rest.

## Budgets

`BUDGETS` in perf.py is what the code does now, 10% over. A change that makes a step of a zoom out
draw, anchor, touch or make more regions than that fails; when a change takes work away, lower them.
