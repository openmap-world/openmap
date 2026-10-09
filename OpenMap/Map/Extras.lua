--------------------------------------------------------------------------------
-- World map extras:
--   coordinates   a bar along the map's foot: your position, and the zone and
--                 position under the cursor (any zone, not just the one shown)
--   zone levels   the hover label adds a zone's level range (coloured by your
--                 level; Data/Levels.lua)
--   no fade       the map stays opaque while you move (mapFade CVar)
-- And Questie: on a zone map its pins (HereBeDragons) only show that zone's own;
-- the stitched map shows the neighbours too, so their pins come along.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

local d = mod.defaults
d.coords = true
d.zoneLevels = true
d.noFade = true

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
-- Questie's pins from neighbouring zones
--------------------------------------------------------------------------------

local SHOW_PARENT = 1                   -- HBD_PINS_WORLDMAP_SHOW_PARENT: pins meant beyond their own zone
local NEAR = 1                          -- how far around the shown zone (in its own widths) neighbours' pins come

-- true when `mapID` is `ancestor` or under it
local function Within(mapID, ancestor)
	for _ = 1, 8 do
		if not mapID or mapID == 0 then return false end
		if mapID == ancestor then return true end
		local info = C_Map.GetMapInfo(mapID)
		mapID = info and info.parentMapID
	end
	return false
end

local function SetUpQuestiePins()
	local pins = LibStub and LibStub("HereBeDragonsQuestie-Pins-2.0", true)
	local provider = pins and pins.worldmapProvider
	if not provider or not provider.HandlePin or provider.openmapNeighbours then return end
	provider.openmapNeighbours = true
	local HandlePin = provider.HandlePin
	provider.HandlePin = function(self, icon, data, ...)
		HandlePin(self, icon, data, ...)
		if not mod.IsStitched() or not data.uiMapID or not data.mapX or (data.worldMapShowFlag or 0) < SHOW_PARENT then return end
		local holder = icon:GetParent()
		if holder and holder.icon == icon then return end    -- HereBeDragons placed it already
		local mapID = self:GetMap():GetMapID()
		local info = C_Map.GetMapInfo(mapID)
		if not info or info.mapType ~= Enum.UIMapType.Zone or Within(data.uiMapID, mapID) then return end
		local l, r, t, b = S.Rect(data.uiMapID)
		if not l then return end
		local x, y = mod.FromWorld(mapID, l + data.mapX * (r - l), t + data.mapY * (b - t))
		if x < -NEAR or x > 1 + NEAR or y < -NEAR or y > 1 + NEAR then return end
		self:GetMap():AcquirePin("HereBeDragonsPinsTemplateQuestie", icon, x, y, data.frameLevelType)
	end
end

local function ApplyExtras()
	if not map then return end
	SetUpCoords()
	SetUpZoneLevels()
	if mod.db.noFade then
		if mod.char.mapFade == nil then mod.char.mapFade = GetCVar and GetCVar("mapFade") or "1" end
		SetCVarSafe("mapFade", "0")
	elseif mod.char.mapFade ~= nil then
		SetCVarSafe("mapFade", mod.char.mapFade)          -- the player's own setting, as it was
		mod.char.mapFade = nil
	end
end

function mod:SetupExtras(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
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
	opts.noFade = { type = "toggle", name = "Don't fade while moving", order = 44, get = get, set = setApply, disabled = off }
end
