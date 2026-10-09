# OpenMap

**OpenMap is an open-source, seamless world map addon for World of Warcraft: Forever that keeps the original Vanilla art style.**

It stitches every zone map into one continuous map. Scroll out of Elwynn and you're looking at Westfall, Duskwood and Redridge, then the whole continent, then the world, instead of clicking in and right-clicking out between zones. It lives inside Blizzard's own world map, so the quest log, the map's buttons, Questie and the rest of the standard map keep working.

## What it does

- **One seamless map.** Zoom from the whole world down to street level, toward your cursor. Zone detail fades in as you get closer, with the game's minimap blended in for extra detail at the closest zoom. When you stop moving, the map underneath quietly becomes the zone you're looking at, so quest areas, coordinates and the zone name match.
- **Zone borders that blend.** Neighbouring zones fade into each other, and the border mountains are colour-matched.
- **The whole map made visible.** Land Forever has no zone map for (Gilneas, the ridges round Orgrimmar, the mountains west of Searing Gorge, the edges of Stonetalon, Feralas, Silithus and more) is drawn from Blizzard's own classic and pre-Cataclysm maps of it, which ship with the game but the game doesn't show. Land no map ever drew is left as clean parchment, like an unfinished map.
- **Ocean and continent names rebuilt** so they zoom properly, lettered in the game's own map font.
- **Dungeon and raid entrances** with level ranges. **Boats and zeppelins**: click one to jump to the other end, and see their routes.
- **Underground.** Zoom into a cave or a dungeon's entrance area and Blizzard's map of it appears.
- **Flight paths.** Learned ones in colour, the rest greyed out. Click two flight masters to see the route you'd fly and roughly how long it takes.
- **Getting around.** Search for a zone, city, dungeon or flight master; a "Find me" button; Ctrl-click to drop a map pin (and a TomTom arrow, if you use it); the map reopens where you left it; party and raid members are shown across the whole map.
- **Vendors, spirit healers and rares** (needs Questie): repair, innkeepers, trainers, bankers, auctioneers, stable masters, spirit healers and rare mobs. These read Questie's NPC database, which isn't a public API, so they may need updating when Questie changes. Questie's quest icons can be switched on or off from OpenMap's menu too.
- **A map that fits your screen.** No black bars at the sides: drag the title bar to move the window and the corner to resize it to any shape, or go full screen and the map fills it.
- **Extras.** Coordinates bar, zone levels on hover, no fade while moving, unexplored areas shown, dimmed or hidden, the map art's parchment border, and a "Report a problem" button for the beta.

Everything is in the **OpenMap** menu on the map (or type `/openmap`). Turn off other world map addons (Leatrix Maps, Mapster, Magnify ...) to avoid conflicts. OpenMap tells you at login if one is on.

## Original game art

Every map and icon OpenMap uses is Blizzard's own art, loaded from the game. The few textures the addon ships are cut or masked from Blizzard's map art (the sea, blank parchment, coastlines, the border) or are plain paper grain made from noise. The zone data, dungeon entrances and levels, boat routes and flight network come from the game's data files; zone level ranges come from the Warcraft Wiki, and townsfolk and spirit healers from Questie. Nothing on the map is AI-generated.

## Status

Beta. Built for WoW Forever (Interface 16001). See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works, [CONTRIBUTING.md](CONTRIBUTING.md) to help, [docs/testing.md](docs/testing.md) for the in-game check before a release and [docs/releasing.md](docs/releasing.md) for publishing one.

Bug reports, ideas, code and fixes are all welcome. Even a screenshot of a spot that looks off helps: use the "Report a problem" button on the map, circle the spot, add a note, and paste the code into a GitHub issue.

## Install (development)

Link the `OpenMap` folder into the game's AddOns folder. In PowerShell (as admin or with developer mode on), from the repo root:

```powershell
New-Item -ItemType SymbolicLink -Path "C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\OpenMap" -Target "$PWD\OpenMap"
```

Restart the game after adding new texture files; `/reload` is enough for Lua changes.

## Licence

The code, data tables and tools are MIT, see [LICENSE](LICENSE). Bundled libraries keep their own licences (`OpenMap/LICENSES`). The map itself is Blizzard's: the zone and continent art is loaded from the game at run time, and the few textures OpenMap ships that are cut from that art (the sea, the blank paper, coastlines, masks) remain Blizzard's and aren't covered by the MIT licence. [OpenMap/Media/Textures/NOTICE.md](OpenMap/Media/Textures/NOTICE.md) lists them and the scripts that make them.
