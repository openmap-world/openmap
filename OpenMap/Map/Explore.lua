--------------------------------------------------------------------------------
-- Places to explore (the menu's "Show places to explore", off until turned on): for each zone's
-- "Explore <zone>" achievement, the pieces of the zone's map you haven't explored yet, each with a
-- soft gold outline of the ground that explores it and a pin where to go (ns.MapExplore, from
-- tools/map-data/explore.py). Further out, each zone with places left shows how many.
--   pieces   the map's own (Stitch.lua's S.Pieces): what's explored is what the map draws as explored
--   cheap    a zone's outlines and pins are made only once it's in view at the zoom they show from,
--            and made again only when something there is explored; nothing while the map is closed
-- WoW Forever's toc only: a client without Explore.lua's data has no option and nothing drawn.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local L = ns.L
local DATA = ns.MapExplore

mod.defaults.explore = false    -- places still to explore for each zone's Explore achievement

if not DATA then return end

local ZONE_FROM = 3             -- zoom the outlines and pins show from; the zones' counts until then
local GOLD = { 1, 0.82, 0.25 }
local LINE, LINE_ALPHA = 2, 0.55   -- the outline: px on screen, alpha
local SPOT = { atlas = "WhiteCircle-RaidBlips", texture = "Interface\\Buttons\\WHITE8X8", size = 12, color = { GOLD[1], GOLD[2], GOLD[3], 0.95 } }
local COUNT = { atlas = "WhiteCircle-RaidBlips", texture = "Interface\\Buttons\\WHITE8X8", size = 20, color = { 0.12, 0.09, 0.04, 0.85 } }

local zones = {}                -- mapID -> { ach, art, keys = { key, ... }, set, dirty }
for ach, a in pairs(DATA.achievements) do
	local keys = {}
	for key in pairs(DATA.pieces[a[2]] or {}) do keys[#keys + 1] = key end
	table.sort(keys)
	zones[a[1]] = { mapID = a[1], ach = ach, art = a[2], keys = keys, dirty = true }
end
local counts                    -- the zones' counts (a pin set), further out
local view                      -- the last view: { u, v, hu, hv, zoom }

local function On() return mod.db and mod.db.explore and S.IsBuilt() end

-- whether a piece is still unexplored: the game's own list of what's explored, asked each time a zone's
-- outlines or counts are made. (Not the map's pieces, S.Pieces: they're set as the map is built, at login,
-- before the game may have sent what you've explored, and only flipped by a later exploring: a zone you'd
-- long explored stayed unexplored here, 3/25 for the Barrens, #417 #418)
--
-- The game's pieces aren't always Explore.lua's: its keys are the pieces of the zones' older art (Elwynn's
-- 1228), the achievements' own, while the game draws most zones with a newer art (2153) and lists that art's
-- pieces: the same places, at the same offsets or a few px off, in other sizes. Matched on the whole key,
-- Elwynn's 12 explored read 6/12 and Tirisfal's 16 read 0/16 (#445 #478). So a piece is explored when the
-- game lists it, or one at its place, or says its own ground is explored where its pin is (a piece redrawn
-- somewhere else: two of Alterac's, one each of Hillsbrad's, Desolace's and Stranglethorn's)
local NEAR = 8                  -- px a piece's corner may sit from its place in the zone's other art (3 at the most, then 20 and up)
local exploredNow = {}          -- mapID -> { key = true, at = { { x, y }, ... }, loose = { key = found } }, for the making in hand (Fresh empties it)
local function Fresh() wipe(exploredNow) end
local function GroundExplored(mapID, p)
	local at = C_MapExplorationInfo.GetExploredAreaIDsAtPosition
	if not at or not CreateVector2D then return false end
	local ok, areas = pcall(at, mapID, CreateVector2D(p[3], p[4]))
	if not ok or type(areas) ~= "table" then return false end
	for _, area in ipairs(areas) do
		for _, own in ipairs(p[2]) do
			if area == own then return true end
		end
	end
	return false
end
local function Unexplored(mapID, key)
	local now = exploredNow[mapID]
	if not now then
		now = { at = {}, loose = {} }
		for _, info in ipairs(C_MapExplorationInfo.GetExploredMapTextures(mapID) or {}) do
			now[info.textureWidth .. ":" .. info.textureHeight .. ":" .. info.offsetX .. ":" .. info.offsetY] = true
			now.at[#now.at + 1] = { info.offsetX, info.offsetY }
		end
		exploredNow[mapID] = now
	end
	if now[key] then return false end
	local found = now.loose[key]
	if found == nil then
		found = false
		local _, _, x, y = strsplit(":", key)
		x, y = tonumber(x), tonumber(y)
		for _, at in ipairs(now.at) do
			if math.abs(at[1] - x) <= NEAR and math.abs(at[2] - y) <= NEAR then found = true break end
		end
		local z = zones[mapID]
		local p = not found and z and DATA.pieces[z.art][key]
		if p then found = GroundExplored(mapID, p) end
		now.loose[key] = found
	end
	return not found
end

-- a zone's explored pieces and its whole count
local function Progress(mapID)
	local z = zones[mapID]
	local done = 0
	for _, key in ipairs(z.keys) do
		if not Unexplored(mapID, key) then done = done + 1 end
	end
	return done, #z.keys
end

local function Title(z)
	local _, name = GetAchievementInfo(z.ach)
	if name then return name end
	local info = C_Map.GetMapInfo(z.mapID)
	return info and info.name or "?"
end

local function ProgressLine(mapID)
	local done, all = Progress(mapID)
	GameTooltip:AddLine(("%s %d/%d"):format(Title(zones[mapID]), done, all), 1, 1, 1)
end

local function SpotEnter(pin)
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	local info = C_Map.GetAreaInfo(pin.area)
	GameTooltip:AddLine(info or "?", GOLD[1], GOLD[2], GOLD[3])
	ProgressLine(pin.mapID)
	GameTooltip:Show()
end

local function CountEnter(pin)
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	local info = C_Map.GetMapInfo(pin.mapID)
	GameTooltip:AddLine(info and info.name or "?", GOLD[1], GOLD[2], GOLD[3])
	ProgressLine(pin.mapID)
	GameTooltip:Show()
end

-- an outline's points, decoded (explore.py's enc: two base-64 characters a position)
local B64 = {}
do
	local chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
	for i = 1, #chars do B64[chars:byte(i)] = i - 1 end
end
local function Decode(s, i)
	return ((B64[s:byte(i)] or 0) * 64 + (B64[s:byte(i + 1)] or 0)) / 4095 * 1.25 - 0.125
end

-- a zone's outlines and pins, for the pieces it has still to explore
local function BuildZone(mapID, z)
	z.dirty = false
	exploredNow[mapID] = nil
	local set = z.set or S.PinSet("explore" .. mapID, ZONE_FROM, 2)
	z.set = set
	S.ClearPinSet(set)
	local l, r, t, b = S.Rect(mapID)
	if not l then return end
	local w, h = r - l, b - t
	for _, key in ipairs(z.keys) do
		local p = DATA.pieces[z.art][key]
		if Unexplored(mapID, key) then
			for loop in (p[5] or ""):gmatch("%S+") do
				local pts = {}
				for i = 1, #loop - 3, 4 do
					pts[#pts + 1] = l + Decode(loop, i) * w
					pts[#pts + 1] = t + Decode(loop, i + 2) * h
				end
				pts[#pts + 1], pts[#pts + 2] = pts[1], pts[2]          -- (round to its start)
				S.AddPath(set, pts, LINE, GOLD[1], GOLD[2], GOLD[3], LINE_ALPHA)
			end
			local pin = S.AddPin(set, l + p[3] * w, t + p[4] * h, SPOT)
			pin.area, pin.mapID = p[2][1], mapID
			pin:SetScript("OnEnter", SpotEnter)
			pin:SetScript("OnLeave", GameTooltip_Hide)
		end
	end
end

-- the zones' counts of places left, at their middles (cheap: one pin a zone, made again on a change)
local function BuildCounts()
	counts = counts or S.PinSet("exploreCount", 1, 2)
	counts.maxZoom = ZONE_FROM
	S.ClearPinSet(counts)
	for mapID in pairs(zones) do
		local done, all = Progress(mapID)
		local l, r, t, b = S.Rect(mapID)
		if l and done < all then
			local pin = S.AddPin(counts, (l + r) / 2, (t + b) / 2, COUNT)
			if not pin.omCount then
				pin.omCount = pin:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
				pin.omCount:SetPoint("CENTER")
			end
			pin.omCount:SetText(all - done)
			pin.omCount:Show()
			pin.mapID = mapID
			pin:SetScript("OnEnter", CountEnter)
			pin:SetScript("OnLeave", GameTooltip_Hide)
		end
	end
end

-- the zones in view at the zoom they show from: made (when new or explored since) and shown; the rest off.
-- Out of view, a zone's outlines are kept only up to KEEP_LINES in all, the longest out of view let go first
-- (made again when it's back): every one kept, each zone toured had its lines laid out again on every frame of
-- each zoom and pan (thousands: #411 #413 #419), and their anchors on the art's frame overflowed the stack
-- when its regions were read (#414). Kept a while, a zoom in and back out doesn't make them all again
local KEEP_LINES = 1500
local tick = 0
local function Let(z)
	S.ClearPinSet(z.set)
	z.dirty = true
end
local function Update()
	if not view then return end
	local u, v, hu, hv, zoom = view[1], view[2], view[3], view[4], view[5]
	local near = (zoom or 0) >= ZONE_FROM * 0.8
	tick = tick + 1
	local kept, oldest = 0, {}
	for mapID, z in pairs(zones) do
		local l, r, t, b = S.Rect(mapID)
		local here = near and l and r > u - hu and l < u + hu and b > v - hv and t < v + hv or false
		if here and z.dirty then BuildZone(mapID, z) end
		if z.set and z.set.on ~= here then S.SetPinSetOn(z.set, here) end
		if here then z.seen = tick end
		if z.set and not z.dirty then
			kept = kept + #z.set.lines
			if not here then oldest[#oldest + 1] = z end
		end
	end
	if kept <= KEEP_LINES then return end
	table.sort(oldest, function(a, b) return (a.seen or 0) < (b.seen or 0) end)
	for _, z in ipairs(oldest) do
		if kept <= KEEP_LINES then break end
		kept = kept - #z.set.lines
		Let(z)
	end
end

-- everything off (the option off)
local function Off()
	for _, z in pairs(zones) do
		if z.set then
			if z.set.on then S.SetPinSetOn(z.set, false) end
			if not z.dirty then Let(z) end
		end
	end
	if counts and counts.on then S.SetPinSetOn(counts, false) end
end

-- the option, or what's explored, changed: made again as each zone comes into view
-- (only the zones where something's explored since are made again, and the counts only then: all of them made
-- again each time, a map opening after a new subzone did thousands of calls, a hitch)
function mod.RefreshExplore()
	if not On() then Off() return end
	Fresh()
	local changed = not counts or not counts.on
	for mapID, z in pairs(zones) do
		local done = Progress(mapID)
		if z.done ~= done then
			z.done = done
			changed = true
			if z.set and not z.dirty then Let(z) end
			z.dirty = true
		end
	end
	if changed then
		BuildCounts()
		S.SetPinSetOn(counts, true)
	end
	Update()
end

tinsert(S.viewHooks, function(u, v, hu, hv, zoom)
	view = view or {}
	view[1], view[2], view[3], view[4], view[5] = u, v, hu, hv, zoom
	if not (mod.db and mod.db.explore) then return end
	if not counts then mod.RefreshExplore() else Update() end      -- (on before the map was built: made now)
end)

tinsert(S.exploredHooks, function()
	if mod.db and mod.db.explore then mod.RefreshExplore() end
end)

-- the game says something was explored (or sent what you'd explored, after login): made again, at once with
-- the map open, else as it next opens; and at the first opening of a session, what it holds by then. (Into a new
-- subzone too: a place explored can come without that event, #422)
-- (the map is WorldMap.lua's, hooked from its Setup: Blizzard's map can load after this file, and a hook made
-- here, on a map not there yet, never was: explored since, a place kept its outline and pin until a /reload)
local owner, pending, theMap = {}, true, nil
local function Explored()
	if theMap and theMap:IsShown() and mod.db and mod.db.explore then mod.RefreshExplore() else pending = true end
end
ns.RegisterEvent(owner, "MAP_EXPLORATION_UPDATED", Explored)
ns.RegisterEvent(owner, "ZONE_CHANGED", Explored)
ns.RegisterEvent(owner, "ZONE_CHANGED_NEW_AREA", Explored)
function mod:SetupExplore(worldMap)
	if theMap or not worldMap then return end
	theMap = worldMap
	worldMap:HookScript("OnShow", function()
		if not pending or not (mod.db and mod.db.explore) then return end
		pending = false
		C_Timer.After(0, function() if On() then mod.RefreshExplore() end end)
	end)
end
