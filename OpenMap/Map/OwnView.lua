--------------------------------------------------------------------------------
-- The own view: the map in a fight on frames of OpenMap's own (drafts: own-frame-map).
--
-- Out of combat OpenMap's art is on Blizzard's map canvas, and OpenMap scrolls and scales that canvas
-- (WorldMap.lua's SetView). In a fight nothing of Blizzard's map may be set from OpenMap's code: its
-- canvas holds a protected pin, and a field OpenMap writes there is read by the game's own code, which
-- then blocks the quest log's protected calls (#345 #347 #368). So in a fight the art (Stitch.lua's root),
-- the sea chart and OpenMap's icons (pinRoot) are moved onto a view of OpenMap's own, over Blizzard's
-- canvas, which OpenMap scrolls and scales itself, as a scroll frame would: the host map's point (x, y)
-- at the view's centre at canvas scale `scale` (WorldMap.lua's own: View, SetView, ApplyZoom read it).
-- The view takes the wheel, drags and clicks; HereBeDragons' icons (Questie's, other addons') are put on
-- it at their world point; your quests are OpenMap's own icons (Quests.lua, as on the controller view).
-- Blizzard's canvas, left as it is under it, is only made see-through meanwhile (its alpha).
-- As combat ends (mod.CombatOver) the view is put on Blizzard's canvas and everything goes back.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

local LEVEL = 9200              -- the view's frame level: over Blizzard's canvas and its icons (OpenMap lifts
                                --  its own arrow to 9500, a dungeon's map is up to 9840)
local ICONS_OVER = 12           -- HereBeDragons' icons, this many levels over OpenMap's (#393)
local QUESTIE_FROM = 2.5        -- the zoom Questie's icons come in at (a continent's worth of quests is too many)
local SCAN_EVERY = 0.25         -- seconds between looks at which icons the addons have
local QUESTIE_LIB = "HereBeDragonsQuestie-Pins-2.0"

local map, sc, view, canvas, iconLayer, input
local own                       -- WorldMap.lua's mod.own: { on, scale, x, y, u, v, zoom }
local levels = {}               -- OpenMap's frame -> its level on Blizzard's canvas (given back as the view ends)
local moved = {}                -- an addon's icon -> its parent before (given back as the view ends)
local strataOf = {}             -- OpenMap's icon layers -> their strata before (given back as the view ends)
local ICON_STRATA = "HIGH"      -- the icons' strata on the view: over the art's (the map's own), whatever the levels
local levelOf = {}              -- an addon's icon -> { level, fixed }: its own before (given back too)
local drag                      -- { sx, sy, u, v, zoom, moved }: a drag under way
local scanAt = 0
local placedScale             -- the view's scale your group's dots were last sized for

-- every copy of the pins library loaded: name -> library (as the controller view's, PadView.lua)
local function PinLibs()
	local out = {}
	local q = mod.QuestieModule and mod.QuestieModule()   -- (Questie 12.8 and later: Extras.lua)
	if q then out[mod.QUESTIE_MODULE] = q end
	if not LibStub then return out end
	if LibStub.IterateLibraries then
		for name, lib in LibStub:IterateLibraries() do
			if type(name) == "string" and type(lib) == "table"
				and (name:match("^HereBeDragons.*%-Pins%-2%.0$") or name == "HereBeDragons-Pins-ZGV") then
				out[name] = lib
			end
		end
	else
		out[QUESTIE_LIB] = LibStub(QUESTIE_LIB, true)
	end
	return out
end
mod.OwnPinLibs = PinLibs

-- an icon's place in the world (normalized), from the library's data
local function IconWorld(icon, data)
	local uiMapID = data.uiMapID
	if uiMapID and icon.UiMapID == uiMapID and type(icon.x) == "number" and type(icon.y) == "number" then
		local l, r, t, b = S.Rect(uiMapID)
		if l then return l + icon.x / 100 * (r - l), t + icon.y / 100 * (b - t) end
	end
	-- (the library's x, y are the game's world Y, X: Extras.lua)
	if type(data.instanceID) == "number" and type(data.x) == "number" and type(data.y) == "number" and S.FromYards then
		return S.FromYards(data.instanceID, data.y, data.x)
	end
end

-- which icons the addons have, and where: icon -> { u, v, Questie's, its show flag } (looked at every
-- SCAN_EVERY: placing them, every frame of a zoom, reads only this)
local at = {}
local function ScanIcons()
	wipe(at)
	for name, lib in pairs(PinLibs()) do
		local pins = lib.worldmapPins
		local questie = name == QUESTIE_LIB or name == mod.QUESTIE_MODULE
		if type(pins) == "table" then
			for icon, data in pairs(pins) do
				if type(icon) == "table" and type(data) == "table" and icon.SetPoint and not (questie and icon.type == "line") then
					local ok, wu, wv = pcall(IconWorld, icon, data)
					if ok and wu and wv then at[icon] = { wu, wv, questie, tonumber(data.worldMapShowFlag) or 0 } end
				end
			end
		end
	end
end
mod.OwnScanIcons = ScanIcons

-- the addons' icons in view put on the view, at their world point; the rest hidden there
local function PlaceIcons()
	if not iconLayer or not own.on then return end
	local u, v, zoom = own.u, own.v, own.zoom
	if not (u and zoom) then return end
	local pu, pv = input.PerPx(zoom)
	local hw, hh = view:GetWidth() / 2 + 16, view:GetHeight() / 2 + 16
	local profile = _G.Questie and Questie.db and Questie.db.profile
	local questieOn = zoom >= QUESTIE_FROM and not (profile and profile.enabled == false)
	local seen = {}
	for icon, a in pairs(at) do
		local x, y = (a[1] - u) / pu, (a[2] - v) / pv
		local on
		if a[3] then on = questieOn else on = zoom >= QUESTIE_FROM or a[4] >= 2 end
		if on and x > -hw and x < hw and y > -hh and y < hh then
			-- (its pin as it is now: the library may have put it on another since, in the fight)
			if icon:GetParent() ~= iconLayer then
				local was = levelOf[icon] or { level = icon:GetFrameLevel(),
					fixed = icon.HasFixedFrameLevel and icon:HasFixedFrameLevel() or false }
				levelOf[icon] = was
				moved[icon] = icon:GetParent() or false
				icon:SetParent(iconLayer)
				was.strata = was.strata or icon:GetFrameStrata()
				icon:SetFrameStrata(ICON_STRATA)
				-- (Questie fixes its icons' levels, from 2015 up: a fixed level stays put whatever the parent's,
				-- under the view's art. Over the layer here, in Questie's own order; given back as the view ends)
				if icon.SetFixedFrameLevel then icon:SetFixedFrameLevel(false) end
				icon:SetFrameLevel(math.min(9950, iconLayer:GetFrameLevel() + 1 + math.max(0, math.min(30, was.level - 2015))))
				if was.fixed and icon.SetFixedFrameLevel then icon:SetFixedFrameLevel(true) end
			end
			icon:ClearAllPoints()
			icon:SetPoint("CENTER", iconLayer, "CENTER", x, -y)
			icon:Show()
			seen[icon] = true
		end
	end
	for icon in pairs(moved) do
		if not seen[icon] and icon:GetParent() == iconLayer then icon:Hide() end
	end
end
mod.OwnPlaceIcons = PlaceIcons

-- the icons given back: to the pin they were on, centred on it as the library has them; hidden otherwise
local function GiveBackIcons()
	for icon, parent in pairs(moved) do
		if icon:GetParent() == iconLayer then
			icon:ClearAllPoints()
			local was = levelOf[icon]
			if parent then
				icon:SetParent(parent)
				if was then
					if icon.SetFixedFrameLevel then icon:SetFixedFrameLevel(false) end
					if was.strata then icon:SetFrameStrata(was.strata) end
					icon:SetFrameLevel(was.level)
					if was.fixed and icon.SetFixedFrameLevel then icon:SetFixedFrameLevel(true) end
				end
				icon:SetPoint("CENTER", parent, "CENTER")
				if parent.IsShown and parent:IsShown() then icon:Show() else icon:Hide() end
			else
				icon:Hide()
			end
		end
	end
	wipe(moved)
	wipe(at)
	wipe(levelOf)
end

-- the canvas where the view is: the host map's (x, y) at the view's centre at `scale`, as a scroll frame does
function mod.OwnViewPlace()
	if not own.on or not canvas then return end
	local w, h = sc.Child:GetWidth(), sc.Child:GetHeight()       -- (read only: the canvas's size is Blizzard's)
	if not (w and h and w > 0 and h > 0 and own.scale and own.scale > 0) then return end
	if canvas:GetWidth() ~= w or canvas:GetHeight() ~= h then canvas:SetSize(w, h) end
	canvas:SetScale(own.scale)
	canvas:ClearAllPoints()
	canvas:SetPoint("TOPLEFT", view, "TOPLEFT", view:GetWidth() / 2 / own.scale - own.x * w,
		-(view:GetHeight() / 2 / own.scale - own.y * h))
	PlaceIcons()
	if mod.OwnQuestAreaMoved then mod.OwnQuestAreaMoved() end     -- (a quest's area: PadView.lua)
	-- (your group's dots are sized for the view's scale: Nav.lua's)
	if own.scale ~= placedScale then
		placedScale = own.scale
		if mod.RefreshGroup then pcall(mod.RefreshGroup) end
	end
end

-- OpenMap's frames moved up to the view's levels (and given their own back), keeping their order. Every
-- frame's level is read first, then each set from it, parents before children: the game moves a frame's
-- children with it when its level changes, so a level read after its parent moved was counted twice (every
-- frame ended at the top, the art over the icons: no icons in a fight)
local lifted = {}               -- the frames in the order they were lifted (parents first)
local LiftNew                   -- (below)
local function Collect(frame, list)
	if not frame then return end
	list[#list + 1] = frame
	for _, child in ipairs({ frame:GetChildren() }) do Collect(child, list) end
end
-- (read before the frames are moved onto the view: the game resets a frame's level, and its children's with
-- it, when it's given another parent, so levels read after S.Rehost were already moved: the art and the icons
-- both ended at the top, the art over the icons)
local function Note(tops)
	local list = {}
	for _, top in ipairs(tops) do Collect(top, list) end
	for _, f in ipairs(list) do if levels[f] == nil then levels[f] = f:GetFrameLevel() end end
	return list
end
local function Lift(list, step)
	for _, f in ipairs(list) do
		f:SetFrameLevel(math.min(9900, levels[f] + step))
		lifted[#lifted + 1] = f
	end
end
-- frames OpenMap made since the view came up, at the art's own levels (the close-up's, a shade's ...): under
-- the view, unseen: lifted as the rest were (one made at its parent's level already is over the view)
local liftStep, liftTops
LiftNew = function()
	if not liftStep then return end
	local list = {}
	for _, top in ipairs(liftTops) do Collect(top, list) end
	for _, f in ipairs(list) do
		if levels[f] == nil and f:GetFrameLevel() < LEVEL then
			levels[f] = f:GetFrameLevel()
			f:SetFrameLevel(math.min(9900, levels[f] + liftStep))
			lifted[#lifted + 1] = f
		end
	end
end
local function Lower()
	for _, f in ipairs(lifted) do
		if levels[f] then f:SetFrameLevel(levels[f]) end
	end
	wipe(lifted)
	wipe(levels)
	liftStep, liftTops = nil, nil
end

local function Build()
	if view then return true end
	view = CreateFrame("Frame", nil, sc)
	view:SetAllPoints(sc)
	view:SetFrameLevel(LEVEL)
	if view.SetClipsChildren then view:SetClipsChildren(true) end
	view:Hide()
	canvas = CreateFrame("Frame", nil, view)
	canvas:SetFrameLevel(LEVEL + 1)
	iconLayer = CreateFrame("Frame", nil, view)
	iconLayer:SetAllPoints(view)
	-- the mouse: the map's own zoom, drag and clicks, on this view (Blizzard's canvas handlers not called)
	view:EnableMouse(true)
	view:EnableMouseWheel(true)
	view:SetScript("OnMouseWheel", function(_, delta) input.Wheel(nil, delta) end)
	view:SetScript("OnMouseDown", function(_, button)
		input.PressDown(nil, button)
		mod.OwnDragStart(button)
		input.Grab()
	end)
	view:SetScript("OnMouseUp", function(_, button)
		local dragged = mod.OwnDragStop()
		if button == "MiddleButton" then if mod.FindMe then mod:FindMe(true) end return end
		if not dragged then input.Click(button) end
	end)
	-- (the window resized in a fight: the art, OpenMap's icons and your arrow laid out for it, not only the
	-- addons' icons, which PlaceIcons puts by the view's size)
	view:SetScript("OnSizeChanged", function() if mod.OwnViewResized then mod.OwnViewResized() end end)
	view:SetScript("OnUpdate", function(_, elapsed)
		mod.OwnDragTrack()
		scanAt = scanAt + elapsed
		if scanAt >= SCAN_EVERY then scanAt = 0 ScanIcons() PlaceIcons() LiftNew() end
	end)
	return true
end

-- a drag on the view (or on one of OpenMap's icons in a fight): the view carried with the cursor
function mod.OwnDragStart(button)
	if not own.on or button ~= "LeftButton" then return end
	local u, v, zoom = input.View()
	local sx, sy = input.CursorOffset()
	drag = { sx = sx, sy = sy, u = u, v = v, zoom = zoom, moved = false }
end
function mod.OwnDragTrack()
	if not drag then return end
	if not IsMouseButtonDown("LeftButton") or not own.on then return end
	local sx, sy = input.CursorOffset()
	local dx, dy = sx - drag.sx, sy - drag.sy
	if not drag.moved and dx * dx + dy * dy <= 20 then return end   -- (Blizzard's click distance, squared)
	drag.moved = true
	local pu, pv = input.PerPx(drag.zoom)
	if mod.ShowNow then mod.ShowNow(drag.u - dx * pu, drag.v - dy * pv, drag.zoom) end
end
-- the drag over: whether it moved (a press that didn't is a click)
function mod.OwnDragStop()
	local d = drag
	drag = nil
	return d and d.moved or false
end

function mod.OwnViewOn() return own and own.on or false end
-- for what draws on the view itself (your party's dots, Nav.lua; a quest's area, PadView.lua): its canvas, its
-- scale, and the level and strata of OpenMap's icons on it; nil while it's down
function mod.OwnCanvas()
	if not (own and own.on and canvas) then return end
	local _, pinRoot = S.Roots()
	return canvas, own.scale, pinRoot:GetFrameLevel(), pinRoot:GetFrameStrata()
end
-- for Extras.lua's place name: the cursor over the view (Blizzard's canvas, under it, never has the mouse then)
function mod.OwnViewHover() return own and own.on and view and view:IsMouseOver() or false end

-- up, at the view Blizzard's canvas has now (nothing moves on screen): true if it's up
function mod.OwnViewStart()
	if not (map and sc and S.IsBuilt and S.IsBuilt()) then return false end
	if own.on then return true end
	if not (mod.IsStitched and mod.IsStitched()) or not map:IsShown() or not InCombatLockdown() then return false end
	if mod.PadViewOn and mod.PadViewOn() then return false end
	if not Build() then return false end
	local mapID = map:GetMapID()
	local scale = sc:GetCanvasScale()
	local x, y = sc:GetCurrentScrollX(), sc:GetCurrentScrollY()
	if not (mapID and scale and scale > 0 and ns.Safe.Finite(scale, x, y)) then return false end
	own.on, own.scale, own.x, own.y = true, scale, x, y
	own.u, own.v = input.View()
	local _, _, zoom = input.View()
	own.zoom = zoom
	local root, pinRoot, chart = S.Roots()
	local tops = { root, pinRoot }
	if chart then table.insert(tops, 1, chart) end
	local list = Note(tops)
	local step = LEVEL + 2 - levels[root]
	liftStep, liftTops = step, tops
	S.Rehost(canvas)
	Lift(list, step)
	iconLayer:SetFrameLevel(pinRoot:GetFrameLevel() + ICONS_OVER)
	-- (and a strata over the art's, so no level of the art's, or one an addon sets on its icons, can cover them)
	for _, f in ipairs({ pinRoot, iconLayer }) do
		strataOf[f] = strataOf[f] or f:GetFrameStrata()
		f:SetFrameStrata(ICON_STRATA)
	end
	-- OpenMap's own frames on the map's view that sit over the art (the coordinates, the brightness shade):
	-- over this view too, in their order (they're under it otherwise: the coordinates went in a fight)
	local over = {}
	local bar = mod.CoordsBar and mod.CoordsBar()
	if mod.brightnessShade then over[#over + 1] = mod.brightnessShade end
	if bar then over[#over + 1] = bar end
	for i, f in ipairs(over) do
		if levels[f] == nil then levels[f] = f:GetFrameLevel() lifted[#lifted + 1] = f end
		f:SetFrameLevel(math.min(9900, iconLayer:GetFrameLevel() + (f == bar and 20 or -ICONS_OVER - 1)))
	end
	sc.Child:SetAlpha(0)          -- (Blizzard's canvas and its icons, under the view: unseen; nothing of it written)
	view:Show()
	ScanIcons()
	mod.OwnViewPlace()
	if mod.RefreshQuests then pcall(mod.RefreshQuests, mod) end   -- (your quests as OpenMap's icons: Quests.lua)
	if mod.RefreshGroup then pcall(mod.RefreshGroup) end     -- (your group on the view: Nav.lua)
	return true
end

-- down: `sync` (combat over) has WorldMap.lua put the view on Blizzard's canvas before the art goes back
function mod.OwnViewStop(sync)
	if not own or not own.on then return end
	local scale, x, y = own.scale, own.x, own.y
	own.on = false
	drag = nil
	-- (combat over: the view on Blizzard's canvas, then the art back on it, in the same frame: nothing jumps)
	if sync and not InCombatLockdown() and mod.SetViewNow then mod.SetViewNow(scale, x, y) end
	GiveBackIcons()
	S.Rehost(nil)
	for f, strata in pairs(strataOf) do f:SetFrameStrata(strata) end
	wipe(strataOf)
	Lower()                       -- (after the move back: the game resets the levels of a frame given another parent)
	if view then view:Hide() end
	sc.Child:SetAlpha(1)
	if mod.RefreshQuests then pcall(mod.RefreshQuests, mod) end
	if mod.RefreshGroup then pcall(mod.RefreshGroup) end
end

-- /openmap combatcheck: where the own view's frames are, printed and saved (OpenMapDB: worldmap, combatcheck)
-- for a report: each one's parents, shown and visible, its alpha on screen, strata and level, place and scale
local function Describe(label, f)
	if not f then return label .. ": none" end
	local chain, p = {}, f
	for _ = 1, 6 do
		if not p then break end
		chain[#chain + 1] = (p.GetDebugName and p:GetDebugName()) or (p.GetName and p:GetName()) or tostring(p)
		p = p.GetParent and p:GetParent() or nil
	end
	local x, y
	if f.GetCenter then x, y = f:GetCenter() end
	local w, h = f.GetWidth and f:GetWidth() or 0, f.GetHeight and f:GetHeight() or 0
	local frame = f.GetFrameLevel and f or (f.GetParent and f:GetParent())
	return ("%s: shown %s visible %s alpha %.2f eff %.2f strata %s level %s at %s,%s size %.0fx%.0f scale %.3f eff %.3f | %s"):format(
		label, tostring(f:IsShown()), tostring(f:IsVisible()), f:GetAlpha() or -1,
		f.GetEffectiveAlpha and f:GetEffectiveAlpha() or -1,
		frame and frame.GetFrameStrata and frame:GetFrameStrata() or "?", frame and frame.GetFrameLevel and frame:GetFrameLevel() or "?",
		x and ("%.0f"):format(x) or "nil", y and ("%.0f"):format(y) or "nil", w, h,
		f.GetScale and f:GetScale() or -1, f.GetEffectiveScale and f:GetEffectiveScale() or -1, table.concat(chain, " < "))
end
function mod:CombatCheck()
	local lines = {}
	local function add(line) lines[#lines + 1] = line end
	add(("combat %s, own view %s, map shown %s, stitched %s"):format(tostring(InCombatLockdown()), tostring(own and own.on),
		tostring(map and map:IsShown()), tostring(mod.IsStitched and mod.IsStitched())))
	if own then
		add(("own: scale %s x %s y %s u %s v %s zoom %s"):format(tostring(own.scale), tostring(own.x), tostring(own.y),
			tostring(own.u), tostring(own.v), tostring(own.zoom)))
	end
	local root, pinRoot, chart = S.Roots()
	add(Describe("view", view))
	add(Describe("canvas", canvas))
	add(Describe("Blizzard canvas", sc and sc.Child))
	add(Describe("art (root)", root))
	add(Describe("icons (pinRoot)", pinRoot))
	add(Describe("chart", chart))
	add(Describe("addons' icons layer", iconLayer))
	local arrowFrame, pins, arrowTex
	if S.DiagFrames then arrowFrame, pins, arrowTex = S.DiagFrames(6) end
	add(Describe("arrow frame", arrowFrame))
	add(Describe("arrow", arrowTex))
	for i, e in ipairs(pins or {}) do add(Describe("pin " .. i .. " (" .. tostring(e[1]) .. ")", e[2])) end
	local n = 0
	for icon in pairs(moved) do
		n = n + 1
		if n <= 4 then add(Describe("addon icon " .. n, icon)) end
	end
	add(("addons' icons moved: %d, known: %d"):format(n, (function() local c = 0 for _ in pairs(at) do c = c + 1 end return c end)()))
	mod.db.combatcheck = { at = date and date("%Y-%m-%d %H:%M:%S") or "", lines = lines }
	for _, line in ipairs(lines) do ns:Print(line) end
	ns:Print("Saved for a report: /reload, then it's in OpenMapDB (worldmap, combatcheck).")
end

function mod:SetupOwnView(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	own = mod.own
	input = mod.OwnInput()
end
