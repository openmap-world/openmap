--------------------------------------------------------------------------------
-- Battlegrounds: Blizzard's map of each (Warsong Gulch, Arathi Basin, Alterac Valley ...), kept as the
-- game shows it, with its player arrow, group dots, flags and bases, made to zoom in as the world map
-- does, and the battleground's own minimap tiles (Data/Battlegrounds.lua) mixed in for detail as it
-- does: the painted map leads, the minimap's trees, rocks and buildings come in closer, toward the
-- world's Minimap detail setting at the deepest zoom. Only the canvas's zoom steps are OpenMap's;
-- Blizzard's map does the rest. Off (Battleground maps), or with the Gamepad UI: the game's map as it was.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local L = ns.L

mod.defaults.bgMaps = true      -- battlegrounds' maps zoom, with the minimap's detail up close

local TILE = 1600 / 3           -- yards per minimap tile
local FEATHER = ns.Media.tex .. "MapFeather"   -- (the focus box's soft edge: Stitch.lua's edge mask)
local ZOOM_STEP = 1.25          -- each wheel notch (WorldMap.lua's)
local DEEP_YARDS = 360          -- the deepest zoom shows this many yards across the map's long side ...
local LEAST_DEEP = 4            -- ... and goes at least this far in
local MINI_FADE = { 1.3, 2.5 }  -- zoom (times the whole map) where the minimap's detail mixes in to Minimap strength
local DEEP_FADE = { 0.5, 1 }    -- ... and takes over toward its most opacity (share of the deepest zoom)

local map, sc, layer, mask
local shownID                   -- the battleground whose tiles are up
local tiles = {}                -- textures of shownID's tiles
local deepest = {}              -- uiMapID -> the deepest zoom (times its fit)

-- (not with the game's Gamepad UI on: it reads the canvas's zoom steps as the map changes, and the
-- controller's bindings it makes would carry OpenMap's writing them, PadView.lua; the game's map then)
local function PadUI()
	return (mod.PadViewOn and mod.PadViewOn()) or (InputUtil and InputUtil.IsGamepadUIEnabled and InputUtil.IsGamepadUIEnabled()) or false
end
local function Data(mapID) return ns.MapBattlegrounds and mapID and ns.MapBattlegrounds[mapID] end
-- (the battleground you're in: WorldMap.lua and Window.lua leave its map's layout and clicks to Blizzard, and here
-- its zoom steps are Blizzard's (Report AFK reads them, #472); only the minimap's detail is put over it)
local function Inside(mapID)
	local bg = Data(mapID)
	if not bg or not IsInInstance then return false end
	local _, kind = IsInInstance()
	if kind ~= "pvp" then return false end
	local instanceID = GetInstanceInfo and select(8, GetInstanceInfo())
	return instanceID == nil or instanceID == bg[1]
end
mod.InsideBattleground = Inside
local function On() return mod.db.bgMaps ~= false and not PadUI() end
function mod.IsBattlegroundMap(mapID) return Data(mapID) ~= nil end

local function Smooth(x, r)
	local t = math.max(0, math.min(1, (x - r[1]) / (r[2] - r[1])))
	return t * t * (3 - 2 * t)
end

-- the deepest zoom of a battleground's map: DEEP_YARDS across its long side
local function Deepest(mapID)
	if deepest[mapID] then return deepest[mapID] end
	local box = Data(mapID)[3]
	local across = math.max(box[3] - box[1], box[4] - box[2])
	deepest[mapID] = math.max(LEAST_DEEP, across / DEEP_YARDS)
	return deepest[mapID]
end
mod.BattlegroundDeepest = Deepest

-- where a world spot (yards) is on its map (0..1), and a minimap tile's part of the map, cut to it:
-- u0, v0, u1, v1 on the map and the texcoords of that part of the tile (nil: off the map)
local function OnMap(bg, x, y)
	local box, part = bg[3], bg[4]
	return part[1] + (part[3] - part[1]) * (box[4] - y) / (box[4] - box[2]),
		part[2] + (part[4] - part[2]) * (box[3] - x) / (box[3] - box[1])
end
local function TilePart(bg, key)
	local tx, ty = math.floor(key / 64), key % 64
	local ua, va = OnMap(bg, (32 - ty) * TILE, (32 - tx) * TILE)     -- (its north-west corner)
	local ub, vb = OnMap(bg, (31 - ty) * TILE, (31 - tx) * TILE)     -- (south-east)
	local part = bg[4]
	local u0, v0 = math.max(ua, part[1]), math.max(va, part[2])
	local u1, v1 = math.min(ub, part[3]), math.min(vb, part[4])
	if u1 <= u0 or v1 <= v0 then return end
	return u0, v0, u1, v1, (u0 - ua) / (ub - ua), (u1 - ua) / (ub - ua), (v0 - va) / (vb - va), (v1 - va) / (vb - va)
end
mod.BattlegroundTilePart = TilePart

-- how strong the minimap's detail is at a zoom (times the map's fit): the world's Minimap detail
-- settings (Close.lua), none with them off
local function Mix(mapID, zoom)
	local base = mod.db.minimap ~= false and (mod.db.minimapMix or 0) or 0
	if base <= 0 then return 0 end
	local most = mod.db.minimapDeep or 1
	-- (the battleground you're in: its map doesn't zoom there, so the detail shows only with Minimap detail set to show
	-- at every zoom, "Always" (minimapFrom at its least, Close.lua), at Minimap strength; otherwise none)
	if Inside(mapID) then return (mod.db.minimapFrom or 20) <= 1 and math.min(base, most) or 0 end
	local mix = math.min(base, most) * Smooth(zoom, MINI_FADE)
	local deep = Deepest(mapID)
	return mix + (most - mix) * Smooth(zoom, { deep * DEEP_FADE[1], deep * DEEP_FADE[2] })
end
mod.BattlegroundMix = Mix

local function Layer()
	if layer then return layer end
	local canvas = map:GetCanvas()
	layer = CreateFrame("Frame", nil, canvas)
	layer:SetAllPoints(canvas)
	local fl = map:GetPinFrameLevelsManager()
	-- (over Blizzard's art, under every icon: where the stitched art goes, WorldMap.lua)
	local level = fl and fl:GetValidFrameLevel("PIN_FRAME_LEVEL_OPENMAP_STITCH")
	if level then layer:SetFrameLevel(level) end
	-- (only inside the battleground on Blizzard's map: not over its frame and portraits, nor the land
	-- round it nobody reaches; Data/Battlegrounds.lua's focus box)
	mask = layer:CreateMaskTexture()
	mask:SetTexture(FEATHER, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
	return layer
end

local function Hide()
	for _, t in ipairs(tiles) do t:Hide() end
	if layer then layer:Hide() end
	shownID = nil
end

-- the zoom now, times the map's fit (Blizzard's least zoom)
local function Zoom()
	local zl = sc.zoomLevels
	local base = zl and zl[1] and zl[1].scale
	local scale = sc.GetCanvasScale and sc:GetCanvasScale()
	if not base or not scale or base <= 0 then return 1 end
	return scale / base
end

local function Fade()
	if not shownID then return end
	local a = Mix(shownID, Zoom())
	layer:SetShown(a > 0.004)
	for _, t in ipairs(tiles) do t:SetAlpha(a) end
end

-- the battleground's tiles on its map, laid out on the canvas (its size is the map art's), through
-- the feathered focus box
local function Show(mapID)
	local bg = Data(mapID)
	local f = Layer()
	local w, h = f:GetParent():GetWidth(), f:GetParent():GetHeight()
	if not w or w <= 0 or not h or h <= 0 then return end
	local focus = bg[6] or { 0, 0, 1, 1 }
	mask:ClearAllPoints()
	mask:SetPoint("TOPLEFT", f, "TOPLEFT", focus[1] * w, -focus[2] * h)
	mask:SetSize((focus[3] - focus[1]) * w, (focus[4] - focus[2]) * h)
	local n = 0
	local keys = {}
	for key in pairs(bg[5]) do keys[#keys + 1] = key end
	table.sort(keys)
	for _, key in ipairs(keys) do
		local u0, v0, u1, v1, l, r, t, b = TilePart(bg, key)
		if u0 then
			n = n + 1
			local tex = tiles[n]
			if not tex then
				tex = f:CreateTexture(nil, "ARTWORK")
				if S.MiniTileLook then S.MiniTileLook(tex) end   -- (the world's minimap tiles' look: Close.lua)
				tex:AddMaskTexture(mask)
				tiles[n] = tex
			end
			tex:SetTexture(bg[5][key], nil, nil, "LINEAR")
			tex:SetTexCoord(l, r, t, b)
			tex:ClearAllPoints()
			tex:SetPoint("TOPLEFT", f, "TOPLEFT", u0 * w, -v0 * h)
			tex:SetSize((u1 - u0) * w, (v1 - v0) * h)
			tex:Show()
		end
	end
	for i = n + 1, #tiles do tiles[i]:Hide() end
	shownID = mapID
	Fade()
end

local function Refresh()
	local mapID = map:GetMapID()
	-- (the battleground you're in too: only the tiles' layer, OpenMap's own frame among the canvas's, as the stitched
	-- map's art is; nothing written on Blizzard's frames or its zoom steps, which Report AFK reads, #472)
	if map:IsShown() and On() and Data(mapID) and not mod.IsStitched() then
		Show(mapID)
	else
		Hide()
	end
end

-- Blizzard's zoom steps for its map (one: it doesn't zoom), OpenMap's in their place: from its fit
-- to the deepest, a wheel notch apart, as the world map's. After WorldMap.lua's own hook, which leaves
-- a map that isn't stitched to Blizzard
local function ZoomLevels(self)
	if not On() or not Data(self.mapID) or mod.IsStitched() then return end
	-- (not on the map of the battleground you're in, whatever the switch: Blizzard works its canvas's scale out from
	-- these steps as it resets the map, a right-click on a group dot reads that scale before its handlers, and with
	-- OpenMap's steps written there Report AFK was blocked, #472. Its map opened from outside still zooms)
	if Inside(self.mapID) then return end
	local zl = self.zoomLevels
	local base = zl and zl[1] and zl[1].scale
	if not base then return end
	local levels, zoom, deep = {}, 1, Deepest(self.mapID)
	while zoom < deep * ZOOM_STEP do
		levels[#levels + 1] = { scale = base * math.min(zoom, deep), layerIndex = zl[1].layerIndex or 1 }
		zoom = zoom * ZOOM_STEP
	end
	self.zoomLevels = levels
end

function mod.SetBattlegroundMaps(on)
	mod.db.bgMaps = on and true or false
	-- (not from here on the map of the battleground you're in: Blizzard makes its zoom steps again as the map next opens,
	-- and the switch off leaves nothing of OpenMap's on it from then: no zoom steps written, no tiles, #472)
	if map and map:IsShown() and Data(map:GetMapID()) and not Inside(map:GetMapID()) and not InCombatLockdown() then
		sc:CreateZoomLevels()
		sc:ResetZoom()
	end
	if map then Refresh() end
end

-- the map's search (Nav.lua): every battleground, by the game's name for it, opening its map
function mod.BattlegroundPlaces()
	local out = {}
	for mapID in pairs(ns.MapBattlegrounds or {}) do
		local info = C_Map.GetMapInfo(mapID)
		if info and info.name and info.name ~= "" then out[#out + 1] = { name = info.name, mapID = mapID } end
	end
	table.sort(out, function(a, b) return a.name < b.name end)
	return out
end

function mod:BattlegroundOptions(opts, get, set, off)
	opts.bgMaps = { type = "toggle", name = L["Battleground maps"], order = 31.027, width = "full", get = get, disabled = off,
		set = function(_, v) mod.SetBattlegroundMaps(v) end,
		desc = L["A battleground's map zooms in like the world map, and the game's minimap of it shows its detail up close (as Minimap detail is set). Off: the game's own map, as it was."] }
end

-- /openmap bg: what the map of a battleground has of OpenMap's, to tell why its minimap's detail doesn't show
function mod:BattlegroundDiag()
	if not map then ns:Print("Battleground maps: not set up.") return end
	local mapID = map:GetMapID()
	local bg = Data(mapID)
	local zl = sc.zoomLevels
	local scale = sc.GetCanvasScale and sc:GetCanvasScale()
	local f = layer and layer:GetParent()
	local shownTiles = 0
	for _, t in ipairs(tiles) do if t:IsShown() then shownTiles = shownTiles + 1 end end
	local inside, kind = IsInInstance()
	ns:Print(("Battleground map: map %s (%s), inside it %s, instance %s/%s; setting %s, gamepad %s, stitched %s"):format(
		tostring(mapID), bg and bg[2] or "not a battleground's", tostring(Inside(mapID)), tostring(inside), tostring(kind),
		tostring(mod.db.bgMaps ~= false), tostring(PadUI()), tostring(mod.IsStitched())))
	ns:Print(("  zoom steps %d (%s to %s), scale %s, zoom %.2f of %.1f; wheel %s, in a fight %s"):format(zl and #zl or 0,
		tostring(zl and zl[1] and zl[1].scale), tostring(zl and zl[#zl] and zl[#zl].scale), tostring(scale), Zoom(),
		bg and Deepest(mapID) or 0, tostring(sc.mouseWheelZoomMode), tostring(InCombatLockdown())))
	ns:Print(("  detail: Minimap %s, strength %s, deepest %s; now %.2f; tiles %d of %d shown, layer %s, canvas %sx%s, up for %s"):format(
		tostring(mod.db.minimap), tostring(mod.db.minimapMix), tostring(mod.db.minimapDeep), bg and Mix(mapID, Zoom()) or 0,
		shownTiles, #tiles, tostring(layer and layer:IsShown()), tostring(f and f:GetWidth()), tostring(f and f:GetHeight()),
		tostring(shownID)))
end

function mod:SetupBattlegrounds(worldMap)
	if not ns.MapBattlegrounds then return end
	map, sc = worldMap, worldMap.ScrollContainer
	if not (sc and sc.CreateZoomLevels and map.GetCanvas) then return end
	hooksecurefunc(sc, "CreateZoomLevels", ZoomLevels)
	hooksecurefunc(map, "OnMapChanged", Refresh)
	if map.OnCanvasScaleChanged then hooksecurefunc(map, "OnCanvasScaleChanged", Fade) end
	map:HookScript("OnShow", Refresh)
	map:HookScript("OnHide", Hide)
	if map:IsShown() then
		if Data(map:GetMapID()) and not Inside(map:GetMapID()) then sc:CreateZoomLevels() end
		Refresh()
	end
end
