--------------------------------------------------------------------------------
-- No icon over another. Once the view has been still for REST after a zoom or a pan, or icons
-- have come or gone, the icons in view are laid out from the most important down: one that would
-- touch an icon already kept is moved beside its place (a width over), or faded out (no alpha, no
-- mouse) when there's no room round it either, until a later pass has room for it.
-- Only the townsfolk (vendors, trainers, mailboxes ...) give way: every other icon (dungeons, boats,
-- flight masters, quests, your own pins ...) stays as it is, and is only in their way; so are other
-- addons' icons on the map (Questie's), which aren't OpenMap's to move.
-- Cost: one pass over the icons in view, only after the view stops (not on every frame of a zoom).
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")   -- (made by WorldMap.lua: this file loads after it, OpenMap.toc)
if not (S and mod) then return end

-- the menu's choice (Panel.lua): "hide" an icon that overlaps one more important, "move" it beside
-- its place first (hidden only when there's no room round it), or "off"
mod.defaults.declutter = "hide"

local REST = 0.12               -- seconds the view must be still before a pass
local PAD = 1                   -- screen px kept between two icons
local CELL = 48                 -- screen px: the grid the kept icons are looked up in

-- sets laid out first (the higher the rank); NEVER: always kept; SKIP: lines and areas, not icons
local RANK = { waypoint = 100, ping = 100, group = 95, friends = 95, userpins = 90, notes = 90,
	quests = 80, questoffers = 75, dungeons = 70, flight = 65, boats = 60, zeppelins = 60 }
local FOREIGN = 85              -- other addons' icons: over OpenMap's quests' own
local NEVER = { waypoint = true, ping = true, group = true, friends = true, userpins = true, notes = true }
local SKIP = { route = true, routes = true, questiepaths = true, sketch = true, sketchLive = true,
	friendzones = true, exploreCount = true }
-- the townsfolk, by kind (Townsfolk.lua's keys); a kind not here: 43
local FOLK = { innkeeper = 57, classTrainer = 56, ammo = 55, repair = 54, banker = 53,
	auctioneer = 52, mailbox = 51, stable = 50, petTrainer = 49, profTrainer = 44, vendor = 42,
	spirit = 41, rare = 40 }

local function RankOf(key)
	if RANK[key] then return RANK[key] end
	if key:sub(1, 3) == "tf_" then
		local kind = key:sub(4)
		return FOLK[kind] or (kind:sub(1, 5) == "prof_" and 45) or 43
	end
	return 10
end

-- hidden / back (hidden, not see-through: a region at alpha 0 still costs its full size to draw)
local function Fade(pin, out)
	if out then
		if not pin.omClut then
			pin.omClut = true
			pin:Hide()
		end
	elseif pin.omClut then
		pin.omClut = nil
		pin:Show()
	end
end

-- an icon's box on the screen (px), or nil when it isn't laid out
local function Box(f)
	local x, y = f:GetCenter()
	if not x then return end
	local s = f:GetEffectiveScale()
	local hw, hh = f:GetWidth() * s / 2 + PAD / 2, f:GetHeight() * s / 2 + PAD / 2
	s = f:GetEffectiveScale()
	x, y = x * s, y * s
	return x - hw, y - hh, x + hw, y + hh
end

-- an OpenMap icon moved off its place by (dx, dy) screen px (0, 0: back on it): two icons at one
-- NPC (an ammo vendor who repairs) side by side, not one hidden
local function Shift(pin, dx, dy)
	if (pin.omDX or 0) == dx and (pin.omDY or 0) == dy then return end
	if not pin.anchor then return end
	local s = pin:GetEffectiveScale()
	pin:ClearAllPoints()
	pin:SetPoint("CENTER", pin.anchor, "TOPLEFT", dx / s, dy / s)
	pin.omDX, pin.omDY = dx, dy
end
-- where to try an icon, in its own widths from its place: on it, then round it
local TRY_HIDE = { { 0, 0 } }   -- ("hide": on its place or not at all)
-- (out to two widths: a small icon beside a bigger one needs more than its own width)
local TRY = { { 0, 0 } }
for _, d in ipairs({ 1, 1.5, 2 }) do
	for _, t in ipairs({ { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 0.75, 0.75 }, { -0.75, 0.75 }, { 0.75, -0.75 }, { -0.75, -0.75 } }) do
		TRY[#TRY + 1] = { t[1] * d, t[2] * d }
	end
end

-- (kept between passes and refilled, not made anew: a pass makes no garbage)
local grid, used, nUsed = {}, {}, 0     -- cell key -> list of box indices; the cells filled this pass
local boxes, nBoxes = {}, 0
local list, nList, pool = {}, 0, {}     -- the icons to lay out this pass ({ pin, rank, order, never }), pooled
local function Clear()
	for i = 1, nUsed do
		local c = grid[used[i]]
		for j = #c, 1, -1 do c[j] = nil end
		used[i] = nil
	end
	nUsed, nBoxes = 0, 0
end
local function Free(x0, y0, x1, y1)
	for gx = math.floor(x0 / CELL), math.floor(x1 / CELL) do
		for gy = math.floor(y0 / CELL), math.floor(y1 / CELL) do
			local c = grid[gx * 65536 + gy]
			if c then
				for _, i in ipairs(c) do
					local b = boxes[i]
					if x0 < b[3] and x1 > b[1] and y0 < b[4] and y1 > b[2] then return false end
				end
			end
		end
	end
	return true
end
local function Take(x0, y0, x1, y1)
	nBoxes = nBoxes + 1
	local b = boxes[nBoxes]
	if not b then b = {} boxes[nBoxes] = b end
	b[1], b[2], b[3], b[4] = x0, y0, x1, y1
	for gx = math.floor(x0 / CELL), math.floor(x1 / CELL) do
		for gy = math.floor(y0 / CELL), math.floor(y1 / CELL) do
			local key = gx * 65536 + gy
			local c = grid[key]
			if not c then c = {} grid[key] = c end
			if #c == 0 then nUsed = nUsed + 1 used[nUsed] = key end
			c[#c + 1] = nBoxes
		end
	end
end
local function Add(pin, rank, order, never)
	nList = nList + 1
	local e = pool[nList]
	if not e then e = {} pool[nList] = e end
	e[1], e[2], e[3], e[4] = pin, rank, order, never
	list[nList] = e
end
-- whether a pin is in view: its cell's own note (Stitch's culling keeps cell.here), else the frame's
local function InView(pin)
	local cell = pin.omCell
	if cell and cell.here ~= nil then return cell.here end   -- (Stitch shows a cell exactly when it is here)
	return pin:GetParent():IsVisible()
end
local function ByRank(a, b)
	if a[2] ~= b[2] then return a[2] > b[2] end
	return a[3] < b[3]
end
local function TakeForeign(pin)
	if pin:IsVisible() and (pin:GetAlpha() or 0) > 0.05 then
		local x0, y0, x1, y1 = Box(pin)
		if x0 then Take(x0, y0, x1, y1) end
	end
end

local function Pass()
	if not S.PinSets then return end
	local mode = mod.db and mod.db.declutter or "hide"
	if mode == "off" then
		-- every icon back as it was, on its place
		for _, set in pairs(S.PinSets()) do
			for _, pin in ipairs(set.pins) do
				if pin.omClut then Fade(pin, false) end
				if pin.omDX then Shift(pin, 0, 0) end
			end
		end
		return
	end
	local tries = mode == "move" and TRY or TRY_HIDE
	Clear()
	for i = nList, 1, -1 do list[i] = nil end
	nList = 0
	-- other addons' icons first, as they are
	if S.ForeignPins then S.ForeignPins(TakeForeign) end
	-- OpenMap's, each set's in view, by rank
	for key, set in pairs(S.PinSets()) do
		if not SKIP[key] and key:sub(1, 7) ~= "explore" then
			local shown = set.frame:IsVisible()
			-- (only the townsfolk give way: dungeons, boats, zeppelins, flight masters, quests and your
			-- own stay as they are, where they are, and are only in the townsfolk's way)
			local rank, never = RankOf(key), NEVER[key] or key:sub(1, 3) ~= "tf_"
			for i, pin in ipairs(set.pins) do
				-- (one hidden by an earlier pass is still a candidate: omClut)
				if shown and (pin.omClut or pin:IsShown()) and InView(pin) then
					Add(pin, rank, i, never)
				elseif pin.omClut or pin.omDX then
					Fade(pin, false)   -- (out of view: as it was, for when it comes back)
					Shift(pin, 0, 0)
				end
			end
		end
	end
	table.sort(list, ByRank)
	for n = 1, nList do
		local e = list[n]
		local pin = e[1]
		local x0, y0, x1, y1 = Box(pin)
		if not x0 then
			Fade(pin, false)
		elseif e[4] then
			if pin.omDX then        -- (moved by an older pass: back on its place first)
				Shift(pin, 0, 0)
				x0, y0, x1, y1 = Box(pin)
			end
			Fade(pin, false)
			Take(x0, y0, x1, y1)
		else
			-- (its box on its own place: less the shift it has now)
			local ox, oy = pin.omDX or 0, pin.omDY or 0
			x0, y0, x1, y1 = x0 - ox, y0 - oy, x1 - ox, y1 - oy
			local w, h = x1 - x0, y1 - y0
			local placed
			for _, t in ipairs(tries) do
				local dx, dy = t[1] * w, t[2] * h
				if Free(x0 + dx, y0 + dy, x1 + dx, y1 + dy) then
					Shift(pin, dx, dy)
					Fade(pin, false)
					Take(x0 + dx, y0 + dy, x1 + dx, y1 + dy)
					placed = true
					break
				end
			end
			if not placed then
				Shift(pin, 0, 0)
				Fade(pin, true)
			end
		end
	end
	for i = 1, nList do pool[i][1] = nil end   -- (no pin held by the pool till the next pass)
end

-- a pass once things are still
local driver = CreateFrame("Frame")
driver:Hide()
local at = 0
local function Dirty()
	at = GetTime()
	driver:Show()
end
driver:SetScript("OnUpdate", function(self)
	if GetTime() - at < REST then return end
	self:Hide()
	local ok, err = pcall(Pass)
	if not ok then geterrorhandler()(err) end
end)
S.Declutter = Dirty

-- what moves or changes the icons: the zoom, the view, icons added or taken away, sets on or off
local function After(name, pinFn)
	local orig = S[name]
	if type(orig) ~= "function" then return end
	S[name] = function(...)
		local a, b, c, d = orig(...)
		if pinFn and a then pinFn(a) end
		Dirty()
		return a, b, c, d
	end
end
After("SetZoom")
After("Cull")
-- (a pooled one, faded or moved before: AddPin has put it back on its new place)
After("AddPin", function(pin)
	if pin.omClut then Fade(pin, false) end
	pin.omDX, pin.omDY, pin.omCell = nil, nil, pin:GetParent()
end)
do  -- (a pin moved into another cell: its new cell; MovePin returns nothing, so the pin is its 2nd argument)
	local orig = S.MovePin
	if type(orig) == "function" then
		S.MovePin = function(set, pin, ...)
			orig(set, pin, ...)
			if pin then pin.omCell = pin:GetParent() end
			Dirty()
		end
	end
end
After("RemovePin")
After("ClearPinSet")
After("SetPinSetOn")
After("SetIconScale")
if WorldMapFrame then WorldMapFrame:HookScript("OnShow", Dirty) end
