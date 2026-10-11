# Where these textures come from

OpenMap draws no art of its own. Every texture here is either cut from World of
Warcraft's own map art (Blizzard Entertainment's, not covered by OpenMap's MIT
licence) or generated from noise. Each is made by a script in `tools/`, so it
can be rebuilt from the game's files; the few touched by hand (marked below) are
Blizzard's art edited by hand, kept in `art-edits/`.

**From Blizzard's art** (crops, colour fields and shapes taken from the game's map textures):

| Texture | What it is | Made by |
| --- | --- | --- |
| `MapSeaDark`, `MapSeaLight` | the open sea's crackled paper, from the client's high-resolution Eastern Kingdoms overview map (its hatching painted out) | `tools/map-preview/sea.py` |
| `MapSeaField/` | the sea's colour, smoothed from the world and continent maps | `tools/map-preview/sea.py` |
| `MapHatch` | the coastal wave strokes, from the Kalimdor continent map | `tools/map-preview/sea.py` |
| `MapPaper` | blank map parchment, from Westfall's zone map | `tools/map-preview/gapfill.py` |
| `MapGap/` | coastlines from the continent maps, and zone edges carried across the strips between zones | `tools/map-preview/gapfill.py` |
| `MapLand/` | smooth colour fields of the continent maps' land | `tools/map-preview/render.py --bake-land` |
| `MapBand/`, `MapCore/`, `MapTerritory/`, `MapEdge/` | masks traced from each zone map's shape and frame | `tools/map-grade`, `tools/map-preview` |
| `MapCave/` | masks traced from the cave maps | `tools/map-caves/build.py` |
| `MapCoast/`, `MapSeaMask/`, `MapGapLand/`, `MapGapMask/`, `MapBackLand/` | masks traced from the continent maps' coasts | `tools/map-preview/sea.py`, `gapfill.py` |
| `MapSeaOut/`, `MapSeaOpen/`, `MapSeaCoast/` | masks of the world and continent maps' sea: past the world map's edge, and its coastal hatching apart from its open sea | `tools/map-preview/sea_world.py` |
| `MapBanner/` | a zone map's name banner for a city ("Orgrimmar" on Durotar's), cut out along a traced outline | `tools/map-preview/banners.py` |
| `MapBannerHole/`, `MapCityMask/` | masks traced on the art: the zone's art without that banner, and a city's map cut down to the city and its name banner | `tools/map-preview/banners.py` |
| `MapGapLand/` (Gilneas), `MapCoastArt/` | masks for Blizzard's own maps that the client has but Forever's tables don't use (Gilneas' base map; the classic base maps of 18 zones, which paint the land round them): where they're drawn, at their own resolution, on land no zone covers | `tools/map-preview/gapfill.py` |
| `MapArt/` | world and continent map tiles with their sea and continent names painted out (by hand) | `tools/map-art/import.py` |
| `MapBorder/` | the map art's parchment frame (cut out by hand), in nine pieces | `tools/map-art/border.py` |

**Generated** (no game art in them): `MapGrain`, `MapTooth` (paper grain, from noise)
and the `MapFeather*` edge masks (`tools/map-textures/make.py`).
