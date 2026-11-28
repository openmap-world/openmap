--------------------------------------------------------------------------------
-- Getting around the map:
--   find me      a button that glides to where you are
--   reopen       choose player-centred, zone-centred, always remember, or remember
--                only while the player is still inside the previous view
--   waypoints    Ctrl-click the map to drop Blizzard's map pin there (and a
--                TomTom arrow, if TomTom is on); click the pin to clear it
--   search       type a zone, city, dungeon or flight master and glide to it (on the
--                window's title bar)
--   group        party and raid members as class-coloured dots with a gold
--                border, wherever they are on the stitched map (Blizzard's own
--                only show on the map underneath)
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local Look, Safe, L = ns.Look, ns.Safe, ns.L
local function Gold(line) return ns.GoldKeys and ns.GoldKeys(line) or line end   -- (a tooltip's keys in gold: Panel.lua)

local d = mod.defaults
d.group = true
d.tomtom = true      -- a waypoint followed on the map sets TomTom's too, if TomTom is on (#444)
d.waypointMeters = false   -- Blizzard's distance to the waypoint you follow, in meters (its arrow on the screen)

local map, sc


local function UnitMapPosition(unit, mapID)
	local pos = Safe.Call(C_Map.GetPlayerMapPosition, mapID, unit)
	if not pos then return end
	local x, y = Safe.XY(pos)
	if Safe.IsSecret(x) or Safe.IsSecret(y) or not x or not y or (x == 0 and y == 0) then return end
	return x, y
end

-- a unit's place on the world (normalized), or nil (secret, in an instance, unknown)
local function UnitWorld(unit)
	local best = Safe.Call(C_Map.GetBestMapForUnit, unit)
	if not best or not S.Rect(best) then return end
	local x, y = UnitMapPosition(unit, best)
	if not x then return end
	local u, v = mod.ToWorld(best, x, y)
	return u, v, best
end

--------------------------------------------------------------------------------
-- Find me, and reopening where you left off
--------------------------------------------------------------------------------

function mod.RememberOutsideInstance()
	local u, v, best = UnitWorld("player")
	-- No viewport needed: this also runs before the map's first opening.
	if u then mod.outsideInstanceView = { u, v, best } end
end

function mod:FindMe(keepZoom)
	if not mod.IsStitched() and not (mod.PadViewOn and mod.PadViewOn()) then return end
	local u, v, best = UnitWorld("player")
	if not u then
		-- the map underneath may still know (the zone you're in, shown)
		local host = mod.HostMap()
		local pos = host and Safe.Call(C_Map.GetPlayerMapPosition, host, "player")
		if pos then
			local x, y = Safe.XY(pos)
			if not Safe.IsSecret(x) and x and y and (x ~= 0 or y ~= 0) then u, v = mod.ToWorld(host, x, y) best = host end
		end
	end
	if not u then
		ns:Print(L["You aren't on the world map here (an instance or a place it doesn't cover)."])
		return
	end
	local _, _, zoom = mod.ViewNow()
	mod.Glide(u, v, keepZoom and zoom or math.max(zoom, mod.FitZoom(best)))
end

local saved                     -- { u, v, zoom, zone, host } when the map closed

function mod.GetReopenView()
	-- Preserve existing preferences, including the earlier two-checkbox setting.
	-- No default for reopenView: it would hide the old preference before migration.
	if not mod.db.reopenView then
		-- (a fresh install, nothing saved: on the player, as Blizzard's map opens)
		mod.db.reopenView = mod.db.rememberViewInView and "visible"
			or (mod.db.rememberView == true and "always" or "player")
	end
	if mod.db.reopenView == "zone" then mod.db.reopenView = "always" end
	mod.db.rememberView, mod.db.rememberViewInView = nil, nil
	return mod.db.reopenView
end

function mod:OnMapHidden()
	local u, v, zoom = mod.ViewNow()
	-- (never a view that isn't one, NaN: reopened on, it left the map blank, #260)
	if u and Safe.Finite(u, v, zoom) and zoom > 0 then saved = { u, v, zoom, Safe.Call(C_Map.GetBestMapForUnit, "player"), mod.HostMap() } end
end

-- the view to reopen on: restore the previous view when the selected condition holds,
-- otherwise centre on the player. Only for the map Blizzard opens on:
-- a map put up for something else (a quest's zone, from the quest log or the tracker) shows as
-- Blizzard shows it, or the view would move the map back and Blizzard would close the quest.
-- (No mapID: whether there's a view to reopen on at all. onlySaved: only a view saved when the map
-- closed, never the one on the player)
function mod.SavedView(mapID, onlySaved)
	local mode = mod.GetReopenView()
	local zone = Safe.Call(C_Map.GetBestMapForUnit, "player")
	local restore = saved and mode == "always"
	-- (nowhere to centre on, inside a dungeon: the view you left the map at, whatever the choice; the map
	-- opened at Blizzard's whole continent there each time, the world you'd browsed lost)
	if saved and not UnitWorld("player") then restore = true end
	if saved and mode == "visible" and not restore then
		local u, v = UnitWorld("player")
		if not u then return end
		local hu, hv = mod.ViewHalfExtents(saved[3])
		restore = math.abs(u - saved[1]) <= hu and math.abs(v - saved[2]) <= hv
	end
	-- (with "zoom", the zoom kept counts as saved: put back on the next frame too, as a saved view is)
	if onlySaved and not restore and not (saved and mode == "zoom") then return end
	local display = Safe.Call(MapUtil and MapUtil.GetDisplayableMapForPlayer)
	if restore then
		if mapID and mapID ~= saved[5] and mapID ~= zone and mapID ~= display then return end
		return saved[1], saved[2], saved[3]
	end
	if mapID and mapID ~= zone and mapID ~= display then return end
	-- (where your map fits, but never past the deepest zoom set: a city fits further in than that, its
	-- own extra half that the wheel can still go to; with "zoom", the zoom it closed at)
	local u, v, best = UnitWorld("player")
	if u and mode == "zoom" and saved then return u, v, saved[3] end   -- (the zoom it closed at)
	-- ("inzone": the whole zone you're in, in the middle, wherever you are in it: #143)
	if u and mode == "inzone" and best then
		local l, r, t, b = S.Rect(best)
		if l then return (l + r) / 2, (t + b) / 2, math.min(mod.FitZoom(best), mod.db.maxZoom or math.huge) end
	end
	if u then return u, v, math.min(mod.FitZoom(best), mod.db.maxZoom or math.huge) end
end

function mod:OnMapShown()
	-- (Blizzard's zoom reset on opening goes straight there, WorldMap.lua; this is for when
	-- Blizzard puts up another map after it, on the next frame: only if it's not there yet. Only a
	-- view saved as the map closed: centred on the player, the reset has done it, and moving the view
	-- again would have the map underneath follow it, away from a quest's zone the quest log put up)
	if not mod.SavedView(nil, true) then return end
	C_Timer.After(0, function()
		local d = QuestMapFrame and QuestMapFrame.DetailsFrame   -- (a quest's details up: they stay on its map, #224)
		if d and d:IsShown() then return end
		local u, v, zoom = mod.SavedView(mod.HostMap(), true)
		if not u or not mod.IsStitched() then return end
		local nu, nv, nz = mod.ViewNow()
		if nu and math.abs(nu - u) < 1e-4 and math.abs(nv - v) < 1e-4 and math.abs(nz - zoom) < 1e-3 then return end
		mod.ShowNow(u, v, zoom)
	end)
end

--------------------------------------------------------------------------------
-- Waypoints
--------------------------------------------------------------------------------

local wpSet, RefreshWaypoint
local WAYPOINT = { atlas = "Waypoint-MapPin-Tracked", texture = "Interface\\Minimap\\Ping\\ping5", size = 30 }

-- The waypoint being followed: Blizzard's user waypoint where the client takes it (its pin, its
-- arrow); else our own, kept per character (mod.char.pin). Either shows on the whole stitched map,
-- as its own marker unless it's on one of the map pins (Pins.lua), which then shows as tracked.
local function BlizzardPin()
	if not (C_Map.HasUserWaypoint and C_Map.GetUserWaypoint) then return end
	local ok, has = pcall(C_Map.HasUserWaypoint)
	if not ok or not has then return end
	local point = C_Map.GetUserWaypoint()
	if point and point.position then
		local x, y = Safe.XY(point.position)
		return point.uiMapID, x, y
	end
end

-- TomTom's waypoint for our pin (its AddWaypoint's handle): gone with the pin, or when another replaces it
local tomtomPoint
local function ClearTomTom()
	local tomtom = _G.TomTom
	if tomtomPoint and tomtom and tomtom.RemoveWaypoint then pcall(tomtom.RemoveWaypoint, tomtom, tomtomPoint) end
	tomtomPoint = nil
end

local function ClearPin()
	if C_Map.ClearUserWaypoint then pcall(C_Map.ClearUserWaypoint) end
	mod.char.pin = nil
	ClearTomTom()
	RefreshWaypoint()
end

-- our pin: a click removes it, a chat-link click (Shift) puts Blizzard's link to it in chat
local function PinClick()
	if IsModifiedClick and IsModifiedClick("CHATLINK") then
		local ok, link = pcall(C_Map.GetUserWaypointHyperlink or nop)
		if ok and link then
			local insert = (ChatFrameUtil and ChatFrameUtil.InsertLink) or ChatEdit_InsertLink
			if insert then insert(link) end
		end
		return
	end
	ClearPin()
end

-- On the stitched map the pin is always ours, never Blizzard's: a click on Blizzard's runs in
-- the map's code that OpenMap changes, and its Shift-click (copying a slash command to the
-- clipboard, which only Blizzard's UI may do) is then blocked, blaming OpenMap
-- (and, on a client whose map filter can show Blizzard's own dungeon entrances, retail's, those: the
-- stitched map has OpenMap's, from the same journal, which would show twice)
local function HideBlizzardPin()
	if not (mod.IsStitched and mod.IsStitched()) or not map or not map.EnumeratePinsByTemplate then return end
	for pin in map:EnumeratePinsByTemplate("WaypointLocationPinTemplate") do pin:Hide() end
	if ns.Client ~= "Forever" then
		for pin in map:EnumeratePinsByTemplate("DungeonEntrancePinTemplate") do pin:Hide() end
	end
end

-- Blizzard's own waypoint set on the stitched map (its Ctrl-click with "Ctrl-click drops a pin" off, #19, or
-- another addon's): put where the cursor is, on the zone there, and followed. Blizzard places it on the map
-- underneath, often a continent's, at the cursor clamped to that map's rectangle: on a continent's map the
-- game has no route to it, so it was set but never followed (no arrow, no distance). Only the waypoint, through
-- the game's own calls: nothing of Blizzard's map is touched
local zoning = false
function mod.ZoneWaypoint()
	if zoning or InCombatLockdown() or not (mod.IsStitched and mod.IsStitched()) or not map or not map:IsShown() then return end   -- (#295)
	local mapID, x, y = BlizzardPin()
	if not mapID or not x then return end
	local info = C_Map.GetMapInfo(mapID)
	local zoneType = Enum and Enum.UIMapType and Enum.UIMapType.Zone or 3
	if info and info.mapType and info.mapType >= zoneType then return end      -- (a zone's, or finer: as it is)
	local u, v
	if sc and sc:IsMouseOver() and mod.CursorWorld then u, v = mod.CursorWorld() end   -- (where the click was)
	if not u and mod.ToWorld and S.Rect(mapID) then u, v = mod.ToWorld(mapID, x, y) end
	if not u then return end
	local chain = S.ChainAt(u, v)
	local zone = chain and chain[#chain]
	if not zone or zone == S.WORLD or zone == mapID then return end
	if C_Map.CanSetUserWaypointOnMap and not C_Map.CanSetUserWaypointOnMap(zone) then return end
	local zx, zy = mod.FromWorld(zone, u, v)
	if not (zx and zy and zx >= 0 and zx <= 1 and zy >= 0 and zy <= 1 and UiMapPoint) then return end
	zoning = true
	local ok = pcall(C_Map.SetUserWaypoint, UiMapPoint.CreateFromCoordinates(zone, zx, zy))
	if ok and C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, true) end
	zoning = false
end

-- In a fight the map is OpenMap's own view (OwnView.lua): a Ctrl-click (with "Ctrl-click drops a pin" off) is
-- Blizzard's waypoint, which its canvas under the view never gets then: set here as Blizzard's would be, on the
-- zone under the cursor, and followed. True if set
function mod.OwnViewWaypoint()
	if not mod.CursorWorld then return false end
	local u, v = mod.CursorWorld()
	if not u then return false end
	local chain = S.ChainAt(u, v)
	local zone = chain and chain[#chain]
	if not zone or zone == S.WORLD then return false end
	if C_Map.CanSetUserWaypointOnMap and not C_Map.CanSetUserWaypointOnMap(zone) then return false end
	local zx, zy = mod.FromWorld(zone, u, v)
	if not (zx and zy and zx >= 0 and zx <= 1 and zy >= 0 and zy <= 1 and UiMapPoint) then return false end
	zoning = true
	-- (the waypoint itself as the fight ends: set from OpenMap's code in it, the tracker's redraw failed, #295)
	ns.OutOfCombat("waypoint", function()
		local ok = pcall(C_Map.SetUserWaypoint, UiMapPoint.CreateFromCoordinates(zone, zx, zy))
		if ok and C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, true) end
	end)
	zoning = false
	return ok
end

-- the waypoint now: map, x, y, and whether it's our own (not Blizzard's)
function mod.WaypointPoint()
	local mapID, x, y = BlizzardPin()
	if mapID then return mapID, x, y, false end
	local own = mod.char.pin
	if own then return own[1], own[2], own[3], true end
end

function RefreshWaypoint()
	if not wpSet then return end
	S.ClearPinSet(wpSet)
	if mod.RefreshPins then mod.RefreshPins() end
	local mapID, x, y, own = mod.WaypointPoint()
	HideBlizzardPin()
	if not mapID or not S.Rect(mapID) then return end
	if mod.PinAt and mod.PinAt(mapID, x, y) then return end   -- (the pin shows it, as tracked)
	local u, v = mod.ToWorld(mapID, x, y)
	local pin = S.AddPin(wpSet, u, v, WAYPOINT)
	pin:SetScript("OnEnter", function(self)
		GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
		local info = C_Map.GetMapInfo(mapID)
		GameTooltip:AddLine(L["Waypoint"], 1, 0.82, 0)
		GameTooltip:AddLine(("%s  %.1f, %.1f"):format(info and info.name or "", x * 100, y * 100), 1, 1, 1)
		GameTooltip:AddLine(Gold(L["Click: stop following it"]), 0.6, 0.6, 0.6)
		if not own then GameTooltip:AddLine(Gold(L["Shift-click: share in chat"]), 0.6, 0.6, 0.6) end
		GameTooltip:Show()
	end)
	pin:SetScript("OnLeave", GameTooltip_Hide)
	pin.OnClick = PinClick
end

-- the waypoint followed to a point on a map: Blizzard's if it takes it, else ours; and TomTom's.
-- `title`: TomTom's name for it (the map's name, else)
function mod.TrackPoint(mapID, x, y, title)
	local info = C_Map.GetMapInfo(mapID)
	local blizzard = false
	if C_Map.SetUserWaypoint and UiMapPoint and UiMapPoint.CreateFromCoordinates and not InCombatLockdown()   -- (#295)
		and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(mapID)) then
		blizzard = pcall(C_Map.SetUserWaypoint, UiMapPoint.CreateFromCoordinates(mapID, x, y)) and BlizzardPin() ~= nil
		if blizzard and C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, true) end
	end
	mod.char.pin = not blizzard and { mapID, x, y } or nil
	local tomtom = _G.TomTom
	ClearTomTom()
	if tomtom and tomtom.AddWaypoint and mod.db.tomtom ~= false then
		local name = (title and title ~= "") and title or (info and info.name) or "OpenMap"
		local ok, point = pcall(tomtom.AddWaypoint, tomtom, mapID, x, y, { title = name, from = "OpenMap" })
		if ok then tomtomPoint = point end
	end
	RefreshWaypoint()
end

-- Ctrl-click, or the menu's Drop a pin: a map pin there (Pins.lua: it's followed, and its note opens)
function mod.DropWaypoint(u, v)
	local chain = S.ChainAt(u, v)
	local mapID = chain[#chain]
	if mapID == S.WORLD then return end
	local x, y = mod.FromWorld(mapID, u, v)
	if mod.AddPin then mod.AddPin(mapID, x, y) else mod.TrackPoint(mapID, x, y) end
end

-- the pin button: the next click on the map drops a pin there (Ctrl-click always does)
-- the menu's pin button: the next click on the map drops a pin there (Ctrl-click always does)
local pinArmed = false
function mod.PinMode() return pinArmed end
function mod.SetPinMode(on)
	pinArmed = on and true or false
	if mod.SyncBlizzardPin then mod.SyncBlizzardPin(pinArmed) end
	if mod.OnPinMode then mod.OnPinMode(pinArmed) end
end
function mod.ClearPin() ClearPin() end         -- (the waypoint: no longer followed)
function mod.SetTomTomWaypoint(on)             -- (off: the one OpenMap set goes too)
	mod.db.tomtom = on and true or false
	if not on then ClearTomTom() end
end

--------------------------------------------------------------------------------
-- Search
--------------------------------------------------------------------------------

-- What it finds: the world's continents and zones, dungeons and raids, flight masters, battlegrounds (their own
-- map opens), boats and zeppelins, caves, the areas of each zone (Goldshire, the Crossroads ...), your map pins by
-- their notes; and with Questie, its database's NPCs, objects and quests (a quest: where it's given and handed in),
-- and its townsfolk by kind (Innkeepers ...: that kind turned on, Townsfolk.lua). Questie's tables are only read,
-- through its own queries, a few hundred a frame the first time the search is used, never written.
local places                    -- { name, lower, kind, u0, v0, u1, v1 } (u0 == u1: a point), or { pts = { { u, v } ... } },
                                -- or { open = uiMapID }, { show = townsfolk kind }, { q = "npc" | "object" | "quest", ids }
local box, list
local MAX_RESULTS = 12
local PER_KIND = 4              -- (so a word that's in hundreds of NPCs' names leaves room for the rest)
local MAX_PINGS = 40
local CHUNK = 400               -- Questie's records indexed a frame
-- the kinds' order in the list: places first, then what's at them
local RANK = {}
local function Rank(kind) return RANK[kind] or 50 end

local function Entry(name, kind, e)
	e = e or {}
	e.name, e.lower, e.kind = name, name:lower(), kind
	return e
end

local function Places()
	if places then return places end
	places = {}
	local seen = {}
	local function add(name, kind, u0, v0, u1, v1)
		if not name or name == "" or not u0 then return end
		local key = kind .. name
		if seen[key] then return end
		seen[key] = true
		places[#places + 1] = Entry(name, kind, { u0, v0, u1 or u0, v1 or v0 })
	end
	-- several places by one name (a route's docks): one entry, every place pinged
	local multi = {}
	local function addAt(name, kind, u, v)
		if not name or name == "" or not u then return end
		local key = kind .. name
		local e = multi[key]
		if not e then
			e = Entry(name, kind, { pts = {} })
			multi[key] = e
			places[#places + 1] = e
		end
		for _, p in ipairs(e.pts) do if math.abs(p[1] - u) < 1e-4 and math.abs(p[2] - v) < 1e-4 then return end end
		e.pts[#e.pts + 1] = { u, v }
	end
	for i, k in ipairs({ L["Continent"], L["Zone"], L["Battleground"], L["Dungeon"], L["Raid"], L["Area"], L["Cave"],
		L["Flight master"], L["Boat"], L["Zeppelin"], L["Airship"], L["Map pin"], L["Townsfolk"], L["NPC"], L["Quest"], L["Object"] }) do
		RANK[k] = RANK[k] or i
	end
	for _, kind in ipairs({ Enum.UIMapType.Continent, Enum.UIMapType.Zone }) do
		for _, info in ipairs(C_Map.GetMapChildrenInfo(S.WORLD, kind, true) or {}) do
			local l, r, t, b = S.Rect(info.mapID)
			if l then add(info.name, kind == Enum.UIMapType.Continent and L["Continent"] or L["Zone"], l, t, r, b) end
		end
	end
	local data = ns.MapPlaces or {}
	for _, g in ipairs(data.instances or {}) do
		local u, v
		if S.EntranceAt then u, v = S.EntranceAt(g) else u, v = S.FromYards(g[1], g[2], g[3]) end   -- (Dungeons.lua)
		if u then
			for _, inst in ipairs(g[4]) do add(S.InstanceName(inst), inst[3] and L["Raid"] or L["Dungeon"], u, v) end
		end
	end
	for _, node in pairs((ns.MapFlights or {}).nodes or {}) do
		local u, v = S.FromYards(node[2], node[3], node[4])
		add(node[1], L["Flight master"], u, v)
	end
	-- boats, zeppelins and airships by their route ("Booty Bay - Ratchet"): both docks (Data's transports)
	local TRANSPORT = { boat = L["Boat"], zeppelin = L["Zeppelin"], airship = L["Airship"] }
	for _, t in ipairs(data.transports or {}) do
		local kind = TRANSPORT[t[1]]
		if kind then
			addAt(t[2], kind, S.FromYards(t[3], t[4], t[5]))
			addAt(t[2], kind, S.FromYards(t[6], t[7], t[8]))
		end
	end
	-- caves (Blizzard's micro maps, Data's Caves): the middle of each
	for _, c in pairs(ns.MapCaves or {}) do
		addAt(c[1], L["Cave"], S.FromYards(c[2], (c[3] + c[5]) / 2, (c[4] + c[6]) / 2))
	end
	-- the areas of each zone, by the game's names (AreaTable): where to stand to explore them (Data's Explore), and
	-- the painted land of WoW Forever's own (Data's GapPlaces)
	local explore = ns.MapExplore
	if explore and explore.pieces and mod.ToWorld and C_Map.GetAreaInfo then
		local zoneOf = {}
		for ach, a in pairs(explore.achievements or {}) do zoneOf[ach] = a[1] end
		for _, pieces in pairs(explore.pieces) do
			for _, p in pairs(pieces) do
				local zone = zoneOf[p[1]]
				if zone and p[3] then
					local u, v = mod.ToWorld(zone, p[3], p[4])
					for _, area in ipairs(p[2] or {}) do add(C_Map.GetAreaInfo(area), L["Area"], u, v) end
				end
			end
		end
	end
	for _, g in ipairs(ns.MapGapPlaces or {}) do
		if g[4] then add(g[2], L["Area"], g[4][1], g[4][2]) end
	end
	-- battlegrounds: no place on the world, their own map opens (Battlegrounds.lua)
	for _, bg in ipairs(mod.BattlegroundPlaces and mod.BattlegroundPlaces() or {}) do
		places[#places + 1] = Entry(bg.name, L["Battleground"], { open = bg.mapID })
	end
	-- townsfolk by kind, from Questie (Townsfolk.lua): found, that kind is turned on
	if mod.TOWNSFOLK and mod.HasTownsfolk and mod.HasTownsfolk() then
		for _, k in ipairs(mod.TOWNSFOLK) do places[#places + 1] = Entry(k.name, L["Townsfolk"], { show = k.key }) end
	end
	return places
end

-- your map pins, by their notes (Pins.lua): read each time, they change
local function PinPlaces()
	local out = {}
	local db = mod.db.pins
	for _, p in ipairs(db and db.list or {}) do
		if p.note and p.note ~= "" and p.map and mod.ToWorld then
			local u, v = mod.ToWorld(p.map, p.x, p.y)
			if u then out[#out + 1] = Entry(p.note, L["Map pin"], { u, v, u, v }) end
		end
	end
	return out
end

-- Questie's database, if it's loaded: its NPCs', objects' and quests' names, indexed a chunk a frame
local QUESTIE_KIND = { npc = "NPC", object = "Object", quest = "Quest" }
local questie = { list = {}, state = nil }      -- state: nil (not begun), "building", "done", "none"
local function QuestieDBs()
	local loader = _G.QuestieLoader
	if not loader or type(loader.ImportModule) ~= "function" then return end
	local ok, db = pcall(loader.ImportModule, loader, "QuestieDB")
	local ok2, zones = pcall(loader.ImportModule, loader, "ZoneDB")
	if ok and ok2 and type(db) == "table" and type(zones) == "table" and db.QueryNPCSingle then return db, zones end
end
local ShowResults
local function IndexQuestie()
	if questie.state then return end
	local QDB = QuestieDBs()
	if not QDB or not QDB.NPCPointers then questie.state = "none" return end
	questie.state = "building"
	local todo = {}
	local function queue(kind, pointers, query)
		if type(pointers) ~= "table" or type(query) ~= "function" then return end
		for id in pairs(pointers) do todo[#todo + 1] = { kind, id, query } end
	end
	queue("npc", QDB.NPCPointers, QDB.QueryNPCSingle)
	queue("object", QDB.ObjectPointers, QDB.QueryObjectSingle)
	queue("quest", QDB.QuestPointers, QDB.QueryQuestSingle)
	local i, seen = 0, {}
	local function Step()
		local ok, err = pcall(function()
			for _ = 1, CHUNK do
				i = i + 1
				local t = todo[i]
				if not t then questie.state = "done" return end
				local kind, id, query = t[1], t[2], t[3]
				local name = query(id, "name")
				-- (only what has a place: an NPC or object with spawns, a quest with someone to give it)
				local where = query(id, kind == "quest" and "startedBy" or "spawns")
				if type(name) == "string" and name ~= "" and type(where) == "table" and next(where) then
					-- (one entry for every record of one name, as Questie keeps some: Spirit Healers, a quest of each
					-- faction's: all their places)
					local key = kind .. name
					local e = seen[key]
					if e then
						e.ids[#e.ids + 1] = id
					else
						e = Entry(name, L[QUESTIE_KIND[kind]], { q = kind, ids = { id } })
						seen[key] = e
						questie.list[#questie.list + 1] = e
					end
				end
			end
		end)
		if not ok then
			questie.state = "done"
			geterrorhandler()(err)
		end
		if box and box:HasFocus() and ShowResults then ShowResults() end
		if questie.state == "building" then C_Timer.After(0, Step) end
	end
	C_Timer.After(0, Step)
end
mod.IndexQuestieSearch = IndexQuestie

-- where a Questie record is on the world (normalized points): its spawns (an NPC that walks about, every point of
-- its path among them: the one nearest their middle), or a quest's givers' and hand-ins'
local WANDER = 6
local function Spawns(QDB, ZoneDB, spawns, out, walker)
	for areaID, coords in pairs(type(spawns) == "table" and spawns or {}) do
		local uiMapID = ZoneDB.GetUiMapIdByAreaId and ZoneDB:GetUiMapIdByAreaId(areaID)
		local l, r, t, b
		if uiMapID then l, r, t, b = S.Rect(uiMapID) end
		if l and type(coords) == "table" then
			local pts = {}
			for _, c in ipairs(coords) do
				if type(c) == "table" and c[1] and c[1] >= 0 then pts[#pts + 1] = { l + c[1] / 100 * (r - l), t + c[2] / 100 * (b - t) } end
			end
			if walker and #pts > WANDER then
				local su, sv = 0, 0
				for _, p in ipairs(pts) do su, sv = su + p[1], sv + p[2] end
				su, sv = su / #pts, sv / #pts
				table.sort(pts, function(a, b2) return (a[1] - su) ^ 2 + (a[2] - sv) ^ 2 < (b2[1] - su) ^ 2 + (b2[2] - sv) ^ 2 end)
				pts = { pts[1] }
			end
			for _, p in ipairs(pts) do out[#out + 1] = p end
		end
	end
	return out
end
local function QuestiePoints(e)
	local QDB, ZoneDB = QuestieDBs()
	if not QDB then return {} end
	local out = {}
	local function npcs(ids) for _, id in ipairs(type(ids) == "table" and ids or {}) do Spawns(QDB, ZoneDB, QDB.QueryNPCSingle(id, "spawns"), out, true) end end
	local function objects(ids)
		if not QDB.QueryObjectSingle then return end
		for _, id in ipairs(type(ids) == "table" and ids or {}) do Spawns(QDB, ZoneDB, QDB.QueryObjectSingle(id, "spawns"), out) end
	end
	if e.q == "npc" then
		npcs(e.ids)
	elseif e.q == "object" then
		objects(e.ids)
	elseif e.q == "quest" and QDB.QueryQuestSingle then
		-- (Questie's startedBy: { NPCs, objects, items }; finishedBy: { NPCs, objects })
		for _, id in ipairs(e.ids) do
			for _, by in ipairs({ QDB.QueryQuestSingle(id, "startedBy"), QDB.QueryQuestSingle(id, "finishedBy") }) do
				if type(by) == "table" then npcs(by[1]) objects(by[2]) end
			end
		end
	end
	-- (the same place twice, a giver who takes it in too: once)
	local once, seenAt = {}, {}
	for _, p in ipairs(out) do
		local key = math.floor(p[1] * 1e5) .. ":" .. math.floor(p[2] * 1e5)
		if not seenAt[key] then seenAt[key] = true once[#once + 1] = p end
	end
	return once
end

-- markers on what was found, for a few seconds
local pingSet, pingTimer
local PING = { atlas = "Waypoint-MapPin-Untracked", texture = "Interface\\Minimap\\Ping\\ping5", size = 30 }
local function Ping(pts)
	if not pingSet then return end
	S.ClearPinSet(pingSet)
	for i, p in ipairs(pts) do
		if i > MAX_PINGS then break end
		local pin = S.AddPin(pingSet, p[1], p[2], PING)
		pin:EnableMouse(false)
	end
	if pingTimer then pingTimer:Cancel() end
	pingTimer = C_Timer.NewTimer(5, function() S.ClearPinSet(pingSet) end)
end

-- the least box several places are shown in (normalized: about a small zone's size)
local MIN_SPAN = 0.012
local function GoTo(pts)
	if #pts == 0 then return false end
	if #pts == 1 then
		mod.Glide(pts[1][1], pts[1][2], math.max(14, select(3, mod.ViewNow()) or 1))
	else
		local u0, v0, u1, v1 = math.huge, math.huge, -math.huge, -math.huge
		for _, p in ipairs(pts) do
			u0, v0, u1, v1 = math.min(u0, p[1]), math.min(v0, p[2]), math.max(u1, p[1]), math.max(v1, p[2])
		end
		local du, dv = math.max(0, MIN_SPAN - (u1 - u0)) / 2, math.max(0, MIN_SPAN - (v1 - v0)) / 2
		S.GlideToRect(u0 - du, v0 - dv, u1 + du, v1 + dv, 0.8)
	end
	Ping(pts)
	return true
end

local function Go(p)
	box:ClearFocus()
	list:Hide()
	if p.open then
		S.OpenMap(p.open)
	elseif p.show then
		mod.db.townsfolk[p.show] = true
		if mod.RefreshTownsfolk then mod:RefreshTownsfolk() end
		if mod.RefreshPanel then mod:RefreshPanel() end
	elseif p.q then
		if not GoTo(QuestiePoints(p)) then ns:Print(L["Not on the map: %s"]:format(p.name)) end
	elseif p.pts then
		GoTo(p.pts)
	elseif p[1] == p[3] then
		GoTo({ { p[1], p[2] } })
	else
		S.GlideToRect(p[1], p[2], p[3], p[4], 0.95)
	end
end

local function Results(text)
	text = (text or ""):lower():gsub("^%s+", ""):gsub("%s+$", "")
	local found = {}
	if #text < 2 then return found end
	local function scan(entries)
		for _, p in ipairs(entries) do
			local at = p.lower:find(text, 1, true)
			if at then found[#found + 1] = { p, at == 1 and 0 or 1 } end
		end
	end
	scan(Places())
	scan(PinPlaces())
	scan(questie.list)
	-- the best first (a name starting so, then the shorter), at most PER_KIND of a kind; then grouped by kind
	table.sort(found, function(a, b)
		if a[2] ~= b[2] then return a[2] < b[2] end
		if #a[1].name ~= #b[1].name then return #a[1].name < #b[1].name end
		return a[1].name < b[1].name
	end)
	local out, per = {}, {}
	for _, f in ipairs(found) do
		local kind = f[1].kind
		if (per[kind] or 0) < PER_KIND then
			per[kind] = (per[kind] or 0) + 1
			out[#out + 1] = f
			if #out >= MAX_RESULTS then break end
		end
	end
	for i, f in ipairs(out) do f[3] = i end
	table.sort(out, function(a, b)
		local ra, rb = Rank(a[1].kind), Rank(b[1].kind)
		if ra ~= rb then return ra < rb end
		return a[3] < b[3]
	end)
	return out
end
mod.SearchResults = Results

local ROW_W = 260
function ShowResults()
	if not (box and list) then return end
	local found = Results(box:GetText())
	list.rows = list.rows or {}
	for _, row in ipairs(list.rows) do row:Hide() end
	if #found == 0 then list:Hide() return end
	for i = 1, math.min(#found, MAX_RESULTS) do
		local row = list.rows[i]
		if not row then
			row = CreateFrame("Button", nil, list)
			row:SetSize(ROW_W, 18)
			row:SetPoint("TOPLEFT", list.pad[1], -list.pad[2] - (i - 1) * 18)
			row:SetHighlightTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight", "ADD")
			row.kind = row:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
			row.kind:SetPoint("RIGHT", -4, 0)
			row.name = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
			row.name:SetPoint("LEFT", 4, 0)
			row.name:SetPoint("RIGHT", row.kind, "LEFT", -6, 0)
			row.name:SetJustifyH("LEFT")
			if row.name.SetWordWrap then row.name:SetWordWrap(false) end
			row:SetScript("OnClick", function(self) Go(self.place) end)
			list.rows[i] = row
		end
		row.place = found[i][1]
		row.name:SetText(found[i][1].name)
		row.kind:SetText(found[i][1].kind)
		row:Show()
	end
	list:SetHeight(list.pad[2] + list.pad[4] + math.min(#found, MAX_RESULTS) * 18)
	list:Show()
	list.first = found[1][1]
end

-- the search box, on `parent`, `width` wide; its results drop down below it, their right edge under its
-- (it sits at the window's right, by its buttons)
function mod.CreateSearch(parent, width)
	map = map or _G.WorldMapFrame
	box = CreateFrame("EditBox", nil, parent, "SearchBoxTemplate")
	box:SetSize(width, 20)
	box:SetAutoFocus(false)
	if box.Instructions then box.Instructions:SetText(L["Find a place"]) end
	list = CreateFrame("Frame", nil, parent)
	list:SetPoint("TOPRIGHT", box, "BOTTOMRIGHT", 6, -2)
	list:SetWidth(ROW_W + 20)
	list:SetFrameStrata("FULLSCREEN_DIALOG")      -- (over the menu's tiles below it: they're in its strata)
	list:EnableMouse(true)
	list.pad = { Look:Dropdown(list) }              -- (the game's own dropdowns' look)
	list:Hide()
	box:HookScript("OnTextChanged", function() IndexQuestie() ShowResults() end)
	box:HookScript("OnEditFocusGained", IndexQuestie)    -- (Questie's names indexed while you start typing)
	box:SetScript("OnEnterPressed", function() if list:IsShown() and list.first then Go(list.first) else box:ClearFocus() end end)
	box:HookScript("OnEscapePressed", function() list:Hide() end)
	box:HookScript("OnEditFocusLost", function() C_Timer.After(0.2, function() if not box:HasFocus() then list:Hide() end end) end)
	map:HookScript("OnHide", function() box:ClearFocus() list:Hide() end)
	return box
end

-- The search on the map's title bar, left of its window buttons (Blizzard's maximize and close): there whenever
-- OpenMap's map is, and nowhere else (Blizzard's own maps, the Gamepad UI's). As wide as the bar leaves it beside
-- the window's title, between these. Its frames are OpenMap's own, on the map as the title bar's drag strip is
-- (Window.lua), made out of combat; nothing of Blizzard's is written or moved
local SEARCH_MIN, SEARCH_MAX = 90, 190
local SEARCH_GAP = 10           -- from the title's text, and from the window's buttons
local holder
local function TitleText(border)
	local c = border.TitleContainer
	return (c and c.TitleText) or border.TitleText or (border.GetTitleText and border:GetTitleText()) or nil
end
local function SearchButtons(border)
	local mm = border.MaximizeMinimizeFrame
	if mm and mm.IsShown and mm:IsShown() then return mm end
	return border.CloseButton
end
-- how wide it can be: from the title's right end to the buttons
local function SearchWidth(border, buttons)
	local title = TitleText(border)
	local right = buttons and buttons.GetLeft and buttons:GetLeft()
	if not (title and right and title.GetCenter) then return SEARCH_MAX end
	local cx = title:GetCenter()
	local w = title.GetStringWidth and title:GetStringWidth() or 0
	if not cx or not w then return SEARCH_MAX end
	local room = right - (cx + w / 2) - 2 * SEARCH_GAP
	return math.max(SEARCH_MIN, math.min(SEARCH_MAX, math.floor(room)))
end
local function PlaceSearch()
	if not holder then return end
	local border = map.BorderFrame
	local buttons = SearchButtons(border)
	box:ClearAllPoints()
	if buttons then box:SetPoint("RIGHT", buttons, "LEFT", -SEARCH_GAP, 0) else box:SetPoint("TOPRIGHT", map, "TOPRIGHT", -80, -2) end
	local w = SearchWidth(border, buttons)
	if math.abs((box:GetWidth() or 0) - w) > 0.5 then box:SetWidth(w) end
	holder.placed = { map:GetWidth(), map:GetHeight(), buttons }
end
local function SearchShown()
	return map:IsShown() and mod.enabled and mod.IsStitched() and not (mod.PadViewOn and mod.PadViewOn()) or false
end
local function RefreshSearch()
	if not holder then return end
	local on = SearchShown()
	if not on and box:HasFocus() then box:ClearFocus() end
	if not on then list:Hide() end
	holder:SetShown(on)
	if not on then return end
	local p = holder.placed
	local border = map.BorderFrame
	if not p or p[1] ~= map:GetWidth() or p[2] ~= map:GetHeight() or p[3] ~= SearchButtons(border) then PlaceSearch() end
end
mod.RefreshTitleSearch = RefreshSearch

function mod.SetupTitleSearch(worldMap)
	map = map or worldMap
	if holder or box or not worldMap or not worldMap.BorderFrame then return end
	-- (made out of combat: the map is a protected window then)
	if InCombatLockdown() then
		local waiter = {}
		ns.RegisterEvent(waiter, "PLAYER_REGEN_ENABLED", function()
			ns.UnregisterEvent(waiter, "PLAYER_REGEN_ENABLED")
			mod.SetupTitleSearch(worldMap)
		end)
		return
	end
	holder = CreateFrame("Frame", nil, worldMap)
	holder:SetAllPoints(worldMap)
	holder:EnableMouse(false)
	-- (over the title bar's art and its drag strip, Window.lua's at the map's level + 5)
	local border = worldMap.BorderFrame
	local level = math.max(worldMap:GetFrameLevel() + 8, (border.GetFrameLevel and border:GetFrameLevel() or 0) + 3)
	holder:SetFrameLevel(level)
	mod.CreateSearch(holder, SEARCH_MAX)
	box:SetFrameLevel(level + 1)
	holder:Hide()
	-- (whether OpenMap's map is up, and the window's size and buttons, checked a few times a second while the map is
	-- open: they change with every map, full screen, the quest log, a drag of a corner)
	local watch = CreateFrame("Frame", nil, worldMap)
	local wait = 0
	watch:SetScript("OnUpdate", function(_, elapsed)
		wait = wait - elapsed
		if wait > 0 then return end
		wait = 0.2
		RefreshSearch()
	end)
	worldMap:HookScript("OnShow", RefreshSearch)
	RefreshSearch()
end

-- the key binding's: the map opened if it's closed, then the search typed into
function mod.FocusSearch()
	if not box then return end
	local function focus()
		RefreshSearch()
		if holder and holder:IsShown() then box:SetFocus() box:HighlightText() end
	end
	if map:IsShown() then focus() return end
	if InCombatLockdown() then return end          -- (as the menu's buttons: no opening the map in combat)
	ToggleWorldMap()
	C_Timer.After(0, function() if map:IsShown() then focus() end end)
end

--------------------------------------------------------------------------------
-- Group members
--------------------------------------------------------------------------------

local groupSet, groupLooks, groupPins = nil, {}, {}
local rosterWait = 0
local DOT = { atlas = "WhiteCircle-RaidBlips", texture = "Interface\\Minimap\\PartyRaidBlips" }
-- The gold edge distinguishes group dots from guild and friend dots (Friends.lua): thin, right round the
-- dot (a wide one round a dark gap read as a target: #158, #170)
local RING_TEXTURE = (ns.Media and ns.Media.path or "") .. "Textures\\GroupRing.tga"   -- (tools/icon/group_ring.py)
local RING_SIZE = 16
local ROUGH_ALPHA = 0.55            -- the dot of someone known only by zone
local ROUGH_SPREAD = 0.006          -- world (normalized): between those known only by zone, in the same zone

local RING_RETRY_WINDOW = 0.1
local nativeRings, nativeRingsUnavailable, ringHandoff

local function HideNativeRings()
	if nativeRings and nativeRings.frame:IsShown() then nativeRings.frame:Hide() end
end

local function NativeGroupPin(host)
	if nativeRingsUnavailable or not host or host == S.WORLD or not map or not map.EnumeratePinsByTemplate then return end
	for pin in map:EnumeratePinsByTemplate("GroupMembersPinTemplate") do
		if pin:IsVisible() and Safe.Call(pin.GetUiMapID, pin) == host then return pin end
	end
end

local function DrawNativeRings(stockPin, host, units, roster, size)
	local asset = RING_TEXTURE
	if not nativeRings then
		local canvas = map:GetCanvas()
		local frame = CreateFrame("UnitPositionFrame", nil, canvas)
		if frame:IsProtected() then error("ring frame is protected") end
		frame:Hide()
		local texture = frame:CreateTexture()
		texture:Hide()
		if texture:SetTexture(asset) == false then error("addon group ring texture unavailable") end
		frame:SetAllPoints(canvas)
		frame:EnableMouse(false)
		nativeRings = { frame = frame }
	end
	local state = nativeRings
	local frame = state.frame
	local strata = stockPin:GetFrameStrata()
	if frame:GetFrameStrata() ~= strata then frame:SetFrameStrata(strata) end
	-- The hollow rim sits under the native dot and player arrow.
	local level = math.max(0, stockPin:GetFrameLevel() - 1)
	if frame:GetFrameLevel() ~= level then frame:SetFrameLevel(level) end
	if state.host ~= host then
		frame:SetUiMapID(host)
		if frame:GetUiMapID() ~= host then error("ring frame did not accept the map ID") end
		state.host = host
	end
	if state.roster ~= roster or state.size ~= size then
		frame:ClearUnits()
		for _, unit in ipairs(units) do
			frame:AddUnit(unit, asset, size, size, 1, 1, 1, 1, 7, false)
		end
		frame:FinalizeUnits()
		state.roster, state.size = roster, size
	end
	state.stockPin, state.units = stockPin, units
	if not frame:IsShown() then frame:Show() end
end

local function TryNativeRings(stockPin, host, units, roster)
	if stockPin and not nativeRingsUnavailable and #units > 0 then
		local scale = map:GetCanvasScale()
		if scale and scale > 0 then
			local factor = mod.NativeGroupIconScale and mod.NativeGroupIconScale(stockPin) or 1
			local ok = pcall(DrawNativeRings, stockPin, host, units, roster, RING_SIZE * factor / scale)
			if ok then return true end
			nativeRingsUnavailable = true
		end
	end
	HideNativeRings()
	return false
end

local function GroupLook(unit)
	local _, class = UnitClass(unit)
	class = Safe.Value(class) or "PRIEST"
	local look = groupLooks[class]
	if not look then
		local c = (C_ClassColor and C_ClassColor.GetClassColor(class)) or (RAID_CLASS_COLORS and RAID_CLASS_COLORS[class])
		look = { atlas = DOT.atlas, texture = DOT.texture, size = 12, color = c and { c.r, c.g, c.b, 1 } or { 1, 1, 1, 1 } }
		groupLooks[class] = look
	end
	return look
end

-- In a fight the map is OpenMap's own view (OwnView.lua) and Blizzard's dots are on its canvas under it,
-- see-through then: your group is drawn on the view by frames of the same kind as Blizzard's, OpenMap's own,
-- which the game fills in as it does Blizzard's (from places it keeps from addons, too): the dots in Blizzard's
-- look and size, each in its class colour, and the gold rings under them; the names on hover, as Blizzard's give
local ownGroup                  -- { dots, rings, key }
local ownGroupFailed
local function OwnGroupFrame(parent)
	local f = CreateFrame("UnitPositionFrame", nil, parent)
	if f:IsProtected() then error("group frame is protected") end
	f:SetAllPoints(parent)
	f:EnableMouse(false)
	return f
end
local function HideOwnGroup()
	if not ownGroup then return end
	ownGroup.dots:Hide()
	ownGroup.rings:Hide()
	ownGroup.key, ownGroup.tip = nil, nil
	if GameTooltip:IsOwned(ownGroup.dots) then GameTooltip:Hide() end
end
local function OwnGroupTip(f)
	local units = { pcall(f.GetMouseOverUnits, f) }
	local names = {}
	for i = 2, units[1] and #units or 0 do
		local unit = Safe.Value(units[i])
		if type(unit) == "string" and not UnitIsUnit(unit, "player") then names[#names + 1] = Safe.Call(UnitName, unit) or "?" end
	end
	local tip = table.concat(names, "\n")
	if tip == ownGroup.tip then return end
	ownGroup.tip = tip
	if tip == "" then
		if GameTooltip:IsOwned(f) then GameTooltip:Hide() end
		return
	end
	GameTooltip:SetOwner(f, "ANCHOR_CURSOR_RIGHT")
	GameTooltip:SetText(tip)
end
local function DrawOwnGroup(stockPin, host, members)
	local parent, scale, level, strata = mod.OwnCanvas()
	if not ownGroup then
		ownGroup = { dots = OwnGroupFrame(parent), rings = OwnGroupFrame(parent) }
		ownGroup.dots:SetScript("OnUpdate", OwnGroupTip)
	end
	local g = ownGroup
	local party, factor = mod.GroupDotSize(stockPin, "party")
	local raidSize = mod.GroupDotSize(stockPin, "raid")
	local inRaid = IsInRaid() and true or false
	local roster = {}
	for _, unit in ipairs(members) do roster[#roster + 1] = unit .. "=" .. (Safe.Call(UnitGUID, unit) or "") end
	local key = table.concat(roster, " ") .. "|" .. host .. "|" .. scale .. "|" .. tostring(party) .. "|" .. tostring(raidSize)
	g.rings:SetFrameStrata(strata)
	g.dots:SetFrameStrata(strata)
	g.rings:SetFrameLevel(math.min(9900, level + 1))
	g.dots:SetFrameLevel(math.min(9900, level + 2))
	if g.key ~= key then
		g.key = nil
		local ring = RING_SIZE * (factor or 1) / scale
		for _, f in ipairs({ g.rings, g.dots }) do
			f:SetUiMapID(host)
			f:ClearUnits()
		end
		for _, unit in ipairs(members) do
			-- (never you: your arrow is OpenMap's own in a fight)
			local you = Safe.Call(UnitIsUnit, unit, "player")
			local sub = not inRaid or Safe.Call(UnitInSubgroup, unit)
			local size = not you and (sub and party or raidSize)
			if size then
				local c = GroupLook(unit).color                -- (its class colour, as OpenMap's own dots)
				local r, gr, b = c[1], c[2], c[3]
				local atlas = (inRaid and sub) and "WhiteDotCircle-RaidBlips" or "WhiteCircle-RaidBlips"
				g.dots:AddUnit(unit, atlas, size / scale, size / scale, r, gr, b, 1, 7, false)
			end
			if not you then g.rings:AddUnit(unit, RING_TEXTURE, ring, ring, 1, 1, 1, 1, 7, false) end
		end
		g.rings:FinalizeUnits()
		g.dots:FinalizeUnits()
		g.key = key
	end
	g.rings:Show()
	g.dots:Show()
	return true
end
-- true when the game draws your group on the own view (on a zone's or continent's map: Blizzard's own dots
-- are on those only)
local function TryOwnGroup(stockPin, host, members)
	if ownGroupFailed or not stockPin or not host or host == S.WORLD or #members == 0 or not mod.OwnCanvas()
		or not mod.GroupDotSize then
		HideOwnGroup()
		return false
	end
	local ok = pcall(DrawOwnGroup, stockPin, host, members)
	if ok then return true end
	ownGroupFailed = true
	HideOwnGroup()
	return false
end

local function Ring(pin)
	if pin.Ring then return end
	pin.Ring = pin:CreateTexture(nil, "BACKGROUND")
	pin.Ring:SetSize(RING_SIZE, RING_SIZE)
	pin.Ring:SetPoint("CENTER")
	pin.Ring:SetTexture(RING_TEXTURE)
end


local function ShowGroupTooltip(pin, name)
	pin.tooltipName = name
	GameTooltip:ClearLines()
	GameTooltip:AddLine(name, 1, 1, 1)
	GameTooltip:AddLine(L["Group"], 1, 0.82, 0)
	local info = pin.zone and C_Map.GetMapInfo(pin.zone)
	if info and info.name then GameTooltip:AddLine(L["Somewhere in %s"]:format(info.name), 0.6, 0.6, 0.6) end
	GameTooltip:Show()
end

local function GroupEnter(pin)
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	ShowGroupTooltip(pin, Safe.Call(UnitName, pin.unit) or "?")
end

local function GroupLeave(pin)
	if GameTooltip:IsOwned(pin) then GameTooltip:Hide() end
end

-- where a group member is: u, v on the world when that's known (the game's, or the place they
-- share with OpenMap: on this client the game can keep a group member's place secret), else
-- nil, nil and the zone they're in (the game's, or as the guild roster and friends lists give it).
local function GroupPlace(unit)
	local u, v = UnitWorld(unit)
	if u then return u, v end
	local name, rlm = UnitName(unit)
	local zone
	u, v, zone = mod.FriendPlace(Safe.Value(name), Safe.Value(rlm))
	if u then return u, v end
	local best = Safe.Call(C_Map.GetBestMapForUnit, unit)
	if best and S.Rect(best) then zone = best end
	return nil, nil, zone
end

-- whether Blizzard's own dot, at the true place, already shows someone in this zone: the map
-- underneath is the zone or one it lies in (none on the whole-world map)
local function BlizzardShows(zone, host)
	if not host or host == S.WORLD then return false end
	while zone and zone ~= 0 do
		if zone == host then return true end
		local info = C_Map.GetMapInfo(zone)
		zone = info and info.parentMapID
	end
	return false
end

-- the n-th known only by this zone: rows of five just below its middle, clear of its friends badge
local function ZoneSpot(zone, n)
	local l, r, t, b = S.Rect(zone)
	local col, row = (n - 1) % 5, math.floor((n - 1) / 5)
	return (l + r) / 2 + col * ROUGH_SPREAD, (t + b) / 2 + (row + 1) * ROUGH_SPREAD
end

local function UpdateGroupPin(pin, unit, u, v, zone)
	local look = GroupLook(unit)
	local zoneChanged = not pin or pin.zone ~= zone
	if not pin then
		pin = S.AddPin(groupSet, u, v, look)
		Ring(pin)
		pin:SetScript("OnEnter", GroupEnter)
		pin:SetScript("OnLeave", GroupLeave)
		pin:SetScript("OnHide", GroupLeave)
	else
		S.MovePin(groupSet, pin, u, v)
		if pin.look ~= look then
			pin.look = look
			S.Look(pin.Icon, look)
			S.Look(pin.Highlight, look)
		end
	end
	pin.unit, pin.zone = unit, zone
	if zoneChanged then pin.Icon:SetAlpha(zone and ROUGH_ALPHA or 1) end
	if GameTooltip:IsShown() and GameTooltip:IsOwned(pin) then
		local name = Safe.Call(UnitName, unit) or "?"
		if zoneChanged or name ~= pin.tooltipName then ShowGroupTooltip(pin, name) end
	end
	return pin
end

local function RingRetryDeadline(unit, host, id, previous, now, handoffDeadline)
	if not previous or previous.id ~= id then return end
	-- Keep the deadline through repeated misses. An exact position clears it.
	local expires = previous.expires or now + RING_RETRY_WINDOW
	if handoffDeadline then expires = math.min(expires, handoffDeadline) end
	if expires <= now then return end
	local u, v = UnitWorld(unit)
	if u then
		local l, r, t, b = S.Rect(host)
		if not l or u < l or u > r or v < t or v > b then return end
	end
	rosterWait = math.min(rosterWait, 0.02, expires - now)
	return expires
end

local function RefreshGroup(afterMapChange)
	if not groupSet then return end
	-- (the controller view, PadView.lua: Blizzard's map underneath unseen, so every one of them here)
	local padView = mod.PadViewOn and mod.PadViewOn()
	if not mod.db.group or not (mod.IsStitched() or padView) or not IsInGroup() then
		ringHandoff = nil
		if nativeRings then nativeRings.members = nil end
		HideNativeRings()
		HideOwnGroup()
		S.ClearPinSet(groupSet)
		wipe(groupPins)
		return
	end
	local host = not padView and mod.HostMap() or nil
	local now = GetTime()
	if ringHandoff and (ringHandoff.host ~= host or now >= ringHandoff.expires) then ringHandoff = nil end
	local raid = IsInRaid()
	local stockPin = NativeGroupPin(host)
	if afterMapChange and ringHandoff and not stockPin then
		HideNativeRings()
		return
	end
	local previous = nativeRings and nativeRings.host == host and nativeRings.members
	local handoffDeadline
	if not previous and ringHandoff then
		previous, handoffDeadline = ringHandoff.members, ringHandoff.expires
	end
	local members, eligible, units, roster = {}, {}, {}, {}
	for i = 1, raid and 40 or 4 do
		local unit = (raid and "raid" or "party") .. i
		if UnitExists(unit) and not UnitIsUnit(unit, "player") then
			members[#members + 1] = unit
			if stockPin then
				local x, y = UnitMapPosition(unit, host)
				local onMap = x and x >= 0 and x <= 1 and y >= 0 and y <= 1
				local prior = not x and previous and previous[unit]
				if onMap or prior then
					local guid = Safe.Call(UnitGUID, unit)
					local id = guid or unit
					local expires = prior and RingRetryDeadline(unit, host, id, prior, now, handoffDeadline)
					if onMap or expires then
						eligible[unit] = { id = id, expires = expires or nil }
						units[#units + 1] = unit
						roster[#roster + 1] = unit .. "=" .. (guid or "")
					end
				end
			end
		end
	end
	local hasNativeRings
	if mod.OwnViewOn and mod.OwnViewOn() then
		-- (in a fight: the game's dots on OpenMap's own view, for everyone in a zone that's on this map; the rest,
		-- elsewhere, OpenMap's dots as ever)
		HideNativeRings()
		hasNativeRings = TryOwnGroup(stockPin, host, members)
		eligible = {}
		for _, unit in ipairs(members) do
			local best = Safe.Call(C_Map.GetBestMapForUnit, unit)
			if not best or BlizzardShows(best, host) then eligible[unit] = true end
		end
		if nativeRings then nativeRings.members = nil end
	else
		HideOwnGroup()
		hasNativeRings = TryNativeRings(stockPin, host, units, table.concat(roster, " "))
		if nativeRings then nativeRings.members = hasNativeRings and eligible or nil end
	end
	local inZone, seen = {}, {}
	for _, unit in ipairs(members) do
		if not (hasNativeRings and eligible[unit]) then
			-- Keep the stitched pins where the native map cannot place the member.
			local u, v, zone = GroupPlace(unit)
			if zone and not u and not BlizzardShows(zone, host) then
				inZone[zone] = (inZone[zone] or 0) + 1
				u, v = ZoneSpot(zone, inZone[zone])
			end
			if u then
				local id = Safe.Call(UnitGUID, unit) or unit
				groupPins[id] = UpdateGroupPin(groupPins[id], unit, u, v, zone)
				groupPins[id].openmapNoPress = true   -- (PadView.lua: nothing to press, the controller's A zooms in under it)
				seen[id] = true
			end
		end
	end
	for id, pin in pairs(groupPins) do
		if not seen[id] then
			S.RemovePin(groupSet, pin)
			groupPins[id] = nil
		end
	end
end

--------------------------------------------------------------------------------

-- Match Blizzard's icon size and draw level as its map zooms.
function mod.RefreshNativeRingLayout()
	local state = nativeRings
	if not state or not state.frame:IsShown() then return end
	local stockPin = state.stockPin
	if not mod.db.group or not IsInGroup() or mod.HostMap() ~= state.host or not stockPin:IsVisible()
		or Safe.Call(stockPin.GetUiMapID, stockPin) ~= state.host then
		HideNativeRings()
		rosterWait = 0
	elseif not TryNativeRings(stockPin, state.host, state.units, state.roster) then
		RefreshGroup()
	end
end

function mod.RefreshWaypoint() RefreshWaypoint() end   -- (PadView.lua: it has no SetupNav)
function mod.RefreshGroup() RefreshGroup() end         -- (PadView.lua: its own ticker; OwnView.lua, as it comes and goes)

function mod:BuildNav()
	wpSet = S.PinSet("waypoint", 0, 5)
	pingSet = S.PinSet("ping", 0, 5)
	groupSet = S.PinSet("group", 0, 4)
	RefreshWaypoint()
end

local function RefreshNav()
	RefreshWaypoint()
	local host = mod.HostMap()
	if host and host ~= S.WORLD and nativeRings and nativeRings.host ~= host and nativeRings.members then
		-- A native dot can already be on the new map while the Lua position catches up.
		ringHandoff = { host = host, members = nativeRings.members, expires = GetTime() + RING_RETRY_WINDOW }
	end
	if map:IsShown() then RefreshGroup(true) end
	rosterWait = 0
end

function mod:SetupNav(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	map:HookScript("OnHide", function()
		ringHandoff = nil
		if nativeRings then nativeRings.members = nil end
		HideNativeRings()
	end)
	if type(map.OnMapChanged) == "function" then
		-- Blizzard's providers have switched their pins by the time this hook runs.
		hooksecurefunc(map, "OnMapChanged", function()
			local ok, err = pcall(RefreshNav)
			if not ok then geterrorhandler()(err) end
		end)
	end
	if type(map.OnCanvasScaleChanged) == "function" then
		hooksecurefunc(map, "OnCanvasScaleChanged", mod.RefreshNativeRingLayout)
	end
	ns.RegisterEvent(mod, "USER_WAYPOINT_UPDATED", function() mod.ZoneWaypoint() RefreshWaypoint() end)
	ns.RegisterEvent(mod, "SUPER_TRACKING_CHANGED", RefreshWaypoint)
	-- Blizzard's pin comes back each time its provider redraws (the waypoint set, the map changed)
	-- (found by a method only it has: asking each provider its pin template errors on some, the
	-- vignettes' takes an argument)
	local entrances = _G.DungeonEntranceDataProviderMixin
	for provider in pairs(map.dataProviders or {}) do
		if type(provider) == "table" and provider.RefreshAllData and (provider.OnWayPointLocationToggleUpdate
			or ns.Client ~= "Forever" and entrances and provider.RefreshAllData == entrances.RefreshAllData) then
			hooksecurefunc(provider, "RefreshAllData", HideBlizzardPin)
		end
	end
	rosterWait = 0
	map:HookScript("OnShow", function()
		RefreshGroup()
		rosterWait = 0 -- check again on the first update in case the host map changes while opening
	end)
	local ticker = CreateFrame("Frame", nil, map)
	ticker:SetScript("OnUpdate", function(_, elapsed)
		rosterWait = rosterWait - elapsed
		if rosterWait > 0 then return end
		rosterWait = 0.5
		RefreshGroup()
	end)
	-- (the waypoint arrow's distance in meters: its frame may come later than this, so tried as the world loads too)
	if not mod.SetupWaypointMeters() then
		local waiter = {}
		ns.RegisterEvent(waiter, "PLAYER_ENTERING_WORLD", function()
			if mod.SetupWaypointMeters() then ns.UnregisterEvent(waiter, "PLAYER_ENTERING_WORLD") end
		end)
	end
	mod.SetupTitleSearch(map)
end

--------------------------------------------------------------------------------
-- The waypoint's distance in meters: Blizzard's arrow on the screen (SuperTrackedFrame) writes "123 yds" every
-- frame (UpdateDistanceText); after it, only its text is written again, in meters. Nothing else of Blizzard's is
-- written (not the IN_GAME_NAVIGATION_RANGE text, no field of the frame), from a secure hook; a distance the game
-- keeps secret is left as Blizzard wrote it. A client without that method or text: nothing happens
--------------------------------------------------------------------------------

local YARD = 0.9144
local metersHooked = false
local function MetersText(yards)
	local m = yards * YARD
	if m >= 1000 then return L["%.1f km"]:format(m / 1000) end
	return L["%d m"]:format(math.floor(m + 0.5))
end
mod.WaypointMetersText = MetersText
local function Meters(frame)
	if not mod.db.waypointMeters then return end
	local fs = frame and frame.DistanceText
	if not (fs and fs.IsShown and fs:IsShown() and fs.SetText) then return end
	local yards = C_Navigation and Safe.Call(C_Navigation.GetDistance)
	if type(yards) ~= "number" or yards <= 0 or not Safe.Finite(yards) then return end
	fs:SetText(MetersText(yards))
end
function mod.SetupWaypointMeters()
	if metersHooked then return true end
	local frame = _G.SuperTrackedFrame
	if type(frame) ~= "table" or type(frame.UpdateDistanceText) ~= "function" or type(frame.DistanceText) ~= "table" then return false end
	metersHooked = true
	hooksecurefunc(frame, "UpdateDistanceText", Meters)
	return true
end

function mod:NavOptions(opts, get, set, off)
	opts.reopenView = { type = "select", name = L["When reopening the map"], order = 11,
		get = mod.GetReopenView, set = set, disabled = off,
		values = { player = L["Center on player"], zoom = L["Center on player, keep zoom"], inzone = L["Center on your zone"],
			always = L["Always remember"], visible = L["Remember while visible"] }, sorting = { "player", "zoom", "inzone", "always", "visible" },
		desc = L["Choose one behavior. Center on player: always open on you. Center on player, keep zoom: open on you, at the zoom you closed the map at. Center on your zone: open on the whole zone you're in, wherever you are in it. Always remember: restore your previous position and zoom, even after changing zones. Remember while visible: restore only if your current location is inside the previous view, even across zone boundaries. Otherwise, open on you. Maps opened for a quest still show the quest's area."] }
	opts.group = { type = "toggle", name = L["Party and raid members"], order = 35, get = get, set = set, disabled = off,
		desc = L["Class-coloured dots for your group anywhere on the stitched map."] }
	opts.tomtom = { type = "toggle", name = L["TomTom waypoint too"], order = 35.92, width = "full", disabled = off,
		get = function() return mod.db.tomtom ~= false end, set = function(_, v) mod.SetTomTomWaypoint(v) end,
		hidden = function() return not (_G.TomTom and TomTom.AddWaypoint) end,
		desc = L["A pin you follow on the map sets TomTom's waypoint and arrow as well as Blizzard's."] }
	opts.waypointMeters = { type = "toggle", name = L["Waypoint distance in meters"], order = 35.93, width = "full", get = get,
		set = function(info, v) set(info, v) mod.SetupWaypointMeters() end,
		desc = L["The distance under the game's waypoint arrow on your screen, in meters (km from 1000) instead of yards."] }
end
