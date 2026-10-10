--------------------------------------------------------------------------------
-- World map extras:
--   coordinates   a bar along the map's foot: your position, and the zone and
--                 position under the cursor (any zone, not just the one shown)
--   zone levels   the hover label adds a zone's level range (coloured by your
--                 level; Data/Levels.lua)
--   moving fade   how far the map fades while you move (0: not at all); ours, not the
--                 game's (its mapFade CVar is held off): smooth, never under the mouse
-- And Questie: on a zone map its pins (HereBeDragons) only show that zone's own;
-- the stitched map shows the neighbours too, so their pins come along.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

local d = mod.defaults
d.coords = true
d.zoneLevels = true
d.moveFade = 0                  -- how much the map fades while you move (0 to 0.9)

local map, sc, bar
local labelProvider, labelOnUpdate      -- Blizzard's area label, and its own OnUpdate

local function SetCVarSafe(name, value)
	if C_CVar and C_CVar.SetCVar then pcall(C_CVar.SetCVar, name, value) elseif SetCVar then pcall(SetCVar, name, value) end
end

-- the zone (or continent) under the cursor, the cursor's point in it, and its
-- point in the map shown. Stitched, from the cursor itself: Blizzard's cursor
-- position is clamped to the shown map's rectangle.
local lastU, lastV, lastId
local function PlaceAt()
	local mapID = map:GetMapID()
	if mod.IsStitched() then
		local u, v, pu = mod.CursorWorld()
		local id = lastId
		if not lastU or math.abs(u - lastU) > (pu or 0) * 2 or math.abs(v - lastV) > (pu or 0) * 2 then
			local chain = S.ChainAt(u, v)
			id, lastU, lastV, lastId = chain[#chain], u, v, chain[#chain]
		end
		local l, r, t, b = S.Rect(id)
		local hx, hy = mod.FromWorld(mapID, u, v)
		return id, (u - l) / (r - l), (v - t) / (b - t), hx, hy
	end
	local x, y = map:GetNormalizedCursorPosition()
	local info = C_Map.GetMapInfoAtPosition(mapID, x, y)
	if info and info.mapID ~= mapID then
		local l, r, t, b = C_Map.GetMapRectOnMap(info.mapID, mapID)
		if l and r > l and b > t then return info.mapID, (x - l) / (r - l), (y - t) / (b - t), x, y end
	end
	return mapID, x, y, x, y
end

local function MapName(mapID)
	local info = mapID and C_Map.GetMapInfo(mapID)
	return info and info.name
end

--------------------------------------------------------------------------------
-- Coordinates
--------------------------------------------------------------------------------

local function Coord(x, y)
	if not x or x < 0 or x > 1 or y < 0 or y > 1 then return "|cff808080--|r" end
	return ("%.1f, %.1f"):format(x * 100, y * 100)
end

local throttle = 0
local function UpdateCoords(_, elapsed)
	throttle = throttle + elapsed
	if throttle < 0.05 then return end
	throttle = 0

	local best = C_Map.GetBestMapForUnit("player")
	local pos = best and C_Map.GetPlayerMapPosition(best, "player")
	local px, py
	if pos then px, py = ns.Safe.XY(pos) end
	if ns.Safe.IsSecret(px) or ns.Safe.IsSecret(py) then px, py = nil, nil end
	bar.player:SetText("|cffffd100" .. PLAYER .. "|r  " .. Coord(px, py))

	if sc:IsMouseOver() then
		local id, zx, zy = PlaceAt()
		local name = MapName(id)
		bar.cursor:SetText((name and ("|cffffd100" .. name .. "|r  ") or "") .. Coord(zx, zy))
	else
		bar.cursor:SetText("")
	end
end

local function SetUpCoords()
	if not bar then
		bar = CreateFrame("Frame", nil, sc)
		bar:SetPoint("BOTTOMLEFT")
		bar:SetPoint("BOTTOMRIGHT")
		bar:SetHeight(18)
		bar:SetFrameLevel(math.min(sc:GetFrameLevel() + 9000, 9900))   -- above every map pin
		local bg = bar:CreateTexture(nil, "BACKGROUND")
		bg:SetAllPoints()
		bg:SetColorTexture(0, 0, 0, 0.5)
		bar.player = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		bar.player:SetPoint("LEFT", 8, 0)
		bar.cursor = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		bar.cursor:SetPoint("RIGHT", -8, 0)
		ns.Look:Font(bar.player, 12, "OUTLINE")
		ns.Look:Font(bar.cursor, 12, "OUTLINE")
		bar:SetScript("OnUpdate", UpdateCoords)
	end
	bar:SetShown(mod.db.coords)
	if mod.db.coords then
		-- Blizzard's own coordinates (another addon may have turned them on) would double ours
		SetCVarSafe("worldMapShowPlayerCoords", "0")
		SetCVarSafe("worldMapShowCursorCoords", "0")
	end
end

--------------------------------------------------------------------------------
-- Zone levels on the hover label
--------------------------------------------------------------------------------

local function LevelText(mapID)
	local lv = ns.MapLevels and ns.MapLevels[mapID]
	if not lv or not lv[1] or not lv[2] then return "" end
	local lo, hi = lv[1], lv[2]
	local level = UnitLevel("player")
	local color
	if level < lo then
		color = GetQuestDifficultyColor(lo)
	elseif level > hi then
		color = GetQuestDifficultyColor(hi - 2)   -- zones wholly below you go grey/green, not yellow
	else
		color = QuestDifficultyColors and QuestDifficultyColors.difficult or { r = 1, g = 0.5, b = 0.25 }
	end
	local range = lo == hi and tostring(hi) or (lo .. "-" .. hi)
	return (" |cff%02x%02x%02x(%s)|r"):format(color.r * 255, color.g * 255, color.b * 255, range)
end

-- replaces AreaLabelFrameMixin's OnUpdate: the place under the cursor, with its levels
local function AreaLabelOnUpdate(self)
	self:ClearLabel(MAP_AREA_LABEL_TYPE.AREA_NAME)
	local m = self.dataProvider:GetMap()
	if m:IsCanvasMouseFocus() then
		local mapID = m:GetMapID()
		local id, _, _, x, y = PlaceAt()
		local name
		if id ~= mapID and id ~= S.WORLD then
			name = MapName(id)
			if name then name = name .. LevelText(id) end
		elseif x >= 0 and x <= 1 and y >= 0 and y <= 1 then
			name = MapUtil.FindBestAreaNameAtMouse(mapID, x, y)
		end
		if name then self:SetLabel(MAP_AREA_LABEL_TYPE.AREA_NAME, name) end
	end
	self:EvaluateLabels()
end

local function SetUpZoneLevels()
	if not labelProvider then
		for provider in pairs(map.dataProviders or {}) do
			if provider.Label and provider.Label.SetLabel then labelProvider = provider break end
		end
		if not labelProvider then return end
		labelOnUpdate = labelProvider.Label:GetScript("OnUpdate")
	end
	labelProvider.Label:SetScript("OnUpdate", mod.db.zoneLevels and AreaLabelOnUpdate or labelOnUpdate)
end

--------------------------------------------------------------------------------
-- Fading
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
-- Questie's pins on the stitched map. HereBeDragons (Questie's copy) places a pin from
-- its world coordinates; on Forever that only works on the world map, where Questie
-- converts it through the client's own map rectangles. On a zone or continent map (the
-- stitched map switches to the one you're looking at) it can't, and the pin is dropped;
-- and it never shows a neighbouring zone's pins on a zone. So any pin HereBeDragons left
-- unplaced is placed here, from the map it belongs to (`uiMapID`, `mapX`, `mapY`) through
-- the same rectangles, following Questie's own rules for where a pin may show.
--------------------------------------------------------------------------------

local SHOW_CURRENT = 0                  -- HBD_PINS_WORLDMAP_SHOW_CURRENT: only on its own map
local NEAR = 1                          -- how far round the map underneath (its widths) pins are placed

local questie = { placed = 0, ours = 0 }   -- for /openmap status: pins placed since the map last changed

local function SetUpQuestiePins()
	local pins = LibStub and LibStub("HereBeDragonsQuestie-Pins-2.0", true)
	local provider = pins and pins.worldmapProvider
	if not provider or not provider.HandlePin or provider.openmapPins then return end
	provider.openmapPins = true
	questie.pins = pins
	local HandlePin = provider.HandlePin
	provider.HandlePin = function(self, icon, data, ...)
		HandlePin(self, icon, data, ...)
		local holder = icon:GetParent()
		if holder and holder.icon == icon then questie.placed = questie.placed + 1 return end   -- placed already
		if not mod.IsStitched() or not data.uiMapID or not data.mapX or not data.mapY then return end
		local mapID = self:GetMap():GetMapID()
		if (data.worldMapShowFlag or SHOW_CURRENT) == SHOW_CURRENT and data.uiMapID ~= mapID then return end
		local info = C_Map.GetMapInfo(mapID)
		if not info then return end
		local profile = _G.Questie and Questie.db and Questie.db.profile
		if profile and profile.hideIconsOnContinents and (info.mapType == Enum.UIMapType.Continent or mapID == S.WORLD) then return end
		local l, r, t, b = S.Rect(data.uiMapID)
		if not l then return end
		local x, y = mod.FromWorld(mapID, l + data.mapX * (r - l), t + data.mapY * (b - t))
		if x < -NEAR or x > 1 + NEAR or y < -NEAR or y > 1 + NEAR then return end
		self:GetMap():AcquirePin("HereBeDragonsPinsTemplateQuestie", icon, x, y, data.frameLevelType)
		questie.ours = questie.ours + 1
	end
	-- (counted afresh each time the map changes: HereBeDragons rebuilds its pins then)
	local Refresh = provider.RefreshAllData
	provider.RefreshAllData = function(self, ...)
		local before = self:GetMap() and self:GetMap():GetMapID()
		if before ~= questie.mapID then questie.placed, questie.ours, questie.mapID = 0, 0, before end
		return Refresh(self, ...)
	end
end

-- for /openmap status: Questie's pins, and how many are on the map now
function mod.QuestieStatus()
	if not questie.pins then return nil end
	local registered, shown = 0, 0
	for _ in pairs(questie.pins.worldmapPins or {}) do registered = registered + 1 end
	for _ in map:EnumeratePinsByTemplate("HereBeDragonsPinsTemplateQuestie") do shown = shown + 1 end
	return registered, shown, questie.placed, questie.ours
end

--------------------------------------------------------------------------------
-- Fading while you move
--------------------------------------------------------------------------------

local FADE_RATE = 6             -- the fade's approach, per second
local fader = CreateFrame("Frame")
fader:Hide()
local faded = 1
fader:SetScript("OnUpdate", function(_, elapsed)
	local moving = false
	if GetUnitSpeed then
		local speed = GetUnitSpeed("player")
		moving = not ns.Safe.IsSecret(speed) and (speed or 0) > 0
	end
	local want = (moving and not map:IsMouseOver()) and 1 - (mod.db.moveFade or 0) or 1
	if math.abs(faded - want) < 0.005 then
		if faded ~= want then faded = want map:SetAlpha(want) end
		return
	end
	faded = faded + (want - faded) * math.min(1, elapsed * FADE_RATE)
	map:SetAlpha(faded)
end)

local function ApplyExtras()
	if not map then return end
	SetUpCoords()
	SetUpZoneLevels()
	-- (from the old on / off setting: fading back on was the game's half-fade)
	if mod.db.noFade ~= nil then
		if mod.db.noFade == false and (mod.db.moveFade or 0) == 0 then mod.db.moveFade = 0.5 end
		mod.db.noFade = nil
	end
	-- the game's own fade off while ours runs (the player's setting kept, put back if ours is gone)
	if mod.char.mapFade == nil then mod.char.mapFade = GetCVar and GetCVar("mapFade") or "1" end
	SetCVarSafe("mapFade", "0")
	fader:SetShown(map:IsShown() and (mod.db.moveFade or 0) > 0)
	if (mod.db.moveFade or 0) == 0 then map:SetAlpha(1) end
end

function mod:SetupExtras(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	map:HookScript("OnShow", function() fader:SetShown((mod.db.moveFade or 0) > 0) end)
	map:HookScript("OnHide", function() fader:Hide() faded = 1 map:SetAlpha(1) end)
	SetUpQuestiePins()
	ApplyExtras()
end

mod.RefreshExtras = ApplyExtras

function mod:ExtraOptions(opts, get, set, off)
	local function setApply(info, v) set(info, v) ApplyExtras() end
	opts.extrasHeader = ns.Header("On the map", 40)
	opts.coords = { type = "toggle", name = "Coordinates", order = 41, get = get, set = setApply, disabled = off,
		desc = "A bar along the map's foot: your position, and the zone and position under the cursor." }
	opts.zoneLevels = { type = "toggle", name = "Zone levels", order = 42, get = get, set = setApply, disabled = off,
		desc = "Hovering a zone shows its level range, coloured for your level." }
	opts.moveFade = { type = "range", name = "Fade while moving", order = 44, min = 0, max = 0.9, step = 0.05, isPercent = true,
		get = get, set = setApply, disabled = off,
		desc = "How much the map fades while you walk or ride, so you can see where you're going. 0% keeps it solid. It never fades while the mouse is over it." }
end
