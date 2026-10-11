# OpenMap changelog

## Unreleased

- Map notes (Tools → Map notes, `/openmap notes`) replace the paint tool: paint an area (or
  click) and say what's there, as a "fix this", "look into this" or "idea"; a list of them all
  (click one to go there) and Export, which gives them all as text to paste where they're needed.
  `tools/map-preview/notes.py` renders them out of game. Older paint mark-up becomes notes.
- A debug overlay (Tools → Debug overlay, `/openmap debug`): the frame rate on the map, a graph of
  frame times, the worst frame, and what OpenMap's own updates cost.
- The quest log shows on the full-screen map too: the Quest log button (and the arrow button in
  the corner, as on the windowed map) puts it over the map's right side. Its background no longer
  ends in a line when the window is taller than Blizzard's.
- Blizzard's quest areas (the blue shapes) keep up with the map as it zooms, instead of a step behind.
- The OpenMap button and the favourites' row are in the map's bottom-left corner, along its
  foot (over the coordinates when they show); favourites are icon buttons in Blizzard's
  action-button frame, glowing while they're on.
- The OpenMap menu is laid out afresh in the map window's own frame: the actions as tiles with
  icons, an icon by each setting, bronze rules between the parts. Find me, Drop a pin,
  Report a problem, Options and a new Quest log button (hide or show the quest log beside the
  map, out of combat) can be starred onto the map too.
- "Minimap detail" (in the menu's Up close and in Options) turns the minimap's detail off at
  the closest zoom, so the painted map is all you see.
- The deepest zoom is a slider in the menu, and goes to 192x (it was 96x at most).
- The window resizes from its bottom-left corner as well as the bottom-right, and both grips
  are easier to catch.
- Favourite settings: the star by each setting in the OpenMap menu puts it on the map as a
  button of its own, beside the OpenMap button (lit while it's on; click to switch it,
  right-click to take it off).
- The parchment border's edges are laid as copies of their piece at its own length, every other
  one mirrored, instead of one piece stretched along the whole side; the corners are as they were.
- Orgrimmar and Undercity keep their own maps' name banners: up close that's the city's title,
  and their zone's big banner for them (Durotar's, Tirisfal's) gives way to it as you zoom in,
  instead of covering the city. (Changed textures: restart the game.)
- No more straight-edged patches over the zones zoomed out (east of the Barrens, Stranglethorn ...):
  the blank paper in the gaps between zones reaches only a little way under the zones, not to
  the edge of the square it's drawn in. (Changed textures: restart the game.)
- The ocean past the world map keeps the world sea's own colours, carried outward, instead of
  one flat grey-green. (New texture: restart the game.)
- The OpenMap button stays in the map's top-left corner (an addon's frame across the map
  could push it off the right edge).
- Going full screen and back (or resizing the window) keeps the view you were looking at,
  instead of jumping to where the map was last closed.
- Resizing the window keeps its top-left corner (and the OpenMap menu) in place with the map
  size option off 100%, so the corner stays under the cursor; the resize grip sits in the
  window's outer corner, clear of the quest log button, and is easier to catch.
- Reopening a moved or resized map shows it in its place at once (not Blizzard's first).
- The menu's pin button works wherever you click (on Blizzard's map icons too, where only
  Ctrl-click did), with the pin cursor while it's on.
- On the stitched map the waypoint is always OpenMap's pin: Shift-clicking Blizzard's there was
  blocked ("only available to the Blizzard UI"). Shift-click OpenMap's to share it in chat.
- No more square patches and straight bands in the sea off Stranglethorn and Wetlands: the
  gap fill's borrowed paintings of the land between zones stay on land, and a zone's painted
  sea fades out well inside its frame. (New textures: restart the game.)
- Zone art fades in as it loads (zooming or panning fast onto new zones), instead of popping in.
- Over the major cities' own maps the minimap shows at half strength at most, so the city plan leads.
- "Dim unexplored areas" is now "Fade unexplored areas": those areas fade 60% of the way to the
  zone's blank parchment (its unexplored look) instead of darkening.
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
