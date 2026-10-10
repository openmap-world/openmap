# Map preview

Renders OpenMap's stitched world map out of game: the same maps, placements,
masks, fades and colour matching as `OpenMap/Map/Stitch.lua`, from the
client's own map tables and textures. Use it to check blending without logging in.

Needs Python with Pillow, numpy and scipy, and the Forever build's map tables
(`UiMap`, `UiMapAssignment`, `UiMapArt`, `UiMapArtTile`, `UiMapXMapArt` as CSV
from wago.tools for build 1.60.1.70245) in one folder. Textures are downloaded by
file ID into the cache folder on first use (about 1,600 files).

```bash
python -P tools/map-preview/render.py <db2 dir> <texture cache> <out dir> "world=0.5,0.5,1" "barrens=@Mulgore+The Barrens,8"
```

A view is `name=u,v,zoom` (centre on Azeroth's map, zoom 1 = the whole world) or
`name=@Zone Name,zoom` (`@A+B` centres between two zones). `--bake-territory`
first rewrites `Media/Textures/MapTerritory` (where each zone's base art shows:
its own land and a little past it, its painted sea off its coasts, the cities in
it, never past its own frame). Re-run `gapfill.py` after it: the gaps are what
the territories leave.

`--bake-land` rewrites `Media/Textures/MapLand/<continent>.tga` (the continents'
land masks). The edge fades and the parchment grain come from
`tools/map-textures/make.py`.

The other bakes, each a script here (run with the same `<db2 dir> <texture cache>`):

| Script | Writes |
| --- | --- |
| `sea.py` | the sea's paper and wave strokes, the coastal bands, the backdrop's land / sea masks |
| `sea_world.py` (after `sea.py`) | the continents' sea past the world map's edges, the sea's colour out there (the world sea's own, carried outward), and the world map's coastal hatching apart from its open sea |
| `gapfill.py` | the gaps: blank parchment, carried strips, bare coasts |
| `banners.py` | city banners cut from their zone's art (Orgrimmar on Durotar's) |
| `tone.py` | each zone's colour, for the close-up minimap's tint |

