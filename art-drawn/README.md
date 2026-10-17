# Maps drawn by players

WoW Forever's own dungeons have no map in the game. The maps here were drawn by players who let
OpenMap use them; each is credited on the map in game ("Map by ..."). They are not Blizzard's art
and not covered by OpenMap's MIT licence: ask the artist before using them anywhere else.

| File | Dungeon | Drawn by |
| --- | --- | --- |
| `dungeons/city-of-dalaran.png` | City of Dalaran | Santiago Reyes |
| `dungeons/ruins-of-lordaeron.png` | Ruins of Lordaeron | Santiago Reyes |
| `dungeons/hall-of-thanes.png` | The Hall of Thanes | Santiago Reyes |

`gaps/` holds the gaps between zones painted by hand on Blizzard's own art (see its README); like the
dungeon maps, they're used with the artist's permission and aren't covered by the MIT licence.

| File | Where | Painted by |
| --- | --- | --- |
| `gaps/G01_dun-morogh-riverglades.png` | Khaz Modan: round Dun Morogh, Loch Modan, Searing Gorge and the Badlands | Santiago Reyes |

`python -P tools/map-dungeons/drawn.py` turns them into `OpenMap/Media/Textures/MapDungeonDrawn/`
and `OpenMap/Data/DungeonDrawn.lua`. A new one: add the drawing here (a 3:2 picture, the dungeon
map's 1002 x 668 shape) and a line to the script's `DRAWN`.
