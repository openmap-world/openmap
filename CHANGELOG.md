# OpenMap changelog

## Unreleased

- The OpenMap button stays in the map's top-left corner (an addon's frame across the map
  could push it off the right edge).
- Going full screen and back (or resizing the window) keeps the view you were looking at,
  instead of jumping to where the map was last closed.
- Resizing the window keeps its top-left corner (and the OpenMap menu) in place with the map
  size option off 100%, so the corner stays under the cursor; the resize grip sits in the
  window's outer corner, clear of the quest log button, and is easier to catch.
- Reopening a moved or resized map shows it in its place at once (not Blizzard's first).
- Faster panning and zooming: map icons off the view (townsfolk, flight masters ...) are
  hidden, and blank tiles of the filled-in land aren't drawn.
- Opening the map loads only the zone art in view (and none until zone detail shows), instead
  of the whole world's; `/openmap status` shows how long the last openings took.
- Questie's icons stay on the map when it switches to a zone: Questie's map library places
  them from world coordinates that are off on Forever's zone and continent maps, so there
  each icon is placed (or moved) from Forever's own map positions. They're also lifted above the stitched art:
  Questie fixes its icons' frame levels, which put them under the zone art up close. `/openmap status`
  shows how many Questie icons there are and who placed them.
- The parchment border frames the map only when zoomed right out, fading as you zoom in.
- Blizzard's glow on the zone under the cursor is off by default on the stitched map
  ("Zone highlight on hover" in the menu brings it back).
- The map window's portrait is OpenMap's icon while the map is stitched; the OpenMap button
  sits beside Blizzard's floor dropdown instead of under it.
- Opening the map sets its view once (straight to where you left off), or not at all if
  it's still there, instead of Blizzard's reset to the whole world and back; the
  close-up softening no longer recolours the whole map when it first builds a zone.
- Zone art coming into view loads over a few frames instead of stalling one; `/openmap status`
  names the slowest steps of the close-up update, and how much of opening the map is OpenMap's.
- Undercity: Tirisfal's "Undercity" banner sits over the city until close in, as Orgrimmar's
  does. You can zoom 1.5x further in cities, and the minimap mixes in over the cities in the
  open. Undercity's and Ironforge's own maps are drawn over the minimap, which shows the
  surface there, wherever they are in the view.
- Blackrock Mountain's inside (its main floor) surfaces from further out as you zoom in on it.
- Cave and dungeon-entrance maps stay while they're on screen (they no longer fade as you pan
  away from them); only the dimming of the surface follows the one you're centred on.
- Undercity's map is cut to the city's plan (its quarters, the Ruins, the Sewers), so Tirisfal's
  painting shows round it instead of the city map's own parchment.
- "Fade while moving" (0-90%, in Options; on / off in the map's menu) replaces "Don't fade while
  moving": the map fades smoothly while you move, never while the mouse is over it.

## v0.1.0-beta (2026-10-09)

First public beta. One seamless world map for WoW Forever: every zone stitched
together, Blizzard's own art, with dungeon entrances and caves, flight paths,
boat and zeppelin routes, townsfolk and rares (with Questie), search, map pins,
group members, a movable and resizable window, and a "Report a problem" button.
The continent and sea names are lettered live; land Forever has no zone map for is
drawn from Blizzard's classic and pre-Cataclysm maps of it, or left as blank parchment.
