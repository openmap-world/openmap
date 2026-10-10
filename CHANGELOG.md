# OpenMap changelog

## Unreleased

- Faster panning and zooming: map icons off the view (townsfolk, flight masters ...) are
  hidden, and blank tiles of the filled-in land aren't drawn.
- Opening the map loads only the zone art in view (and none until zone detail shows), instead
  of the whole world's; `/openmap status` shows how long the last openings took.
- Questie's icons stay on the map when it switches to a zone: any icon Questie's map
  library can't place there is placed from Forever's own map positions. `/openmap status`
  shows how many Questie icons there are and who placed them.
- The parchment border now frames the edge of the world, zoomed right out, instead of the window.
- The map's corner button is OpenMap's icon, in the game's round minimap-button style.
- Zone art coming into view loads over a few frames instead of stalling one; `/openmap status`
  names the slowest steps of the close-up update.
- "Fade while moving" (0-90%, in Options; on / off in the map's menu) replaces "Don't fade while
  moving": the map fades smoothly while you move, never while the mouse is over it.

## v0.1.0-beta (2026-10-09)

First public beta. One seamless world map for WoW Forever: every zone stitched
together, Blizzard's own art, with dungeon entrances and caves, flight paths,
boat and zeppelin routes, townsfolk and rares (with Questie), search, map pins,
group members, a movable and resizable window, and a "Report a problem" button.
The continent and sea names are lettered live; land Forever has no zone map for is
drawn from Blizzard's classic and pre-Cataclysm maps of it, or left as blank parchment.
