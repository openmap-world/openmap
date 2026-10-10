--------------------------------------------------------------------------------
-- OpenMap: Blizzard's world map (quest log, controls, Questie) with every
-- zone stitched into one canvas (ns.MapStitch). More map helpers are in
-- Extras.lua, Flights.lua, Townsfolk.lua, Panel.lua and Paint.lua.
--
-- On the world, continent and zone maps:
--   * the stitched art is a layer just above Blizzard's map art, under its pins
--   * zoom runs from the whole world down to street level, anchored at the cursor
--   * panning runs past the map's edge into its neighbours
--   * once the view settles, the map underneath quietly becomes the zone (or
--     continent) you're looking at, so quest areas, coordinates and the zone
--     name always match what's on screen
--   * left-click zooms into the place under the cursor, right-click out a level
-- Other maps (dungeons, battlegrounds) behave as Blizzard made them.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local WORLD = S.WORLD

local mod = ns:NewModule("worldmap", {
	defaults = {
		enabled = true,
		autoSwitch = true,      -- the map underneath follows what you're looking at
		icons = true,
		flight = true,
		routes = false,         -- boat and zeppelin routes
		colorMatch = 1,         -- how far zone borders move to the shared palette
		desaturate = 0.1,
		unexplored = "show",    -- areas not explored yet: "show", "dim" or "hide"
		maxZoom = 48,           -- x the whole-world view
	},
})

local ZOOM_STEP = 1.25          -- each wheel notch
local ENTER, LEAVE = 0.9, 0.7   -- switch into a map at this share of its fit zoom; leave it below that
local ART_RANGE = 80            -- frame levels the stitched art needs

local map, sc
local active = false            -- the current map is stitched
local switching = false         -- we're changing the map ourselves
local userMoved = false         -- the view moved since Blizzard last showed a map (only then do we follow it)
local wheelMode, scalingMode    -- Blizzard's, to put back on other maps

--------------------------------------------------------------------------------
-- Geometry: "zoom" 1 = the whole world fits the view
--------------------------------------------------------------------------------

local function Stitchable(mapID)
	if not mapID then return false end
	if mapID == WORLD then return true end
	local info = C_Map.GetMapInfo(mapID)
	if not info then return false end
	if info.mapType ~= Enum.UIMapType.Continent and info.mapType ~= Enum.UIMapType.Zone then return false end
	return S.Rect(mapID) ~= nil and S.ArtSize(mapID) ~= nil
end

-- view px per world unit when the whole world fits
local function FitPx()
	local W, H = S.Size()
	return math.min(sc:GetWidth() / W, sc:GetHeight() / H)
end

-- host canvas units per world unit
local function K(mapID)
	local W = S.Size()
	local l, r = S.Rect(mapID)
	return S.ArtSize(mapID) / ((r - l) * W)
end

local function ZoomFor(mapID, scale) return scale * K(mapID) / FitPx() end
local function ScaleFor(mapID, zoom) return zoom * FitPx() / K(mapID) end

-- the zoom at which `mapID` just fits the view
local function FitZoom(mapID)
	local W, H = S.Size()
	local l, r, t, b = S.Rect(mapID)
	return math.min(sc:GetWidth() / ((r - l) * W), sc:GetHeight() / ((b - t) * H)) / FitPx()
end

-- world point (normalized) <-> the current map's normalized point
local function ToWorld(mapID, x, y)
	local l, r, t, b = S.Rect(mapID)
	return l + x * (r - l), t + y * (b - t)
end
local function FromWorld(mapID, u, v)
	local l, r, t, b = S.Rect(mapID)
	return (u - l) / (r - l), (v - t) / (b - t)
end

-- the view: world centre (normalized) and zoom
local function View()
	local mapID = map:GetMapID()
	local u, v = ToWorld(mapID, sc:GetCurrentScrollX() or 0.5, sc:GetCurrentScrollY() or 0.5)
	return u, v, ZoomFor(mapID, sc:GetCanvasScale())
end

-- puts the view at once (Blizzard's InstantPanAndZoom drifts the pan toward the old one)
local openStart, Part             -- (timing an opening: below)

local function SetView(scale, x, y)
	sc.currentScale, sc.targetScale, sc.zoomTarget = scale, scale, scale
	sc.Child:SetScale(scale)
	sc:CalculateScrollExtents()
	x = Clamp(x, sc.scrollXExtentsMin, sc.scrollXExtentsMax)
	y = Clamp(y, sc.scrollYExtentsMin, sc.scrollYExtentsMax)
	sc.targetScrollX, sc.targetScrollY, sc.currentScrollX, sc.currentScrollY = x, y, x, y
	sc:SetNormalizedHorizontalScroll(x)
	sc:SetNormalizedVerticalScroll(y)
	local start = openStart and debugprofilestop and debugprofilestop()
	map:OnCanvasScaleChanged()
	if start then Part("icons rescaled (all addons)", debugprofilestop() - start) end
	sc:MarkAreaTriggersDirty()
	sc:MarkViewRectDirty()
end

-- the view centred on a world point (normalized) at `zoom`, at once
local function ShowWorld(u, v, zoom)
	local mapID = map:GetMapID()
	local x, y = FromWorld(mapID, u, v)
	SetView(ScaleFor(mapID, zoom), x, y)
end

--------------------------------------------------------------------------------
-- Zoom animation. Ours, not Blizzard's: Blizzard eases zoom and pan separately
-- (the point under the cursor zigzags) and won't pan while zooming out. Each
-- frame we work out the view exactly, so the point under the cursor stays put,
-- and a drag mid-zoom just carries that point with the cursor.
--   anchor: wheel zoom about a world point held at a view offset
--   glide:  click zoom from one view to another, as one zoom about a fixed point
--------------------------------------------------------------------------------

local ZOOM_RATE = 14            -- the wheel zoom's approach, per second (in log zoom)
local GLIDE_TIME = 0.4
local anim                      -- the running animation, or nil

-- the cursor in view px from the view's centre (y down)
local function CursorOffset()
	local x, y = GetCursorPosition()
	local es = sc:GetEffectiveScale()
	return x / es - (sc:GetLeft() + sc:GetWidth() / 2), (sc:GetTop() - sc:GetHeight() / 2) - y / es
end

-- world units (normalized) per view px at `zoom`
local function PerPx(zoom)
	local W, H = S.Size()
	local px = FitPx() * zoom
	return 1 / (W * px), 1 / (H * px)
end

-- the deepest zoom at (u, v): further in a city, whose map is small (its own map, and outdoors
-- the minimap, carry the detail there)
local CITY_ZOOM = 1.5
local function MaxZoomAt(u, v)
	return mod.db.maxZoom * ((u and S.InCity and S.InCity(u, v)) and CITY_ZOOM or 1)
end

-- wheel: zoom about the point under the cursor
local function ZoomAtCursor(factor)
	local u, v, zoom = View()
	local sx, sy = CursorOffset()
	local pu, pv = PerPx(zoom)
	local target = Clamp((anim and anim.mode == "anchor" and anim.target or zoom) * factor, 1, MaxZoomAt(u + sx * pu, v + sy * pv))
	anim = { mode = "anchor", u = u + sx * pu, v = v + sy * pv, sx = sx, sy = sy, target = target }
	userMoved = true
end

-- glides the view to a world point (normalized) at `zoom`
local function GlideTo(u, v, zoom)
	local u0, v0, z0 = View()
	anim = { mode = "glide", u0 = u0, v0 = v0, z0 = z0, u1 = u, v1 = v,
		z1 = Clamp(zoom, 1, MaxZoomAt(u, v)), t = 0 }
	userMoved = true
end

-- after Blizzard's own OnUpdate, so its panning never adds to ours
local function Animate(_, elapsed)
	if not anim then return end
	if not active then anim = nil return end
	local a = anim
	if a.mode == "anchor" then
		local _, _, z = View()
		local zoom = math.exp(math.log(z) + (math.log(a.target) - math.log(z)) * (1 - math.exp(-elapsed * ZOOM_RATE)))
		local done = math.abs(math.log(a.target / zoom)) < 0.003
		if done then zoom = a.target end
		local down = sc.mouseButtonInfo.LeftButton.down
		if down and not a.down then
			-- grabbed mid-zoom: what's under the cursor now is what the cursor carries
			local u, v = View()
			local sx, sy = CursorOffset()
			local pu, pv = PerPx(z)
			a.u, a.v, a.sx, a.sy = u + sx * pu, v + sy * pv, sx, sy
		elseif down then
			a.sx, a.sy = CursorOffset()
		end
		a.down = down
		local pu, pv = PerPx(zoom)
		ShowWorld(a.u - a.sx * pu, a.v - a.sy * pv, zoom)
		if done then anim = nil end
	else
		a.t = math.min(1, a.t + elapsed / GLIDE_TIME)
		local e = a.t * a.t * (3 - 2 * a.t)
		local zoom = math.exp(math.log(a.z0) + (math.log(a.z1) - math.log(a.z0)) * e)
		-- the centre moves with 1/zoom, which is what zooming about one fixed point looks like
		local w = math.abs(a.z1 - a.z0) < 1e-6 and e or (1 / a.z0 - 1 / zoom) / (1 / a.z0 - 1 / a.z1)
		ShowWorld(a.u0 + (a.u1 - a.u0) * w, a.v0 + (a.v1 - a.v0) * w, zoom)
		if a.t >= 1 then anim = nil end
	end
end

--------------------------------------------------------------------------------
-- Following the view: which map should be underneath
--------------------------------------------------------------------------------

local function PickMap(u, v, zoom, current)
	local chain = S.ChainAt(u, v)
	local pick = WORLD
	for _, mapID in ipairs(chain) do
		local need = (mapID == current) and LEAVE or ENTER
		if mapID ~= WORLD and Stitchable(mapID) and zoom >= FitZoom(mapID) * need then pick = mapID end
	end
	return pick
end

local function Switch(target)
	local u, v, zoom = View()
	switching = true
	local ok, err = pcall(map.SetMapID, map, target)
	switching = false
	if not ok then geterrorhandler()(err) return end
	if active then
		local x, y = FromWorld(target, u, v)
		SetView(ScaleFor(target, zoom), x, y)
	end
end

local function Settled()
	return not anim and not sc.mouseButtonInfo.LeftButton.down
		and sc.currentScale == sc.targetScale
		and sc.currentScrollX == sc.targetScrollX and sc.currentScrollY == sc.targetScrollY
end

local ticker = CreateFrame("Frame")
ticker:Hide()
local elapsedSum = 0
-- a switch has Blizzard refresh every map data provider (every Questie pin with them): a
-- hitch, so it waits until the view has been still this long, not the moment it stops
local SWITCH_AFTER = 0.6
local stillFor = 0
ticker:SetScript("OnUpdate", function(_, elapsed)
	elapsedSum = elapsedSum + elapsed
	if elapsedSum < 0.1 then return end
	elapsedSum = 0
	if not active then return end
	local mapID = map:GetMapID()

	-- the player, when the map underneath can't show them
	local pos = C_Map.GetPlayerMapPosition(mapID, "player")
	if pos then
		S.SetPlayer(nil)
	else
		local best = C_Map.GetBestMapForUnit("player")
		local p = best and S.Rect(best) and C_Map.GetPlayerMapPosition(best, "player")
		local x, y
		if p then x, y = ns.Safe.XY(p) end
		if not ns.Safe.IsSecret(x) and not ns.Safe.IsSecret(y) and x and y then
			local u, v = ToWorld(best, x, y)
			S.SetPlayer(u, v, ns.Safe.Call(GetPlayerFacing))
		else
			S.SetPlayer(nil)
		end
	end

	stillFor = Settled() and stillFor + 0.1 or 0
	if mod.db.autoSwitch and userMoved and stillFor >= SWITCH_AFTER and not InCombatLockdown() then
		local u, v, zoom = View()
		local target = PickMap(u, v, zoom, mapID)
		if target ~= mapID then Switch(target) end
	end
end)

--------------------------------------------------------------------------------
-- Hooks into Blizzard's map
--------------------------------------------------------------------------------

-- how long opening the map takes, to the next frame drawn (/openmap status): the game's
-- work, Questie's and ours (the first opening also builds the map); and OpenMap's own part,
-- its handlers' time from the open until the second frame after it
local openTimes, openOurs, openFrames = {}, 0, 0
local openParts, openLast = {}, {}
local openTimer = CreateFrame("Frame")
openTimer:Hide()
openTimer:SetScript("OnUpdate", function(self)
	openFrames = openFrames + 1
	if openFrames == 1 and openStart then
		table.insert(openTimes, 1, { debugprofilestop() - openStart, 0 })
		openTimes[4] = nil
	elseif openFrames >= 2 then
		if openTimes[1] then openTimes[1][2] = openOurs end
		openLast, openParts = openParts, {}
		openStart = nil
		self:Hide()
	end
end)
-- `fn`, with its time counted as OpenMap's part of an opening (while one is being timed),
-- by part. "icons rescaled" (Blizzard telling every addon's map icons the new scale, from
-- SetView) is timed apart: it runs inside our handlers but is mostly other addons' work.
Part = function(name, ms)
	openParts[name] = (openParts[name] or 0) + ms
end
local function Ours(name, fn)
	return function(...)
		if not openStart or not debugprofilestop then return fn(...) end
		local start = debugprofilestop()
		fn(...)
		local ms = debugprofilestop() - start
		openOurs = openOurs + ms
		Part(name, ms)
	end
end

-- the view for Close.lua (minimap, grain, caves): centre, half extents (normalized), zoom
-- (Blizzard reports a pan several times a frame: the work is done once, on the next frame)
local viewFrame = CreateFrame("Frame")
viewFrame:Hide()
viewFrame:SetScript("OnUpdate", Ours("view update", function(self)
	self:Hide()
	if not active or not S.SetView then return end
	local u, v, zoom = View()
	local pu, pv = PerPx(zoom)
	S.SetView(u, v, sc:GetWidth() / 2 * pu, sc:GetHeight() / 2 * pv, zoom)
end))
local function ApplyView()
	if active then viewFrame:Show() end
end

local function ApplyZoom()
	if not active then return end
	S.SetZoom(ZoomFor(map:GetMapID(), sc:GetCanvasScale()), sc:GetCanvasScale())
	ApplyView()
end

-- a map is about to show: decide whether it's stitched, then lay the art out for it
-- Blizzard's own art for the host map (its tiles, and the explored-area pin, which also
-- runs every frame): all under ours, so off while the stitched map shows
local function BlizzardArt()
	local show = not active
	if map.detailLayerPool then
		for layer in map.detailLayerPool:EnumerateActive() do layer:SetShown(show) end
	end
	for pin in map:EnumeratePinsByTemplate("MapExplorationPinTemplate") do pin:SetShown(show) end
end

local function Attach(mapID)
	active = mod.enabled and Stitchable(mapID) and S.IsBuilt() and S.Layout(mapID) or false
	S.SetShown(active)
	BlizzardArt()
	if active then
		sc:SetMouseWheelZoomMode(MAP_CANVAS_MOUSE_WHEEL_ZOOM_BEHAVIOR_NONE)
		sc:SetScalingMode("SCALING_MODE_LINEAR")
		if map:IsShown() then ticker:Show() end
	else
		sc:SetMouseWheelZoomMode(wheelMode)
		sc:SetScalingMode(scalingMode)
		S.SetPlayer(nil)
		ticker:Hide()
		anim = nil
		if mod.IsPainting and mod:IsPainting() then mod:TogglePaint(false) end
	end
end

-- zoom levels from the whole world to street level, in this map's scale
local function OnCreateZoomLevels(self)
	if not S.IsBuilt() then
		local fl = map:GetPinFrameLevelsManager()
		S.Build(map:GetCanvas(), fl:GetValidFrameLevel("PIN_FRAME_LEVEL_OPENMAP_STITCH"), ART_RANGE,
			fl:GetValidFrameLevel("PIN_FRAME_LEVEL_OPENMAP_ICONS"))
		if mod.BuildFlights then mod:BuildFlights() end
		if mod.BuildPaint then mod:BuildPaint() end
		if mod.BuildNav then mod:BuildNav() end
		mod:Refresh()
	end
	Attach(self.mapID)
	if not active then return end
	local levels = {}
	local zoom = 1
	local deepest = mod.db.maxZoom * CITY_ZOOM               -- (the deepest anywhere: a city's)
	while zoom < deepest * ZOOM_STEP do
		levels[#levels + 1] = { scale = ScaleFor(self.mapID, math.min(zoom, deepest)), layerIndex = 1 }
		zoom = zoom * ZOOM_STEP
	end
	self.zoomLevels = levels
	self.baseScale = levels[1].scale    -- panning allowed above the whole-world view
end

-- Blizzard showed a map (opening, the quest log, the dropdown): show it as it would
-- Blizzard's zoom reset (each time the map opens, after re-adding every addon's icons), done
-- our way while the map is stitched: straight to where you left off, in one step (not the
-- whole world and then there: every addon's icons rescaled twice); and if the map is still
-- there (closed and reopened without moving), nothing at all
local function ResetView(self)
	userMoved = false
	anim = nil
	local u, v, zoom
	if mod.SavedView then u, v, zoom = mod.SavedView() end
	if u then
		zoom = Clamp(zoom, 1, MaxZoomAt(u, v))
		local nu, nv, nz = View()
		if not (nu and math.abs(nu - u) < 1e-4 and math.abs(nv - v) < 1e-4 and math.abs(nz - zoom) < 1e-3) then
			ShowWorld(u, v, zoom)
		end
		userMoved = true
		return
	end
	local aw, ah = S.ArtSize(self.mapID)
	SetView(math.min(self:GetWidth() / aw, self:GetHeight() / ah), 0.5, 0.5)
end

-- pan anywhere on the world, not just this map. Zoomed right out the world is centred;
-- zooming in, the view gains room to go past its edges (EDGE_SLACK, in by CENTRE_UNTIL), so
-- the wheel zooms about the point under the cursor from the first step
local EDGE_SLACK = 0.2          -- world widths / heights
local CENTRE_UNTIL = 1.6        -- zoom by which the view has all that room
local function Range(a0, a1, half, slack, t)
	local lo, hi = a0 + half, a1 - half
	local c = (a0 + a1) / 2
	local plainLo, plainHi = lo, hi         -- on the world, or (the view wider than it) centred
	if lo > hi then plainLo, plainHi = c, c end
	-- with room: the whole world kept in view (if wider), and EDGE_SLACK past it
	local fullLo, fullHi = math.min(lo, hi) - slack, math.max(lo, hi) + slack
	return plainLo + (fullLo - plainLo) * t, plainHi + (fullHi - plainHi) * t
end
local function Extents(origExtents)
	return function(self, scale)
		if not active then return origExtents(self, scale) end
		local mapID = map:GetMapID()
		local x0, y0 = FromWorld(mapID, 0, 0)
		local x1, y1 = FromWorld(mapID, 1, 1)
		local hw = self:NormalizeHorizontalSize(self:GetWidth() * 0.5 / scale)
		local hh = self:NormalizeVerticalSize(self:GetHeight() * 0.5 / scale)
		local t = Clamp((ZoomFor(mapID, scale) - 1) / (CENTRE_UNTIL - 1), 0, 1)
		local minX, maxX = Range(x0, x1, hw, (x1 - x0) * EDGE_SLACK, t)
		local minY, maxY = Range(y0, y1, hh, (y1 - y0) * EDGE_SLACK, t)
		return minX, maxX, minY, maxY
	end
end

-- the hover highlight. Blizzard's shows the host map's children: on the world, whole
-- continents. Once the continents' art (and its zone outlines) is in, it's the zone under
-- the cursor instead: the continent's own highlight for it, placed on the world
local ZONE_HIGHLIGHT = 1.5      -- zoom from which the world highlights zones (Stitch.lua's continents half in)
local lastHU, lastHV, lastHK      -- (the highlight's cursor: it's redone only when that moves a pixel)
local function HighlightZone(pin)
	local tex = pin.HighlightTexture
	local u, v, pu = mod.CursorWorld()
	local key = sc:GetCanvasScale()
	if u and lastHU and lastHK == key and math.abs(u - lastHU) < pu and math.abs(v - lastHV) < pu then return end
	lastHU, lastHV, lastHK = u, v, key
	local cont
	for _, id in ipairs(u and S.ChainAt(u, v) or {}) do
		local info = C_Map.GetMapInfo(id)
		if info and info.mapType == Enum.UIMapType.Continent then cont = id end
	end
	local l, r, t, b = S.Rect(cont or WORLD)
	if not cont or not l then tex:Hide() return end
	local x, y = FromWorld(cont, u, v)
	local fid, atlas, tx, ty, w, h, left, top = C_Map.GetMapHighlightInfoAtPosition(cont, x, y)
	if not ((fid and fid > 0) or atlas) or not w or w <= 0 or h <= 0 then tex:Hide() return end
	if atlas then
		tex:SetAtlas(atlas, false, "TRILINEAR")
	else
		tex:SetTexture(fid, nil, nil, "TRILINEAR")
		tex:SetTexCoord(0, tx, 0, ty)
	end
	-- from the continent's normalized space to the world's (this map's)
	local pw, ph = pin:GetWidth(), pin:GetHeight()
	tex:ClearAllPoints()
	tex:SetSize(w * (r - l) * pw, h * (b - t) * ph)
	tex:SetPoint("TOPLEFT", (l + left * (r - l)) * pw, -(t + top * (b - t)) * ph)
	tex:Show()
end
local function HookHighlight()
	for pin in map:EnumeratePinsByTemplate("MapHighlightPinTemplate") do
		if not pin.omRefresh and pin.Refresh and pin.HighlightTexture then
			pin.omRefresh = pin.Refresh
			pin.Refresh = function(self)
				if active and map:GetMapID() == WORLD and select(3, View()) >= ZONE_HIGHLIGHT then
					return HighlightZone(self)
				end
				return self:omRefresh()
			end
		end
	end
end

-- wheel: a step, about the point under the cursor
local function OnMouseWheel(_, delta)
	if not active then return end
	ZoomAtCursor(delta > 0 and ZOOM_STEP or 1 / ZOOM_STEP)
end

-- clicks: in = the next map down under the cursor, out = the map above
local function OnCanvasClick(_, button)
	if not active then return false end
	-- not the click position Blizzard passes: that's clamped to this map's rectangle
	local u, v = mod.CursorWorld()
	local _, _, zoom = View()
	if button == "LeftButton" and (IsControlKeyDown() or (mod.PinMode and mod.PinMode())) and mod.DropWaypoint then
		if mod.SetPinMode then mod.SetPinMode(false) end
		mod.DropWaypoint(u, v)
		return true
	end
	local chain = S.ChainAt(u, v)
	if button == "LeftButton" then
		for _, id in ipairs(chain) do
			if id ~= WORLD and Stitchable(id) and FitZoom(id) > zoom * 1.05 then
				local l, r, t, b = S.Rect(id)
				GlideTo((l + r) / 2, (t + b) / 2, FitZoom(id))
				break
			end
		end
	elseif button == "RightButton" then
		if mod.ClearFlightRoute then mod:ClearFlightRoute() end
		local target = WORLD
		for _, id in ipairs(chain) do
			if id ~= WORLD and Stitchable(id) and FitZoom(id) < zoom * 0.95 then target = id end
		end
		local l, r, t, b = S.Rect(target)
		GlideTo((l + r) / 2, (t + b) / 2, FitZoom(target))
	end
	return true
end

-- our icons: a press still drags the map, a click is the icon's
-- the map was grabbed (on it or on one of our icons)
local function OnGrab()
	userMoved = true
	if anim and anim.mode == "glide" then anim = nil end   -- a grab stops a glide where it is
end

local function OnPinMouseDown(_, button)
	sc:OnMouseDown(button)
	OnGrab()
end

local function OnPinMouseUp(pin, button)
	local x, y = sc:GetCursorPosition()
	if button ~= "LeftButton" or not sc:WouldCursorPositionBeClick(button, x, y) then
		sc:OnMouseUp(button)
		return
	end
	sc.mouseButtonInfo.LeftButton.down = false
	if pin.OnClick then pin:OnClick() end
end

local function Setup()
	map = _G.WorldMapFrame
	sc = map and map.ScrollContainer
	if not sc or not sc.CreateZoomLevels or not map.GetPinFrameLevelsManager or not map:GetPinFrameLevelsManager() then
		ns:Print("World map: Blizzard's map isn't the expected kind; the seamless map is off.")
		return
	end
	wheelMode = sc.mouseWheelZoomMode or MAP_CANVAS_MOUSE_WHEEL_ZOOM_BEHAVIOR_FULL
	scalingMode = sc.scalingMode or "SCALING_MODE_TRANSLATE_FASTER_THAN_SCALE"

	-- our art sits just above Blizzard's exploration overlays, our icons above the highlight
	local fl = map:GetPinFrameLevelsManager()
	if not fl:InsertFrameLevelAbove("PIN_FRAME_LEVEL_OPENMAP_STITCH", "PIN_FRAME_LEVEL_MAP_EXPLORATION", ART_RANGE)
		or not fl:InsertFrameLevelAbove("PIN_FRAME_LEVEL_OPENMAP_ICONS", "PIN_FRAME_LEVEL_MAP_HIGHLIGHT", 6) then
		ns:Print("World map: Blizzard's map layers aren't the expected ones; the stitched art may cover some map icons.")
	end

	S.OnPinMouseDown, S.OnPinMouseUp = OnPinMouseDown, OnPinMouseUp
	S.GlideToWorld = function(u, v, zoom) GlideTo(u, v, math.max(zoom or 1, select(3, View()))) end
	-- glides until a world rectangle (normalized) just fills the view
	S.GlideToRect = function(u0, v0, u1, v1, fill)
		local W, H = S.Size()
		local z = math.min(sc:GetWidth() / ((u1 - u0) * W), sc:GetHeight() / ((v1 - v0) * H)) / FitPx()
		GlideTo((u0 + u1) / 2, (v0 + v1) / 2, z * (fill or 1))
	end
	S.OpenMap = function(mapID) map:SetMapID(mapID) end
	hooksecurefunc(sc, "CreateZoomLevels", Ours("zoom levels", OnCreateZoomLevels))
	local blizzardReset, ourReset = sc.ResetZoom, Ours("reset zoom", ResetView)
	sc.ResetZoom = function(self, ...)
		if active and not switching then return ourReset(self) end
		return blizzardReset(self, ...)
	end
	if map.RefreshDetailLayers then hooksecurefunc(map, "RefreshDetailLayers", BlizzardArt) end
	sc.CalculateScrollExtentsAtScale = Extents(sc.CalculateScrollExtentsAtScale)
	sc:HookScript("OnMouseWheel", OnMouseWheel)
	sc:HookScript("OnMouseDown", OnGrab)
	sc:HookScript("OnUpdate", Animate)
	map:AddCanvasClickHandler(OnCanvasClick, 1000)
	HookHighlight()

	local dp = CreateFromMixins(MapCanvasDataProviderMixin)
	dp.OnCanvasScaleChanged = Ours("scale changed", ApplyZoom)
	dp.OnCanvasPanChanged = ApplyView
	dp.OnMapChanged = function()
		ApplyZoom()
		if mod.RefreshPortrait then pcall(mod.RefreshPortrait) end   -- (OpenMap's icon only while stitching)
		-- (inside Blizzard's map change: a failure here is reported, never left to break it)
		if mod.RefreshNav then
			local ok, err = pcall(mod.RefreshNav, mod)
			if not ok then geterrorhandler()(err) end
		end
	end
	dp.OnHide = function()
		if mod.OnMapHidden then mod:OnMapHidden() end
		ticker:Hide()
	end
	local shown = Ours("map shown", function()
		if not S.IsBuilt() and map:GetMapID() then sc:OnCanvasSizeChanged() end   -- built on first showing
		if active then ticker:Show() end
		if mod.OnMapShown then mod:OnMapShown() end
	end)
	dp.OnShow = function()
		if debugprofilestop then openStart, openOurs, openFrames, openParts = debugprofilestop(), 0, 0, {} openTimer:Show() end
		shown()
	end
	map:AddDataProvider(dp)

	if mod.SetupExtras then mod:SetupExtras(map) end
	if mod.SetupFlights then mod:SetupFlights() end
	ns.RegisterEvent(mod, "MAP_EXPLORATION_UPDATED", function() if S.IsBuilt() then S.RefreshExplored() end end)
	if mod.SetupNav then mod:SetupNav(map) end          -- (before the menu: it holds Nav's search box)
	if mod.SetupPanel then mod:SetupPanel(map) end
	if mod.SetupPaint then mod:SetupPaint(map) end
	if mod.SetupReport then mod:SetupReport(map) end
	if mod.SetupWindow then mod:SetupWindow(map) end

	-- the map may already be showing something
	if map:IsShown() and map:GetMapID() then sc:OnCanvasSizeChanged() end
end

-- for Extras / Flights / Townsfolk / Panel / Paint
function mod.IsStitched() return active end
function mod.WheelZoom(delta) if active then ZoomAtCursor(delta > 0 and ZOOM_STEP or 1 / ZOOM_STEP) end end
-- the world point (normalized) under the cursor, and world units per view px
function mod.CursorWorld()
	if not active then return end
	local u, v, zoom = View()
	local sx, sy = CursorOffset()
	local pu, pv = PerPx(zoom)
	return u + sx * pu, v + sy * pv, pu, pv
end
mod.ToWorld = function(mapID, x, y) return ToWorld(mapID, x, y) end
-- for Nav.lua: glide / jump to a world point (normalized) at a zoom; the zoom where a map fits
function mod.Glide(u, v, zoom) if active then GlideTo(u, v, zoom) end end
function mod.ShowNow(u, v, zoom) if active then anim = nil ShowWorld(u, v, Clamp(zoom, 1, MaxZoomAt(u, v))) userMoved = true end end
function mod.FitZoom(mapID) return FitZoom(mapID) end
function mod.HostMap() return active and map:GetMapID() or nil end
mod.FromWorld = function(mapID, u, v) return FromWorld(mapID, u, v) end
-- the view now: centre (normalized), zoom; nil when the map isn't stitched
function mod.ViewNow() if active then return View() end end

-- other world map addons that change the same map: say so once, at login
local CLASHES = { Leatrix_Maps = "Leatrix Maps", Mapster = "Mapster", Magnify = "Magnify" }
local function WarnClashes()
	local loaded = C_AddOns and C_AddOns.IsAddOnLoaded or IsAddOnLoaded
	if not loaded then return end
	for addon, title in pairs(CLASHES) do
		if loaded(addon) then
			ns:Print(ns.L["%s is also changing the world map. Turn off its world map options (or the addon) so the two don't fight."]:format(title))
		end
	end
end

function mod:OnEnable()
	C_Timer.After(3, WarnClashes)
	if _G.WorldMapFrame then
		Setup()
	elseif EventUtil and EventUtil.ContinueOnAddOnLoaded then
		EventUtil.ContinueOnAddOnLoaded("Blizzard_WorldMap", Setup)
	end
end

-- which pin sets each option shows
local SET_OPTION = { dungeons = "icons", travel = "icons", flight = "flight", routes = "routes" }

function mod:Refresh()
	for key, opt in pairs(SET_OPTION) do
		local set = S.GetPinSet(key)
		if set then S.SetPinSetOn(set, self.db[opt]) end
	end
	S.ApplyGrade(self.db.colorMatch, self.db.desaturate, self.db.unexplored)
	ApplyZoom()
	if self.RefreshExtras then self.RefreshExtras() end
	if self.RefreshTownsfolk then self:RefreshTownsfolk() end
	if self.RefreshPanel then self:RefreshPanel() end
end

-- /openmap status: what the map is doing
function mod:Diag()
	if not map or not sc or not S.IsBuilt() then
		ns:Print("World map: not built yet (it's built the first time the map opens).")
		return
	end
	local mapID = map:GetMapID()
	local info = C_Map.GetMapInfo(mapID)
	ns:Print("World map: %s (%d), %s, zoom %.2f, scale %.3f, %d zones / %d base tiles / %d overlay tiles / %d icons.",
		info and info.name or "?", mapID or 0, active and "stitched" or "Blizzard's",
		active and select(3, View()) or 0, sc:GetCanvasScale(),
		S.stats.zones, S.stats.tiles, S.stats.overlays, S.stats.pins)
	local fixed, live = S.RegionCount()
	local kb
	if UpdateAddOnMemoryUsage and GetAddOnMemoryUsage then
		UpdateAddOnMemoryUsage()
		kb = GetAddOnMemoryUsage(ns.name)
	end
	ns:Print("World map: %d art regions, %d live ones; addon memory %s.", fixed, live, kb and ("%.1f MB"):format(kb / 1024) or "?")
	if map:IsVisible() then
		ns:Print("Drawing %d of the art's textures now; %.0f frames a second.", S.DrawnCount(), GetFramerate())
	else
		ns:Print("The map is closed: open it and run this again for what it's drawing.")
	end
	if #openTimes > 0 then
		local list = {}
		for i, t in ipairs(openTimes) do list[i] = ("%.0f (OpenMap %.0f)"):format(t[1], t[2]) end
		ns:Print("Opening the map took %s ms, latest first; the rest is the game and other addons.", table.concat(list, ", "))
		local parts = {}
		for name, ms in pairs(openLast) do parts[#parts + 1] = { name, ms } end
		table.sort(parts, function(a, b) return a[2] > b[2] end)
		for i, p in ipairs(parts) do parts[i] = ("%s %.0f"):format(p[1], p[2]) end
		if #parts > 0 then ns:Print("  the latest, by part (ms; parts can run inside each other): %s.", table.concat(parts, ", ")) end
	end
	local registered, shown, placed, ours, moved
	if mod.QuestieStatus then registered, shown, placed, ours, moved = mod.QuestieStatus() end
	if registered then
		ns:Print("Questie: %d map icons, %d on this map (%d placed by Questie, %d of those moved to Forever's positions, %d placed by OpenMap), map %d.",
			registered, shown, placed, moved, ours, map:GetMapID() or 0)
	end
	local cv = S.closeView or {}
	ns:Print("Up close: zoom %.1f, softening %.0f%%, minimap %.0f%% (%d tiles, %d in the gaps); %d view updates, the last %.1fs ago; %.2f ms each (worst %.1f).",
		cv.zoom or 0, (cv.soft or 0) * 100, (cv.mix or 0) * 100, cv.tiles or 0, cv.gapTiles or 0,
		cv.updates or 0, cv.time and (GetTime() - cv.time) or -1, cv.ms or 0, cv.worst or 0)
	cv.worst = 0
	-- its slowest steps (by their worst), so a slow update says where the time went
	local steps = {}
	for name, s in pairs(S.closeSteps or {}) do steps[#steps + 1] = { name, s } end
	table.sort(steps, function(a, b) return a[2].worst > b[2].worst end)
	local list = {}
	for i = 1, math.min(3, #steps) do
		list[i] = ("%s %.1f (worst %.1f)"):format(steps[i][1], steps[i][2].ms, steps[i][2].worst)
		steps[i][2].worst = 0
	end
	if #list > 0 then ns:Print("Slowest steps, ms: %s.", table.concat(list, "; ")) end
	-- and the zoom update's (S.SetZoom, "scale changed" when the map opens)
	steps = {}
	for name, st in pairs(S.zoomSteps or {}) do steps[#steps + 1] = { name, st } end
	table.sort(steps, function(a, b) return a[2].worst > b[2].worst end)
	list = {}
	for i = 1, math.min(4, #steps) do
		list[i] = ("%s %.1f (worst %.1f)"):format(steps[i][1], steps[i][2].ms, steps[i][2].worst)
		steps[i][2].worst = 0
	end
	if #list > 0 then ns:Print("Zoom update, slowest parts, ms: %s.", table.concat(list, "; ")) end
	for name, err in pairs(S.closeFailed or {}) do ns:Print("|cffff6060%s failed:|r %s", name, err) end
end


function mod:Options()
	local get, set = ns.Bind(function() return mod.db end, function() mod:Refresh() end)
	local function off() return not mod.db.enabled end
	local opts = {
		intro = ns.Desc("Blizzard's world map with every zone stitched together: scroll out of a zone into the next, drag across the whole world. The quest log, the map's controls and Questie all keep working.\n\n|cffffd100Wheel|r zooms at the cursor, |cffffd100drag|r pans, |cffffd100left-click|r zooms into the place under the cursor, |cffffd100right-click|r zooms out a level.\n\nIf you use Leatrix Maps or another world map addon, turn it off.", 1),
		autoSwitch = { type = "toggle", name = "Follow the view", order = 10, width = "full", get = get, set = set, disabled = off,
			desc = "Once the map stops moving, the map underneath becomes the zone or continent you're looking at, so quest areas, coordinates and the zone name match what's on screen." },
		lookHeader = ns.Header("Look", 20),
		colorMatch = { type = "range", name = "Colour matching", order = 21, min = 0, max = 1, step = 0.05, isPercent = true,
			get = get, set = set, disabled = off,
			desc = "How far each zone's borders move toward a shared palette, so mountains and borders hand over smoothly between zones. Zone interiors keep their own colours." },
		desaturate = { type = "range", name = "Take colour out", order = 22, min = 0, max = 0.6, step = 0.05, isPercent = true,
			get = get, set = set, disabled = off },
		unexplored = { type = "select", name = "Unexplored areas", order = 23, get = get, set = set, disabled = off,
			values = { show = "Show", dim = "Dim", hide = "Hide" }, sorting = { "show", "dim", "hide" },
			desc = "Areas you haven't explored yet: shown as they are, dimmed, or hidden like Blizzard's own map (blank parchment until you get there)." },
		maxZoom = { type = "range", name = "Deepest zoom", order = 24, min = 16, max = 96, step = 4,
			get = get, set = function(info, v) set(info, v) if map and active then sc:OnCanvasSizeChanged() end end, disabled = off,
			desc = "Times the whole-world view." },
		iconHeader = ns.Header("Icons", 30),
		routes = { type = "toggle", name = "Boat and zeppelin routes", order = 34, get = get, set = set, disabled = off },
		icons = { type = "toggle", name = "Dungeons, travel and more", order = 31, get = get, set = set, disabled = off,
			desc = "Dungeon and raid entrances, boats and zeppelins (click: the other end)." },
		flight = { type = "toggle", name = "Flight masters", order = 32, get = get, set = set,
			disabled = off },
	}
	if mod.ExtraOptions then mod:ExtraOptions(opts, get, set, off) end
	if mod.NavOptions then mod:NavOptions(opts, get, set, off) end
	if mod.WindowOptions then mod:WindowOptions(opts, get, set, off) end
	if mod.CloseOptions then mod:CloseOptions(opts, get, set, off) end
	return opts
end
