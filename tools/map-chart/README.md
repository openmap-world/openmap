# The sea chart

Options' **Sea chart** (off unless chosen): Santiago Reyes's sea chart round the world map
(`art-drawn/chart/`, used with his permission), laid out for the map window's shape. Zoomed right
out, the chart fills the view; the game's own world map stays in its middle, fading into his sea.

- `export.py <his .psd>`: his layers into `art-drawn/chart/` (needs psd-tools).
- `build.py <db2 dir>`: the textures (`OpenMap/Media/Textures/MapChart/`) and `OpenMap/Data/Chart.lua`.
- `layout.py`: the layout, used by both, by `tools/map-preview/render.py` (`OPENMAP_CHART=1`) and by
  `preview.py`. `OpenMap/Map/Chart.lua` does the same in game; `tools/offline-test/chart.py` checks
  the two agree.
- `preview.py <out dir> [aspect ...]`: the chart alone (the middle outlined) for some window shapes.

How it's laid out (`layout.py`, in his sheet's px):

- **The middle.** The box where the game's world map is at least half there (`Middle`: OpenMap's
  wide edge fade less its burnt rim, never under the continents and their coasts) sits in the
  chart's middle, unscaled, with at least `PAD` of sea round it on the tighter side; the window's
  shape gives the other side more.
- **The paper.** His sheet is cut along the lines of that box into bands round it. A band longer
  than his is made of overlapping cuts of his paper (the first keeps his torn edge, the last meets
  the middle as his did, any between come from inside his paper), each fading in over the one
  before through `SeamX` / `SeamY` (a cross-fade whose edge is bent by smooth noise, so a seam is
  never a straight line); a shorter band is two such cuts. Past `CUTS` cuts a band's cuts stretch.
- **The lines.** The web of his navigation lines stays with the middle; each compass rose's own
  rays (the lines that meet at its centre) move with that rose. Both fade out before his sheet's
  edge, and at the chart's edge (`MapFeather`).
- **The ornaments** keep their size (the corner ones at most `CORNER` of it). For each window shape
  (`ASPECTS` in `build.py`) each one's place is worked out once: in its own zone (the bands round
  the middle and their corners) at the same share of its room as he painted it; if the game's map
  or another ornament is in the way, the nearest free spot, then the band above or below, then a
  little smaller; never on the game's map. The corner ones stay in their corners (or slide along
  an edge). One with no room at all on a shape is left out there.
- **The frame's corners** sit in the chart's corners, the wooden ones at `FRAME` of his size.

In game (`Chart.lua`, Stitch.lua's `S.SetChart`): the chart is drawn under all of OpenMap's art, in
place of the sea OpenMap draws past the world map (`MapSeaFieldOut`, its mottling, the continents'
sea past the world map's edges); the world map fades into it through `MapChart\Middle`. Zoomed right
out the chart fills the view, and the view pans to its edges and no further (WorldMap.lua:
`LeastZoom`, `Extents`). The parchment border round the view is off with it (the chart has its own).
