--------------------------------------------------------------------------------
-- The map window: drag its title bar to move it, drag the corner grip to make it
-- any width and height (the stitched map has no edges to keep a shape for); both are
-- remembered, and a size slider scales the whole window. Only the windowed map: the maximized map is left to
-- Blizzard. Blizzard's panel layout tables are left alone (writing to them can
-- taint): the saved place is put back each time Blizzard lays the map out.
--------------------------------------------------------------------------------

local _, ns = ...
local mod = ns:GetModule("worldmap")
local L = ns.L

local d = mod.defaults
d.window = false                -- { point, relPoint, x, y } once moved
d.windowScale = 1
d.windowSize = false            -- { width, height } once resized
d.fullWidth = true              -- the maximized map fills the screen's width (the stitched map has no edges to keep)
local MIN_SCALE, MAX_SCALE = 0.5, 1.6
local MIN_W, MIN_H = 480, 320

d.border = true                 -- the map art's parchment frame round the stitched map

local map, handle, grip, border
local FillScreen, SetupBorder
local blizzardSize              -- the windowed map's own size, for a reset

local function Refit()
	local sc = map.ScrollContainer
	if sc and sc.OnCanvasSizeChanged then sc:OnCanvasSizeChanged() end
end

local function Maximized()
	return map.IsMaximized and map:IsMaximized()
end

local function Apply()
	if not map or Maximized() then return end
	local w = mod.db.window
	if w then
		map:ClearAllPoints()
		map:SetPoint(w[1], UIParent, w[2], w[3], w[4])
	end
	if math.abs((map:GetScale() or 1) - mod.db.windowScale) > 0.001 then map:SetScale(mod.db.windowScale) end
	local size = mod.db.windowSize
	if size and not InCombatLockdown() and (math.abs(map:GetWidth() - size[1]) > 0.5 or math.abs(map:GetHeight() - size[2]) > 0.5) then
		map:SetSize(size[1], size[2])
		Refit()
	end
end

-- maximized: Blizzard keeps the map art's shape (black bars at the sides on a wide
-- screen); the stitched map is the whole world, so it takes the screen's full width
FillScreen = function()
	if not map or not Maximized() or InCombatLockdown() then return end
	if math.abs((map:GetScale() or 1) - 1) > 0.001 then map:SetScale(1) end   -- (the windowed size is the window's)
	if not mod.db.fullWidth then return end
	local w = math.floor(UIParent:GetWidth())
	if math.abs(map:GetWidth() - w) < 1 then return end
	map:SetWidth(w)
	Refit()
end

local function Save()
	local point, _, relPoint, x, y = map:GetPoint(1)
	if point then mod.db.window = { point, relPoint, x, y } end
end

function mod:ResetWindow()
	mod.db.window = false
	mod.db.windowScale = 1
	mod.db.windowSize = false
	if map then
		map:SetScale(1)
		if blizzardSize and not Maximized() then map:SetSize(blizzardSize[1], blizzardSize[2]) Refit() end
		if map:IsShown() and not InCombatLockdown() then HideUIPanel(map) ShowUIPanel(map) end
	end
end

--------------------------------------------------------------------------------
-- The border: the map art's own parchment frame round the stitched map's view, cut in
-- nine (tools/map-art/border.py): the corners as they are, the edges stretched, so
-- the map keeps its edge whatever its shape. Sized to the view; it takes no clicks.
--------------------------------------------------------------------------------

local BORDER = ns.Media.path .. "Textures\\MapBorder\\"
local CORNER, SIDE = 192 / 256, 640 / 1024   -- the pieces' content on their canvases (border.py)
local BORDER_SCALE = 0.55       -- the corners' size: their own 192 px x this, per 1024 px of view height

local function Piece(name)
	local tex = border:CreateTexture(nil, "OVERLAY")
	tex:SetTexture(BORDER .. name, nil, nil, "LINEAR")
	return tex
end

local function SizeBorder()
	local c = 192 * BORDER_SCALE * map.ScrollContainer:GetHeight() / 1024
	for _, tex in ipairs(border.corners) do tex:SetSize(c, c) end
	border.top:SetHeight(c)
	border.bottom:SetHeight(c)
	border.left:SetWidth(c)
	border.right:SetWidth(c)
end

SetupBorder = function()
	local sc = map.ScrollContainer
	border = CreateFrame("Frame", nil, map)
	border:SetAllPoints(sc)
	border:SetFrameLevel(math.min(sc:GetFrameLevel() + 9000, 9900))   -- (over the map's icons, under OpenMap's menu)
	local tl, tr, bl, br = Piece("tl"), Piece("tr"), Piece("bl"), Piece("br")
	tl:SetPoint("TOPLEFT")
	tr:SetPoint("TOPRIGHT")
	bl:SetPoint("BOTTOMLEFT")
	br:SetPoint("BOTTOMRIGHT")
	for _, tex in ipairs({ tl, tr, bl, br }) do tex:SetTexCoord(0, CORNER, 0, CORNER) end
	local top, bottom, left, right = Piece("top"), Piece("bottom"), Piece("left"), Piece("right")
	top:SetPoint("TOPLEFT", tl, "TOPRIGHT")
	top:SetPoint("TOPRIGHT", tr, "TOPLEFT")
	bottom:SetPoint("BOTTOMLEFT", bl, "BOTTOMRIGHT")
	bottom:SetPoint("BOTTOMRIGHT", br, "BOTTOMLEFT")
	top:SetTexCoord(0, 1, 0, CORNER)
	bottom:SetTexCoord(0, 1, 0, CORNER)
	left:SetPoint("TOPLEFT", tl, "BOTTOMLEFT")
	left:SetPoint("BOTTOMLEFT", bl, "TOPLEFT")
	right:SetPoint("TOPRIGHT", tr, "BOTTOMRIGHT")
	right:SetPoint("BOTTOMRIGHT", br, "TOPRIGHT")
	left:SetTexCoord(0, CORNER, 0, SIDE)
	right:SetTexCoord(0, CORNER, 0, SIDE)
	border.corners, border.top, border.bottom, border.left, border.right = { tl, tr, bl, br }, top, bottom, left, right
	sc:HookScript("OnSizeChanged", SizeBorder)
	SizeBorder()
	-- only round the stitched map (Blizzard's own maps have their frame in their art)
	local shown
	local watch = CreateFrame("Frame", nil, map)
	watch:SetScript("OnUpdate", function()
		local want = mod.db.border and mod.IsStitched() or false
		if want ~= shown then
			shown = want
			border:SetShown(want)
		end
	end)
end

function mod:SetupWindow(worldMap)
	map = worldMap
	map:SetClampedToScreen(true)
	if not Maximized() then blizzardSize = { map:GetWidth(), map:GetHeight() } end

	-- the title bar: a strip along the top, clear of the corner buttons
	handle = CreateFrame("Frame", nil, map)
	handle:SetPoint("TOPLEFT", map, "TOPLEFT", 70, 0)
	handle:SetPoint("TOPRIGHT", map, "TOPRIGHT", -70, 0)
	handle:SetHeight(22)
	handle:SetFrameLevel(map:GetFrameLevel() + 5)
	handle:EnableMouse(true)
	handle:RegisterForDrag("LeftButton")
	handle:SetScript("OnDragStart", function()
		if Maximized() then return end
		map:SetMovable(true)
		map:StartMoving()
	end)
	handle:SetScript("OnDragStop", function()
		map:StopMovingOrSizing()
		map:SetUserPlaced(false)            -- (ours to remember, not the layout cache's)
		Save()
	end)
	handle:SetScript("OnEnter", function(self)
		if Maximized() then return end
		GameTooltip:SetOwner(self, "ANCHOR_TOP")
		GameTooltip:AddLine(L["Drag to move the map"], 1, 1, 1)
		GameTooltip:Show()
	end)
	handle:SetScript("OnLeave", GameTooltip_Hide)

	-- the resize grip: any width and height, the top-left corner staying put
	grip = CreateFrame("Button", nil, map)
	grip:SetSize(16, 16)
	grip:SetPoint("BOTTOMRIGHT", map, "BOTTOMRIGHT", -2, 2)
	grip:SetFrameLevel(map:GetFrameLevel() + 20)
	grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
	grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
	grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
	local start
	grip:SetScript("OnMouseDown", function()
		if Maximized() then return end
		local x, y = GetCursorPosition()
		start = { x = x, y = y, w = map:GetWidth(), h = map:GetHeight(), left = map:GetLeft(), top = map:GetTop() }
	end)
	grip:SetScript("OnMouseUp", function()
		if not start then return end
		start = nil
		mod.db.windowSize = { math.floor(map:GetWidth() + 0.5), math.floor(map:GetHeight() + 0.5) }
		Save()
		Refit()
	end)
	grip:SetScript("OnUpdate", function()
		if not start then return end
		local x, y = GetCursorPosition()
		local s = map:GetEffectiveScale()
		local w = math.max(MIN_W, start.w + (x - start.x) / s)
		local h = math.max(MIN_H, start.h - (y - start.y) / s)
		map:ClearAllPoints()
		map:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", start.left * s / UIParent:GetEffectiveScale(), start.top * s / UIParent:GetEffectiveScale())
		map:SetSize(w, h)
	end)
	grip:SetScript("OnEnter", function(self)
		GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
		GameTooltip:AddLine(L["Drag to resize the map"], 1, 1, 1)
		GameTooltip:Show()
	end)
	grip:SetScript("OnLeave", GameTooltip_Hide)

	-- put the saved place back whenever Blizzard lays the map out
	map:HookScript("OnShow", Apply)
	if UpdateUIPanelPositions then hooksecurefunc("UpdateUIPanelPositions", function() if map:IsShown() then Apply() end end) end
	local function Mode()
		local max = Maximized()
		handle:SetShown(not max)
		grip:SetShown(not max)
		if max then FillScreen() else Apply() end
	end
	if map.Maximize then hooksecurefunc(map, "Maximize", Mode) end
	if map.Minimize then hooksecurefunc(map, "Minimize", Mode) end
	-- Blizzard re-sizes the maximized map when the screen or UI scale changes
	if map.UpdateMaximizedSize then hooksecurefunc(map, "UpdateMaximizedSize", function() if Maximized() then FillScreen() end end) end
	map:HookScript("OnShow", Mode)
	SetupBorder()
	grip:SetFrameLevel(border:GetFrameLevel() + 1)
end

function mod:WindowOptions(opts, get, set, off)
	opts.windowScale = { type = "range", name = L["Map size"], order = 25, min = MIN_SCALE, max = MAX_SCALE, step = 0.05, isPercent = true,
		get = get, set = function(info, v) set(info, v) Apply() end, disabled = off,
		desc = L["Scales the whole windowed map. Drag its bottom-right corner to change its width and height, and its title bar to move it."] }
	opts.fullWidth = { type = "toggle", name = L["Full-screen map fills the width"], order = 27, get = get,
		set = function(info, v)
			set(info, v)
			if not map or not Maximized() then return end
			if map.UpdateMaximizedSize then map:UpdateMaximizedSize() else FillScreen() end   -- (off: Blizzard's size again on the next maximize)
		end, disabled = off,
		desc = L["When maximized, the map takes the screen's whole width instead of keeping Blizzard's shape with bars at the sides."] }
	opts.border = { type = "toggle", name = L["Parchment border"], order = 28, get = get, set = set, disabled = off,
		desc = L["The map art's own torn-parchment frame round the map, whatever its shape."] }
	opts.resetWindow = { type = "execute", name = L["Reset size and place"], order = 26, disabled = off,
		func = function() mod:ResetWindow() end }
end
