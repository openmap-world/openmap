# Map data

Builds `OpenMap/Data/Forever/Reveal.lua` (explored-area pieces per zone art) and
`OpenMap/Data/Forever/Places.lua` (instance entrances, boats, zeppelins) from the game's own
tables, fetched as CSV from wago.tools for the given build.

```bash
python -P tools/map-data/build.py <cache dir> [build]
```

Instance entrances are each instance's ghost-return point (`Map.Corpse`); entrances
within 250 yards share one (Blackrock Mountain). Boat and zeppelin docks are the stops
on the transport paths (`TaxiPath` / `TaxiPathNode`). Dungeon level ranges are the game's
Group Finder's (`GroupFinderActivity`); rerunning for a new build keeps them current.

`explore.py` builds `OpenMap/Data/Forever/Explore.lua` for the map's "Show places to explore": the
game's "Explore <zone>" achievements (`Achievement`, `CriteriaTree`, `Criteria` type 43: a
`WorldMapOverlay`), each piece's trigger ground (the terrain's map chunks tagged with one of the
overlay's own areas, not their child areas), its outline and where to go. The terrain is read from
the game's install with `OPENMAP_WOW` (`tools/casc`), else fetched from wago.tools into the cache.

```bash
OPENMAP_WOW="<World of Warcraft folder>" python -P tools/map-data/explore.py <cache dir> [build]
```
