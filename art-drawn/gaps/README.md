# Gaps painted by hand

Land on the continent maps that no zone map covers, painted over by hand: Blizzard's own zone art
cloned, warped and retouched to fill the blank parchment between zones, following the game's own
minimap for what's there. No generated art, and no places or landmarks the game doesn't have.

- `regions.json`: the regions, each with its place on its continent (world units from the
  continent map's top-left), its scale and its size. Kept fixed, so a painting always lines up.
- `G01_<zones>.png` ...: the paintings, named after their region. One may come back at another size
  (a whole-number scale is best); only the part inside the region's fill area is used.
- `fits.json`: how each painting lines up with its region (found once; delete an entry to fit again).

To export the plates an artist paints on (each region's zone art, its fill area, the minimap and
how the map looks there now) into `source/` (not committed):

    python -P tools/map-preview/gapregions.py <db2 dir> <texture cache> [--only G01,G02]

Then, with a painting here:

    python -P tools/map-preview/gapfills.py
    python -P tools/map-preview/render.py <db2 dir> <texture cache> <out> --bake-zones

The first writes `OpenMap/Media/Textures/MapGapFill/` and `OpenMap/Data/GapFills.lua`; the second
bakes the paintings into the zone tiles (`MapZones/`), which draw them at most zooms. Restart the
game to see new textures. Options' Filled gaps turns them off.

| Region | Painted by |
| --- | --- |
| G01 Khaz Modan: round Dun Morogh, Loch Modan, Searing Gorge and the Badlands | Santiago Reyes |
| G02 Kalimdor: round Tanaris and Silithus | Santiago Reyes |
| G03 Eastern Kingdoms: north of the Plaguelands | Santiago Reyes |
| G04 Kalimdor: west of Stonetalon Mountains and the Barrens | Santiago Reyes |
| G05 Eastern Kingdoms: round Silverpine Forest and Hillsbrad Foothills | Santiago Reyes |
| G06 Kalimdor: between Thousand Needles and Feralas | Santiago Reyes |
| G07 Kalimdor: between Winterspring and Darkshore | Santiago Reyes |
| G08 Kalimdor: between Ashenvale and Azshara | Santiago Reyes |
| G09 Eastern Kingdoms: between Stranglethorn Vale and the Blasted Lands | Santiago Reyes |
| G10 Kalimdor: between Thousand Needles and Dustwallow Marsh | Santiago Reyes |
| G11 Kalimdor: between Desolace and Feralas | Santiago Reyes |
