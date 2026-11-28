# OpenMap for other addons

OpenMap works with most map addons without anything from them: icons other addons put on the
world map through HereBeDragons (Questie, TomTom, gatherers, notes addons) show on the stitched map
from every zone in view, not just the one the map is on, and Blizzard's own map icons keep working.

For more than that there is `OpenMapAPI`, a global table. Check it's there before using it:

```lua
local OM = OpenMapAPI
if OM and OM.major == 1 then
	-- ...
end
```

`OM.version` goes up when something is added. Nothing is changed or taken away without a new
`OM.major`. Everything is read-only or "add your own": nothing lets another addon change OpenMap's
settings. Functions return `nil` (or `false`) when the map hasn't been opened yet or the stitched
map isn't showing.

## Positions

- `u, v`: a point on OpenMap's stitched Azeroth, 0 to 1 across and down. (The same space as the
  in-game Report codes, `OM1|...`.)
- `x, y`: a point on a uiMap, 0 to 1, as Blizzard's map APIs use.

| Function | Returns |
| --- | --- |
| `OM.IsStitched()` | whether the world map shows OpenMap's stitched map now |
| `OM.WorldFromMap(uiMapID, x, y)` | `u, v`, or nil if that map isn't part of the stitched world |
| `OM.MapFromWorld(uiMapID, u, v)` | `x, y` on that map (outside 0..1 when the point is off it) |
| `OM.CanvasFromWorldPos(continent, x, y)` | (version 2) where a point in the game's world (continent and yards, as `UnitPosition` gives them) is on the world map's canvas: `x, y` of the map underneath the stitched view, outside 0..1 where the view shows past it. See below |
| `OM.ArtTopLevel()` | (version 2) the highest frame level the stitched art takes on the canvas |
| `OM.MapAt(u, v)` | the uiMapID of the zone (or city) at that point |
| `OM.CursorPosition()` | (version 3) `u, v` under the cursor, or nil (not stitched, or the cursor's off the map). With `MapAt`: the zone under the cursor at any zoom. The map underneath follows the view, so zoomed in it's a zone and `C_Map.GetMapInfoAtPosition` on it sees no other: a zone-hover tooltip should ask this instead while `OM.IsStitched()` |
| `OM.GetView()` | the view's centre `u, v` and its zoom (1: the whole world fits) |
| `OM.ShowWorld(u, v [, zoom])` | glides the stitched map there; false if it isn't showing |

### Frames of your own on the world map's canvas

On the stitched map the map underneath (`WorldMapFrame:GetMapID()`) is only the part the view is
on: as you zoom in it's a zone, while the view shows its neighbours too. An addon that puts frames on
`WorldMapFrame:GetCanvas()` itself, at positions on that map (dropping anything outside 0..1), only
shows what's on that zone. While `OM.IsStitched()`, place them by `OM.CanvasFromWorldPos` instead and
keep the ones outside 0..1:

```lua
local mx, my
if OM and OM.version >= 2 and OM.IsStitched() then
	mx, my = OM.CanvasFromWorldPos(continent, worldX, worldY)
else
	-- as before, on WorldMapFrame:GetMapID()
end
if mx then frame:SetPoint("CENTER", canvas, "TOPLEFT", canvas:GetWidth() * mx, -canvas:GetHeight() * my) end
```

Recompute on `OpenMap_ViewChanged` or the map's own changes, as for any canvas frame. A frame at a
fixed frame level on the canvas needs to be above OpenMap's art, which `OM.ArtTopLevel()` (version 2)
gives: Questie's icons, made from level 2015, are under it, and OpenMap lifts them itself.

## Callbacks

CallbackHandler-1.0: `OM.RegisterCallback(self, event, method)`, `OM.UnregisterCallback(self, event)`,
`OM.UnregisterAllCallbacks(self)`.

| Event | Arguments |
| --- | --- |
| `OpenMap_StitchedChanged` | `stitched`: the map switched between OpenMap's and Blizzard's own |
| `OpenMap_ViewChanged` | `u, v, zoom`: the stitched view moved (a few times a second at most, and the last always) |
| `OpenMap_DungeonMapShown` | `info`: a dungeon's map is up (below) |
| `OpenMap_DungeonMapHidden` | none |

`info` is `{ mapID = uiMapID, instances = { { name, minLevel, maxLevel, raid, bosses = { name, ... } }, ... } }`
(`mapID` is nil when the client has no map of the dungeon: WoW Forever has none, so its card shows over
the world map when its entrance is clicked, and `OpenMap_DungeonMapShown` doesn't fire for it):
more than one instance when the map is shared (Dire Maul's wings). Bosses are the game's own list, in
its order.

## Adding your own

### A switch in OpenMap's menu

```lua
OM.RegisterMenuToggle("MyAddon", {
	id = "herbs",                       -- yours, stable (a starred switch is saved by it)
	label = "Herbs",
	get = function() return MyAddonDB.showHerbs end,
	set = function(on) MyAddonDB.showHerbs = on; MyAddon:Refresh() end,
	icon = "Interface\\Icons\\INV_Misc_Herb_07",   -- optional
	tab = "show",                       -- "show" (On the map), "look" or "more"; default "show"
	section = "My Addon",               -- the heading it sits under; default "Other addons"
	onRightClick = function() MyAddon:OpenOptions() end,   -- optional (version 5)
	rightClickTip = "open My Addon's options",              -- optional (version 5)
	lit = function() return MyAddonDB.showHerbs end,        -- optional (version 5)
	grey = false,                                           -- optional (version 5)
})
```

It shows in that tab of the OpenMap menu and can be starred onto the map's button tray like
OpenMap's own. Registering the same `id` again replaces it.

(version 5) On the tray, a left-click flips the switch (`set(not get())`). `onRightClick` gives its
button a right-click of your own: open a menu, your options, another feature. Without it a right-click
does nothing. `rightClickTip` adds a line to the button's tooltip, "Right-click: open My Addon's
options" (the key in gold; your text as it is, so translate it yourself). Shift-right-click stays
OpenMap's: it takes the button off the tray.

(version 5) The button glows with a gold edge while `get()` is true and its icon greys while it's
false. `lit` and `grey` set those apart: `lit = function() ... end` decides the glow, `grey =
function() ... end` the greying, and `grey = false` never greys it. A button whose left-click opens
something of yours and whose right-click turns a feature on or off can glow while that feature's on
and never grey.

```lua
OM.RefreshMenuToggles()   -- (version 5)
```

draws your buttons again, reading `get`, `lit` and `grey` anew: call it when what they show changes
outside OpenMap's menu and tray (your own button, a slash command).

### A section on a dungeon's map

```lua
OM.RegisterDungeonSection("MyLootAddon", function(info)
	local lines = {}
	for _, inst in ipairs(info.instances) do
		for _, boss in ipairs(inst.bosses) do lines[#lines + 1] = boss .. ": " .. MyLoot:Summary(boss) end
	end
	return "Loot", lines                -- a title and up to 40 lines; nil for nothing
end)
```

It's shown on the card OpenMap puts on a dungeon's map, after OpenMap's own bosses and quests,
whenever the card is filled. Keep it quick: it runs on the map's change. Pass `nil` as the function
to take it off.

### Townsfolk from your own NPC database

(version 4) OpenMap's townsfolk and rare mobs (On the map > Townsfolk) come from Questie's NPC
database. An addon with a database of the same shape can give it instead, so players without Questie
get them too:

```lua
OM.RegisterTownsfolkProvider("MyNPCs", {
	db = {
		NPCPointers = MyNPCs.byID,          -- [npcID] = anything: the NPCs to go through
		npcFlags = MyNPCs.flags,            -- { VENDOR = bit, REPAIR = bit, INNKEEPER = bit, BANKER = bit,
		                                    --   AUCTIONEER = bit, STABLEMASTER = bit, TRAINER = bit }
		QueryNPCSingle = function(npcID, field) return MyNPCs:Get(npcID, field) end,
		-- fields read: "name", "subName", "npcFlags", "rank" (2 rare elite, 4 rare), "minLevel",
		-- "maxLevel", "friendlyToFaction" ("A", "H", "AH"), "spawns" ({ [areaID] = { { x, y }, ... },
		-- x and y 0..100)
		QueryObjectSingle = function(objectID, field) return MyNPCs:GetObject(objectID, field) end,   -- optional ("spawns": mailboxes)
	},
	zones = { GetUiMapIdByAreaId = function(self, areaID) return MyNPCs.uiMapOf[areaID] end },
	mailboxes = function(faction) return MyNPCs.mailboxes[faction] end,   -- optional: object IDs, faction "A" or "H"
})
```

Questie's own `QuestieDB` and `ZoneDB` modules have this shape. Yours is used whenever it's
registered, Questie or not; pass `nil` to take it off.

Errors in your functions are reported (the game's error handler) and don't break the map.
