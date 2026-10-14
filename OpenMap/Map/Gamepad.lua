--------------------------------------------------------------------------------
-- The gamepad (Forever's gamepad mode). On the map Blizzard moves a cursor of its own
-- (SoftCursor) with the left stick and zooms with the right; WorldMap.lua zooms the stitched
-- map about that cursor and makes its A and X zoom in and out as clicks do. That cursor has
-- no mouse-over: here, what's under it (OpenMap's buttons and menu, its map icons) is entered
-- and left as the mouse would (tooltips, highlights), and A presses it.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

local REACH = 12                -- px from the cursor that an icon counts as under it (Blizzard's for its own)
local EVERY = 0.05              -- seconds between looks at what's under the cursor
local roots = {}                -- OpenMap's controls on the map (Panel, Paint, Report add theirs)
mod.padRoots = roots
local hovered                   -- what's under the cursor, entered
local found, foundLevel, blocked

local function Inside(f, x, y)
	local l, b, w, h = f:GetRect()
	if not l then return false end
	local es = f:GetEffectiveScale()
	local il, ir, it, ib = f:GetHitRectInsets()
	x, y = x / es, y / es
	return x >= l + il and x <= l + w - ir and y >= b + ib and y <= b + h - it
end

local function Pressable(f)
	return f:IsObjectType("Button") or f:IsObjectType("Slider") or f:IsObjectType("EditBox")
end

-- the topmost pressable frame at (x, y) in f and its children (found); blocked: a frame
-- that takes the mouse is there (the menu's background), so the map under it isn't
local Find
local function FindIn(x, y, ...)
	for i = 1, select("#", ...) do Find((select(i, ...)), x, y) end
end
function Find(f, x, y)
	if not f:IsVisible() then return end
	if f:IsMouseEnabled() and Inside(f, x, y) then
		blocked = true
		if Pressable(f) and (not found or f:GetFrameLevel() >= foundLevel) then found, foundLevel = f, f:GetFrameLevel() end
	end
	FindIn(x, y, f:GetChildren())
end

-- OpenMap's control under (x, y), or its map icon; and whether a control is in the way
local function Under(x, y)
	found, foundLevel, blocked = nil, nil, false
	for _, root in ipairs(roots) do Find(root, x, y) end
	if found or blocked then return found, blocked end
	local pin = S.IsBuilt() and mod.IsStitched() and S.PinAt(x, y, REACH)
	if pin then return pin, true end
	return nil, false
end

local function Enter(f)
	if f == hovered then return end
	local was = hovered
	hovered = f
	if was then
		if was.UnlockHighlight then was:UnlockHighlight() end
		local leave = was:GetScript("OnLeave")
		if leave then leave(was, false) end
	end
	if f then
		if f.LockHighlight then f:LockHighlight() end
		local enter = f:GetScript("OnEnter")
		if enter then enter(f, false) end
	end
end

-- A, with the gamepad's cursor at (x, y): true if it was OpenMap's to take
function mod.PadPress(x, y)
	local f, taken = Under(x, y)
	if not f then return taken end
	if f:IsObjectType("Slider") then
		-- to the value at the cursor
		local lo, hi = f:GetMinMaxValues()
		local l, _, w = f:GetRect()
		if l and w > 0 and hi > lo then
			local v = lo + (hi - lo) * math.max(0, math.min(1, (x / f:GetEffectiveScale() - l) / w))
			local step = f:GetValueStep()
			if step and step > 0 then v = lo + math.floor((v - lo) / step + 0.5) * step end
			f:SetValue(v)
		end
	elseif f:IsObjectType("EditBox") then
		f:SetFocus()
	elseif f.OnClick and not f:GetScript("OnClick") then
		f:OnClick()             -- (a map icon: its click, as WorldMap.lua's OnPinMouseUp gives it)
	else
		f:Click()
	end
	return true
end

function mod:SetupGamepad(worldMap)
	local driver = CreateFrame("Frame", nil, worldMap)
	local wait = 0
	driver:SetScript("OnUpdate", function(_, elapsed)
		wait = wait - elapsed
		if wait > 0 then return end
		wait = EVERY
		local x, y = mod.PadCursor()
		Enter(x and (Under(x, y)) or nil)
	end)
	driver:SetScript("OnHide", function() Enter(nil) end)
end
