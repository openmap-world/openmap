--------------------------------------------------------------------------------
-- Map paint & notes, for contributors: soft-brush mark-up on the stitched map
-- (what to change where, per layer) and pinned notes, saved in OpenMapDB
-- (worldmap -> paint), to attach to an issue or pull request. Players reporting
-- a problem use the Report button instead (Report.lua).
--
--   left-drag  paint (or drop a note, with the note tool)
--   right-drag pan        wheel  zoom        Ctrl-Z  undo the last stroke
--
-- A stroke: { mode, layer, zone, radius, strength, r, g, b, points = { u, v, ... } }
-- (u, v: Azeroth's map, normalized; radius in the same units, horizontally)
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local Look = ns.Look

mod.defaults.paint = { strokes = {}, notes = {} }

local MODES = {
	{ key = "hide", name = "Hide layer", color = { 1, 0.25, 0.2 } },
	{ key = "show", name = "Show layer", color = { 0.3, 1, 0.35 } },
	{ key = "blend", name = "Blend seam", color = { 0.35, 0.6, 1 } },
	{ key = "tint", name = "Tint", color = nil },   -- the chosen colour
	{ key = "note", name = "Note", color = { 1, 0.85, 0.3 } },
}
local LAYERS = { "auto", "overlays", "base", "cities", "continent", "world", "sea" }
local LAYER_NAMES = { auto = "Zone art (under the stroke)", overlays = "Zone overlays", base = "Zone base art",
	cities = "City art", continent = "Continent art", world = "World art", sea = "Sea" }

local tool = { mode = 1, layer = 1, size = 40, strength = 0.7, tint = { 0.55, 0.42, 0.25 } }
local painting = false
local map, sc, catcher, bar, notesSet
local stroke                    -- the stroke being drawn
local panning

local function DB() return mod.db.paint end

local function ModeColor(st)
	if st.mode == "tint" then return st.r or 1, st.g or 1, st.b or 1 end
	for _, m in ipairs(MODES) do
		if m.key == st.mode and m.color then return unpack(m.color) end
	end
	return 1, 1, 1
end

--------------------------------------------------------------------------------
-- Drawing the saved mark-up
--------------------------------------------------------------------------------

local function DrawStroke(st)
	local r, g, b = ModeColor(st)
	local p = st.points
	for i = 1, #p, 2 do
		S.AddMark(p[i], p[i + 1], st.radius, r, g, b, 0.18 + 0.25 * (st.strength or 1))
	end
end

local function NoteEnter(pin)
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	GameTooltip:AddLine("Note", 1, 0.82, 0)
	GameTooltip:AddLine(pin.note.text, 1, 1, 1, true)
	GameTooltip:AddLine("Click: edit or delete", 0.6, 0.6, 0.6)
	GameTooltip:Show()
end

local EditNote

local function Redraw()
	if not S.IsBuilt() then return end
	S.ClearMarks()
	for _, st in ipairs(DB().strokes) do DrawStroke(st) end
	if notesSet then
		S.ClearPinSet(notesSet)
		for _, note in ipairs(DB().notes) do
			local pin = S.AddPin(notesSet, note.u, note.v, { texture = "Interface\\Buttons\\UI-GuildButton-PublicNote-Up", size = 18 })
			pin.note = note
			-- the text beside it: the paint layer sits over the icons, so no hovering while painting
			if not pin.caption then         -- pins are pooled: the caption is made once
				pin.caption = pin:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
				pin.caption:SetPoint("LEFT", pin, "RIGHT", 2, 0)
				pin.caption:SetWidth(180)
				pin.caption:SetJustifyH("LEFT")
				Look:Font(pin.caption, 11, "OUTLINE")
			end
			pin.caption:SetText(#note.text > 80 and (note.text:sub(1, 78) .. "...") or note.text)
			pin:SetScript("OnEnter", NoteEnter)
			pin:SetScript("OnLeave", GameTooltip_Hide)
			pin.OnClick = function(self) EditNote(self.note) end
		end
	end
end

--------------------------------------------------------------------------------
-- Notes
--------------------------------------------------------------------------------

local function ZoneAt(u, v)
	local chain = S.ChainAt(u, v)
	return chain[#chain]
end

StaticPopupDialogs.OPENMAP_MAP_NOTE = {
	text = "Map note",
	hasEditBox = true,
	editBoxWidth = 320,
	button1 = SAVE or "Save",
	button2 = CANCEL,
	button3 = DELETE or "Delete",
	OnShow = function(self, note)
		local box = self.editBox or self.EditBox
		box:SetText(note and note.text or "")
		box:HighlightText()
	end,
	OnAccept = function(self, note)
		local box = self.editBox or self.EditBox
		local text = strtrim(box:GetText() or "")
		if text == "" then return end
		note.text = text
		if not note.saved then
			note.saved = true
			tinsert(DB().notes, note)
		end
		Redraw()
	end,
	OnAlt = function(_, note)
		for i, n in ipairs(DB().notes) do
			if n == note then tremove(DB().notes, i) break end
		end
		Redraw()
	end,
	EditBoxOnEnterPressed = function(box)
		local dialog = box:GetParent()
		StaticPopupDialogs.OPENMAP_MAP_NOTE.OnAccept(dialog, dialog.data)
		dialog:Hide()
	end,
	EditBoxOnEscapePressed = function(box) box:GetParent():Hide() end,
	timeout = 0,
	whileDead = true,
	hideOnEscape = true,
}

function EditNote(note)
	StaticPopup_Show("OPENMAP_MAP_NOTE", nil, nil, note)
end

--------------------------------------------------------------------------------
-- Brush input
--------------------------------------------------------------------------------

local function Mode() return MODES[tool.mode] end

local function AddPoint(u, v)
	local p = stroke.points
	p[#p + 1] = math.floor(u * 1e5 + 0.5) / 1e5
	p[#p + 1] = math.floor(v * 1e5 + 0.5) / 1e5
	local r, g, b = ModeColor(stroke)
	S.AddMark(u, v, stroke.radius, r, g, b, 0.18 + 0.25 * stroke.strength)
end

local function StrokeUpdate()
	if not stroke then return end
	local u, v, pu = mod.CursorWorld()
	if not u then return end
	local p = stroke.points
	local lu, lv = p[#p - 1], p[#p]
	-- a dab every quarter brush width
	if math.sqrt((u - lu) ^ 2 + (v - lv) ^ 2) >= stroke.radius * 0.25 then AddPoint(u, v) end
end

local function StartStroke()
	local u, v, pu = mod.CursorWorld()
	if not u then return end
	local m = Mode()
	if m.key == "note" then
		-- near an existing note: edit it
		for _, note in ipairs(DB().notes) do
			if math.sqrt((note.u - u) ^ 2 + (note.v - v) ^ 2) / pu < 14 then EditNote(note) return end
		end
		EditNote({ u = math.floor(u * 1e5 + 0.5) / 1e5, v = math.floor(v * 1e5 + 0.5) / 1e5, zone = ZoneAt(u, v), text = "" })
		return
	end
	local layer = LAYERS[tool.layer]
	stroke = { mode = m.key, layer = layer, zone = ZoneAt(u, v), radius = (tool.size / 2) * pu,
		strength = tool.strength, points = {} }
	if m.key == "tint" then stroke.r, stroke.g, stroke.b = unpack(tool.tint) end
	AddPoint(u, v)
end

local function EndStroke()
	if not stroke then return end
	stroke.radius = math.floor(stroke.radius * 1e6 + 0.5) / 1e6
	tinsert(DB().strokes, stroke)
	stroke = nil
end

local function Undo()
	if #DB().strokes > 0 then
		tremove(DB().strokes)
		Redraw()
	end
end

--------------------------------------------------------------------------------
-- The toolbar
--------------------------------------------------------------------------------

local function UpdateBar()
	if not bar then return end
	local m = Mode()
	bar.mode:SetText(m.name)
	bar.layer:SetText(LAYER_NAMES[LAYERS[tool.layer]])
	bar.layer:SetEnabled(m.key ~= "note")
	bar.size:SetText(("Size %d"):format(tool.size))
	bar.strength:SetText(("Strength %d%%"):format(tool.strength * 100))
	bar.swatch:SetColorTexture(unpack(tool.tint))
	bar.swatchButton:SetShown(m.key == "tint")
	bar.count:SetText(("%d strokes, %d notes"):format(#DB().strokes, #DB().notes))
end

local function Button(parent, width, text, onClick, tip)
	local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
	b:SetSize(width, 20)
	b:SetText(text)
	b:SetScript("OnClick", function(self, button) onClick(self, button) UpdateBar() end)
	b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	if tip then
		b:SetScript("OnEnter", function(self)
			GameTooltip:SetOwner(self, "ANCHOR_TOP")
			GameTooltip:AddLine(tip, 1, 1, 1, true)
			GameTooltip:Show()
		end)
		b:SetScript("OnLeave", GameTooltip_Hide)
	end
	return b
end

local function Step(value, delta, lo, hi) return math.max(lo, math.min(hi, value + delta)) end

local function CreateBar()
	bar = CreateFrame("Frame", nil, map)
	bar:SetPoint("TOP", sc, "TOP", 0, -6)
	bar:SetSize(760, 52)
	bar:SetFrameLevel(math.min(sc:GetFrameLevel() + 9400, 9960))
	bar:EnableMouse(true)
	Look:Panel(bar, { inset = 0, alpha = 0.92 })

	local cycle = function(list, key) return function(_, button)
		tool[key] = (tool[key] + (button == "RightButton" and -2 or 0)) % #list + 1
	end end
	bar.mode = Button(bar, 110, "", cycle(MODES, "mode"), "What the brush does (right-click: back)")
	bar.mode:SetPoint("TOPLEFT", 8, -6)
	bar.layer = Button(bar, 190, "", cycle(LAYERS, "layer"), "Which layer it's about (right-click: back)")
	bar.layer:SetPoint("LEFT", bar.mode, "RIGHT", 4, 0)
	bar.size = Button(bar, 80, "", function(_, button) tool.size = Step(tool.size, button == "RightButton" and -10 or 10, 10, 300) end,
		"Brush size on screen (click: bigger, right-click: smaller)")
	bar.size:SetPoint("LEFT", bar.layer, "RIGHT", 4, 0)
	bar.strength = Button(bar, 110, "", function(_, button) tool.strength = Step(tool.strength, button == "RightButton" and -0.1 or 0.1, 0.1, 1) end,
		"How strong (click: more, right-click: less)")
	bar.strength:SetPoint("LEFT", bar.size, "RIGHT", 4, 0)
	bar.swatchButton = CreateFrame("Button", nil, bar)
	bar.swatchButton:SetSize(20, 20)
	bar.swatchButton:SetPoint("LEFT", bar.strength, "RIGHT", 6, 0)
	bar.swatch = bar.swatchButton:CreateTexture(nil, "ARTWORK")
	bar.swatch:SetAllPoints()
	bar.swatchButton:SetScript("OnClick", function()
		local r, g, b = unpack(tool.tint)
		local function Apply()
			tool.tint = { ColorPickerFrame:GetColorRGB() }
			UpdateBar()
		end
		if ColorPickerFrame.SetupColorPickerAndShow then
			ColorPickerFrame:SetupColorPickerAndShow({ r = r, g = g, b = b, swatchFunc = Apply,
				cancelFunc = function() tool.tint = { r, g, b } UpdateBar() end })
		else
			ColorPickerFrame.func, ColorPickerFrame.cancelFunc = Apply, function() tool.tint = { r, g, b } UpdateBar() end
			ColorPickerFrame:SetColorRGB(r, g, b)
			ColorPickerFrame:Show()
		end
	end)
	local undo = Button(bar, 60, "Undo", Undo, "Remove the last stroke (Ctrl-Z)")
	undo:SetPoint("LEFT", bar.swatchButton, "RIGHT", 8, 0)
	local clear = Button(bar, 60, "Clear", function(self)
		if self.armed then
			wipe(DB().strokes)
			wipe(DB().notes)
			Redraw()
			self.armed = nil
			self:SetText("Clear")
		else
			self.armed = true
			self:SetText("Sure?")
			C_Timer.After(3, function() self.armed = nil self:SetText("Clear") end)
		end
	end, "Remove every stroke and note (click twice)")
	clear:SetPoint("LEFT", undo, "RIGHT", 4, 0)
	local done = Button(bar, 60, "Done", function() mod:TogglePaint(false) end)
	done:SetPoint("LEFT", clear, "RIGHT", 4, 0)

	local help = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	help:SetPoint("BOTTOMLEFT", 10, 6)
	Look:Font(help, 11)
	help:SetText("|cffffd100Left-drag|r paint   |cffffd100Right-drag|r pan   |cffffd100Wheel|r zoom   |cffffd100Ctrl-Z|r undo   Saved with your settings (|cffffd100/reload|r writes them out).")
	bar.count = bar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
	bar.count:SetPoint("BOTTOMRIGHT", -10, 6)
	Look:Font(bar.count, 11)
	bar:Hide()
end

local function CreateCatcher()
	catcher = CreateFrame("Frame", nil, sc)
	catcher:SetAllPoints(sc)
	catcher:SetFrameLevel(math.min(sc:GetFrameLevel() + 9200, 9940))
	catcher:EnableMouse(true)
	catcher:EnableMouseWheel(true)
	catcher:Hide()
	catcher:SetScript("OnMouseDown", function(_, button)
		if button == "LeftButton" then
			StartStroke()
		elseif button == "RightButton" then
			panning = true
			sc:OnMouseDown("LeftButton")   -- Blizzard's own drag-to-pan
		end
	end)
	catcher:SetScript("OnMouseUp", function(_, button)
		if button == "LeftButton" then
			EndStroke()
			UpdateBar()
		elseif panning then
			panning = false
			sc.mouseButtonInfo.LeftButton.down = false
		end
	end)
	catcher:SetScript("OnMouseWheel", function(_, delta) mod.WheelZoom(delta) end)
	catcher:SetScript("OnUpdate", StrokeUpdate)
	catcher:EnableKeyboard(true)
	catcher:SetPropagateKeyboardInput(true)
	catcher:SetScript("OnKeyDown", function(self, key)
		if key == "Z" and IsControlKeyDown() and not InCombatLockdown() then
			self:SetPropagateKeyboardInput(false)
			Undo()
			UpdateBar()
			C_Timer.After(0, function() if not InCombatLockdown() then self:SetPropagateKeyboardInput(true) end end)
		end
	end)
end

--------------------------------------------------------------------------------

function mod:IsPainting() return painting end

function mod:TogglePaint(on)
	if on == nil then on = not painting end
	if not map or not S.IsBuilt() then
		ns:Print("Open the world map first.")
		return
	end
	if on and not mod.IsStitched() then
		ns:Print("Paint works on the world, continent and zone maps.")
		return
	end
	if on and mod.ToggleReport then mod:ToggleReport(false) end
	painting = on and true or false
	catcher:SetShown(painting)
	bar:SetShown(painting)
	S.SetMarksShown(painting)
	if notesSet then S.SetPinSetOn(notesSet, painting) end
	if painting then Redraw() UpdateBar() else EndStroke() end
	if mod.RefreshPanel then mod:RefreshPanel() end
end

function mod:BuildPaint()
	if not S.IsBuilt() then return end
	notesSet = S.PinSet("notes", 1, 5)
	S.SetPinSetOn(notesSet, painting)
	if painting then Redraw() end
end

function mod:SetupPaint(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	CreateCatcher()
	CreateBar()
	map:HookScript("OnHide", function() if painting then mod:TogglePaint(false) end end)
end
