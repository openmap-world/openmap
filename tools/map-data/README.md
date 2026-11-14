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
