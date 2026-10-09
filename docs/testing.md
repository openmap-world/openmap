# In-game check (about 15 minutes)

Everything in OpenMap is first checked out of game with the preview renderer
(`tools/map-preview`), but some things only the game can show. Run through this before
a release, and after any change to `Map/Stitch.lua`, `Map/Close.lua` or the textures.

**Setup.** Link the `OpenMap` folder into `_classic_beta_\Interface\AddOns` (see the
README), turn off other world map addons, and **restart the game** (new or changed
textures aren't picked up by `/reload`). Turn on Lua errors: `/console scriptErrors 1`.

Write down anything odd, with `/openmap status` output, or use the map's own
"Report a problem" button.

## 1. It loads (1 min)
- [ ] No Lua error at login. If Leatrix Maps / Mapster / Magnify are on, one chat line says so.
- [ ] `/openmap status` after opening the map: a zone count around 40+, "stitched", and a memory figure.

## 2. The whole world (3 min)
- [ ] Open the map, scroll out to the whole world: one picture, no missing zones, no black or white blocks.
- [ ] The continent and sea names: sharp, in the map's font with a soft glow, staying put as you zoom; never two of one. Scroll in on the Great Sea: the whirlpool stays a while, then the sea keeps a soft paper texture and brown wave strokes along the coasts, with no giant blurred stripes.
- [ ] Drag across from Kalimdor to the Eastern Kingdoms: no stutter you'd notice. Note `/openmap status` memory before and after.
- [ ] Gilneas, round Orgrimmar, the rims of Stonetalon, Feralas and Silithus: Blizzard's own lighter terrain, no stray names, no hard edges. Southern Mount Hyjal and the rest: blank map paper, crisp coastlines, no repeating marks.
- [ ] Orgrimmar: from zoom ~3 the city fills in under Durotar's banner; zoomed in, the banner goes and the whole city shows, soft-edged.
- [ ] Elwynn into Redridge, Elwynn into Westfall: the zones meet through a soft strip, no doubled outlines.

## 3. Up close (3 min)
- [ ] Zoom all the way into Goldshire: the map softens with paper grain, and the minimap's buildings and ground show faintly. The map stays fully opaque: the game world must never show through it.
- [ ] Zoom into Blackrock Mountain or the Wailing Caverns entrance: the world blurs and the cave map surfaces, soft-edged, no stray strips or banner pieces.
- [ ] Click a dungeon entrance icon: it glides down into its cave (or opens the dungeon map).

## 4. Icons and routes (2 min)
- [ ] Dungeon, boat and zeppelin icons; the zeppelin is a red-ballooned airship. Click one: it glides to the other end.
- [ ] OpenMap menu → Boat and zeppelin routes: faint dotted routes, Alliance blue, others red. Hover near one: it lights up with a tooltip.
- [ ] Flight masters: click two, the route and time show.

## 5. Getting around (3 min)
- [ ] Search box: type "gadg", click Gadgetzan → glides there with a marker. Type "deadm" → the Deadmines entrance.
- [ ] Find me button: glides to you.
- [ ] Close the map and reopen it: same view. Move to another zone and reopen: it opens on you.
- [ ] Ctrl-click the map: a map pin appears (and the navigation arrow). Click the pin: it's gone. With TomTom on, Ctrl-click also adds a TomTom arrow.
- [ ] In a group: party members show as class-coloured dots, also on zones the map isn't currently on.
- [ ] Drag the map's title bar: it moves. Drag the bottom-right corner: it resizes. `/reload`, reopen: same place and size. Maximize: the grip and drag bar go away; un-maximize: back where it was.

## 6. Settings and combat (2 min)
- [ ] Options → Look → Unexplored areas: Show / Dim / Hide each change the map at once. On Hide, unexplored parts of a zone are blank parchment; explore a new spot and it fills in without a reload.
- [ ] Open and close the map in combat, open the quest log from it, then leave combat: no "action blocked" message, and the action bars still work.
- [ ] With Questie: quest icons on the stitched map, including in the neighbouring zones and once the map has switched to a zone; the menu's "Questie icons" turns them off and on.
- [ ] HandyNotes / GatherMate / TomTom (if you use them): their icons still show on the zone the map is on, and nothing errors.

## 7. Report a problem (1 min)
- [ ] The report button: circle something, type a note, copy the code. Paste it into `tools/map-preview/report.py`: the render shows your circle in the right place.
