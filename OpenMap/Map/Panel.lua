--------------------------------------------------------------------------------
-- The map's menu: one "OpenMap" button in the map's corner opens a floating panel
-- in the classic dialog style (gold border, header plate, red buttons, check
-- boxes): search, find me, drop a pin, report a problem, options, and the
-- checklist of what the map shows. Drag it by its body; it remembers where it was
-- and whether it was open.
--------------------------------------------------------------------------------

local _, ns = ...
local mod = ns:GetModule("worldmap")
local L = ns.L

-- { header } or { label, get, set }
local function Rows()
	local db = mod.db
	local function opt(key) return function() return db[key] end, function(v) db[key] = v mod:Refresh() end end
	local rows = {
		{ L["Places"] },
		{ L["Dungeons, boats, zeppelins"], opt("icons") },
		{ L["Flight masters"], opt("flight") },
		{ L["Boat and zeppelin routes"], opt("routes") },
		{ L["Party and raid members"], opt("group") },
	}
	-- Questie's quest icons: its own "Enable Map Icons" setting, switched as its options do
	local loaded = C_AddOns and C_AddOns.IsAddOnLoaded or IsAddOnLoaded
	if loaded and loaded("Questie") then
		local function profile() return _G.Questie and Questie.db and Questie.db.profile end
		rows[#rows + 1] = { L["Questie icons"],
			function() local p = profile() return p and p.enableMapIcons end,
			function(v)
				local p = profile()
				local loader = _G.QuestieLoader
				local quests = loader and loader.ImportModule and loader:ImportModule("QuestieQuest")
				if not p or not quests or not quests.ToggleNotes then return end
				p.enableMapIcons = v
				quests:ToggleNotes(v)
			end }
	end
	rows[#rows + 1] = { L["Townsfolk"] }
	for _, k in ipairs(mod.TOWNSFOLK or {}) do
		if not k.rare and k.key ~= "spirit" then
			rows[#rows + 1] = { k.name, function() return db.townsfolk[k.key] end,
				function(v) db.townsfolk[k.key] = v mod:RefreshTownsfolk() end }
		end
	end
	rows[#rows + 1] = { L["Spirit healers"], function() return db.townsfolk.spirit end,
		function(v) db.townsfolk.spirit = v mod:RefreshTownsfolk() end }
	rows[#rows + 1] = { L["Creatures"] }
	rows[#rows + 1] = { L["Rare mobs"], function() return db.townsfolk.rare end,
		function(v) db.townsfolk.rare = v mod:RefreshTownsfolk() end }
	rows[#rows + 1] = { L["Map"] }
	rows[#rows + 1] = { L["Coordinates"], opt("coords") }
	rows[#rows + 1] = { L["Zone levels"], opt("zoneLevels") }
	rows[#rows + 1] = { L["Parchment border"], opt("border") }
	rows[#rows + 1] = { L["Zone highlight on hover"], opt("hoverHighlight") }
	rows[#rows + 1] = { L["Fade while moving"], function() return (db.moveFade or 0) > 0 end,
		function(v) db.moveFade = v and 0.5 or 0 mod:Refresh() end }   -- (the amount: Options → Fade while moving)
	-- unexplored areas: dim or hide (neither ticked: shown as they are)
	for _, mode in ipairs({ { "dim", L["Dim unexplored areas"] }, { "hide", L["Hide unexplored areas"] } }) do
		rows[#rows + 1] = { mode[2], function() return db.unexplored == mode[1] end,
			function(v) db.unexplored = v and mode[1] or "show" mod:Refresh() end }
	end
	rows[#rows + 1] = { L["Follow the view"], opt("autoSwitch") }
	rows[#rows + 1] = { L["Reopen where you left off"], opt("rememberView") }
	rows[#rows + 1] = { L["Up close"] }
	rows[#rows + 1] = { L["Soften and paper grain"], opt("soften") }
	rows[#rows + 1] = { L["Minimap in the gaps"], opt("gapMinimap") }
	rows[#rows + 1] = { L["Caves underground"], opt("underground") }
	if mod.TogglePaint then
		rows[#rows + 1] = { L["Tools"] }
		rows[#rows + 1] = { L["Paint & notes"], function() return mod:IsPainting() end, function(v) mod:TogglePaint(v) end }
	end
	return rows
end

local d = mod.defaults
d.menuPos = false               -- { point, relPoint, x, y } on the map once dragged
d.menuOpen = false

local map, sc, menu, toggle, pinButton, checks
local W, PAD, COL = 420, 16, 186

local function Fill()
	local rows = Rows()
	-- two columns, split at the section boundary nearest the middle
	local split, best = #rows, math.huge
	for i, row in ipairs(rows) do
		if not row[2] and math.abs(i - #rows / 2) < best then split, best = i, math.abs(i - #rows / 2) end
	end
	checks.heads = checks.heads or {}
	checks.boxes = checks.boxes or {}
	for _, it in ipairs(checks.heads) do it:Hide() end
	for _, it in ipairs(checks.boxes) do it:Hide() end
	local nh, nb, tallest = 0, 0, 0
	for col = 1, 2 do
		local y = 0
		local from, to = col == 1 and 1 or split, col == 1 and split - 1 or #rows
		for i = from, to do
			local row = rows[i]
			if not row[2] then
				nh = nh + 1
				local it = checks.heads[nh] or checks:CreateFontString(nil, "OVERLAY", "GameFontNormal")
				checks.heads[nh] = it
				if y < 0 then y = y - 6 end
				it:ClearAllPoints()
				it:SetPoint("TOPLEFT", (col - 1) * COL + 2, y)
				it:SetText(row[1])
				it:Show()
				y = y - 18
			else
				nb = nb + 1
				local it = checks.boxes[nb]
				if not it then
					it = CreateFrame("CheckButton", nil, checks, "UICheckButtonTemplate")
					it:SetSize(24, 24)
					it.label = it:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
					it.label:SetPoint("LEFT", it, "RIGHT", 1, 1)
					it:SetScript("OnClick", function(self) self.row[3](self:GetChecked() and true or false) end)
					checks.boxes[nb] = it
				end
				it.row = row
				it:ClearAllPoints()
				it:SetPoint("TOPLEFT", (col - 1) * COL, y)
				it.label:SetText(row[1])
				it:SetChecked(row[2]() and true or false)
				it:Show()
				y = y - 20
			end
		end
		tallest = math.max(tallest, -y)
	end
	checks:SetHeight(tallest)
	menu:SetHeight(checks.top + tallest + PAD + 4)
end

local function Place()
	menu:ClearAllPoints()
	local p = mod.db.menuPos
	if p then menu:SetPoint(p[1], map, p[2], p[3], p[4])
	else menu:SetPoint("TOPLEFT", sc, "TOPLEFT", 8, -34) end
end

local function SetOpen(on)
	mod.db.menuOpen = on and true or false
	if on then Fill() Place() menu:Show() else menu:Hide() end
end

local function ClassicButton(parent, text, w, onClick, tip)
	local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
	b:SetSize(w, 22)
	b:SetText(text)
	b:SetScript("OnClick", onClick)
	if tip then
		b:SetScript("OnEnter", function(self)
			GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
			GameTooltip:AddLine(text, 1, 0.82, 0)
			GameTooltip:AddLine(tip, 1, 1, 1, true)
			GameTooltip:Show()
		end)
		b:SetScript("OnLeave", GameTooltip_Hide)
	end
	return b
end

function mod:SetupPanel(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	local level = math.min(sc:GetFrameLevel() + 9300, 9950)

	-- the corner button, beside whatever Blizzard keeps in that corner (the floor dropdown, on
	-- maps with floors): placed again whenever Blizzard refreshes its overlay buttons
	toggle = ClassicButton(map, "OpenMap", 84, function() SetOpen(not menu:IsShown()) end,
		L["Search, find me, map pins, report a problem, options, and what the map shows."])
	toggle:SetFrameLevel(level)
	local function PlaceToggle()
		local x = 6
		local left, top = sc:GetLeft(), sc:GetTop()
		for _, f in ipairs(map.overlayFrames or {}) do
			local fl, ft, fr = f:IsShown() and f:GetLeft(), f:GetTop(), f:GetRight()
			-- (a button in the corner, not a frame across the map: an addon's can span its width)
			if fl and left and ft and fr and fl - left < 40 and top - ft < 40 and fr - fl < 220 then
				x = math.max(x, fr - left + 4)
			end
		end
		local w = sc:GetWidth()
		if w and w > 0 then x = math.min(x, w - toggle:GetWidth() - 6) end     -- (never past the map's edge)
		toggle:ClearAllPoints()
		toggle:SetPoint("TOPLEFT", sc, "TOPLEFT", x, -6)
	end
	PlaceToggle()
	map:HookScript("OnShow", PlaceToggle)
	if map.RefreshOverlayFrames then hooksecurefunc(map, "RefreshOverlayFrames", PlaceToggle) end

	-- the window's portrait (Blizzard's quest log book): OpenMap's icon, while it's stitching
	local border = map.BorderFrame
	if border and border.SetPortraitToAsset then
		local function Portrait()
			border:SetPortraitToAsset(mod.IsStitched() and "Interface\\Icons\\Achievement_Zone_EasternKingdoms_01"
				or "Interface\\QuestFrame\\UI-QuestLog-BookIcon")
		end
		Portrait()
		map:HookScript("OnShow", Portrait)
		if map.Minimize then hooksecurefunc(map, "Minimize", Portrait) end
		mod.RefreshPortrait = Portrait
	end

	-- the floating menu, in the classic dialog's dress
	menu = CreateFrame("Frame", nil, map, "BackdropTemplate")
	menu:SetWidth(W)
	menu:SetFrameLevel(level + 5)
	menu:SetBackdrop({
		bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background-Dark",
		edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Gold-Border",
		tile = true, tileSize = 32, edgeSize = 32,
		insets = { left = 11, right = 12, top = 12, bottom = 11 },
	})
	menu:EnableMouse(true)
	menu:SetMovable(true)
	menu:SetClampedToScreen(true)
	menu:RegisterForDrag("LeftButton")
	menu:SetScript("OnDragStart", function(self) self:StartMoving() end)
	menu:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		self:SetUserPlaced(false)
		-- kept relative to the map, so it moves with the window
		local s = self:GetEffectiveScale() / map:GetEffectiveScale()
		mod.db.menuPos = { "TOPLEFT", "TOPLEFT", self:GetLeft() * s - map:GetLeft(), self:GetTop() * s - map:GetTop() }
		Place()
	end)
	local header = menu:CreateTexture(nil, "ARTWORK")
	header:SetTexture("Interface\\DialogFrame\\UI-DialogBox-Header")
	header:SetSize(240, 60)
	header:SetPoint("TOP", 0, 14)
	local title = menu:CreateFontString(nil, "OVERLAY", "GameFontNormal")
	title:SetPoint("TOP", header, "TOP", 0, -14)
	title:SetText("OpenMap")
	local close = CreateFrame("Button", nil, menu, "UIPanelCloseButton")
	close:SetPoint("TOPRIGHT", -4, -4)
	close:SetScript("OnClick", function() SetOpen(false) end)

	local inner = W - 2 * PAD
	local y = -30
	local search = mod.CreateSearch and mod.CreateSearch(menu, inner - 8)
	if search then
		search:SetPoint("TOPLEFT", PAD + 6, y)
		y = y - 30
	end
	local bw = (inner - 6) / 2
	local find = ClassicButton(menu, L["Find me"], bw, function() mod:FindMe() end, L["Glide to where you are."])
	find:SetPoint("TOPLEFT", PAD, y)
	pinButton = ClassicButton(menu, L["Drop a pin"], bw, function(_, b)
		if b == "RightButton" then
			mod.SetPinMode(false)
			if mod.ClearPin then mod.ClearPin() end
		else
			mod.SetPinMode(not mod.PinMode())
		end
	end, L["Click, then click the map to drop a pin (Ctrl-click the map does it any time). Right-click: remove the pin."])
	pinButton:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	pinButton:SetPoint("TOPLEFT", find, "TOPRIGHT", 6, 0)
	y = y - 26
	local report = ClassicButton(menu, L["Report a problem"], bw, function() mod:ToggleReport() end,
		L["OpenMap is in beta: circle anything that looks wrong and tell us about it."])
	report:SetPoint("TOPLEFT", PAD, y)
	local options = ClassicButton(menu, L["Options"], bw, function() if ns.OpenOptions then ns.OpenOptions() end end,
		L["All of OpenMap's settings."])
	options:SetPoint("TOPLEFT", report, "TOPRIGHT", 6, 0)
	y = y - 32
	local rule = menu:CreateTexture(nil, "ARTWORK")
	rule:SetColorTexture(0.8, 0.65, 0.3, 0.45)
	rule:SetPoint("TOPLEFT", PAD + 4, y)
	rule:SetSize(inner - 8, 1)
	y = y - 8

	checks = CreateFrame("Frame", nil, menu)
	checks:SetPoint("TOPLEFT", PAD, y)
	checks:SetWidth(inner)
	checks.top = -y

	mod.OnPinMode = function(on) pinButton:SetText(on and L["Click the map..."] or L["Drop a pin"]) end
	menu:Hide()
	map:HookScript("OnShow", function() if mod.db.menuOpen then SetOpen(true) end end)
	map:HookScript("OnHide", function() menu:Hide() mod.SetPinMode(false) end)
	if map:IsShown() and mod.db.menuOpen then SetOpen(true) end
end

-- the menu's ticks follow settings changed elsewhere
function mod:RefreshPanel()
	if menu and menu:IsShown() then Fill() end
end
