--------------------------------------------------------------------------------
-- Report a problem (beta feedback), from the map's menu: circle the
-- problem on the map (drag), say what's wrong, and get a short report code to paste
-- into a GitHub issue (addons can't send anything themselves). The code carries the
-- place, zoom, circles and note, so tools/map-preview/report.py can render exactly
-- what the player saw, circles and all.
--
-- Code: OM1|<version>|<mapID>|<u>|<v>|<zoom>|<circles u:v:r;...>|<note>
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local Look = ns.Look

local map, sc, catcher, bar
local circles = {}              -- { u, v, r } in world units (normalized)
local drawing                   -- the circle being dragged: { u, v }
local reporting = false
local RED = { 0.85, 0.15, 0.1 }

local function Redraw()
	S.ClearMarks()
	for _, c in ipairs(circles) do
		-- a ring of dabs: reads as a hand-drawn circle
		local n = 28
		for k = 1, n do
			local a = k / n * 2 * math.pi
			S.AddMark(c[1] + math.cos(a) * c[3], c[2] + math.sin(a) * c[3] * 1.5, c[3] * 0.09, RED[1], RED[2], RED[3], 0.85)
		end
	end
end


local function Code(note)
	local u, v, zoom = mod.ViewNow()
	local parts = {}
	for _, c in ipairs(circles) do parts[#parts + 1] = ("%.5f:%.5f:%.5f"):format(c[1], c[2], c[3]) end
	note = (note or ""):gsub("[|\n\r]", " ")
	return ("OM1|%s|%d|%.5f|%.5f|%.2f|%s|%s"):format(ns.version, map:GetMapID() or 0, u or 0, v or 0, zoom or 0,
		table.concat(parts, ";"), note)
end

StaticPopupDialogs.OPENMAP_REPORT_NOTE = {
	text = "What's wrong here?\n|cffaaaaaa(a sentence is plenty)|r",
	hasEditBox = true,
	editBoxWidth = 340,
	button1 = CONTINUE or "Continue",
	button2 = CANCEL,
	OnAccept = function(self)
		local box = self.editBox or self.EditBox
		mod:ShowReportCode(Code(box:GetText()))
	end,
	EditBoxOnEnterPressed = function(box)
		local dialog = box:GetParent()
		mod:ShowReportCode(Code(box:GetText()))
		dialog:Hide()
	end,
	EditBoxOnEscapePressed = function(box) box:GetParent():Hide() end,
	timeout = 0, whileDead = true, hideOnEscape = true,
}

-- the code and where to paste it, both selectable for Ctrl-C
local codeFrame
function mod:ShowReportCode(code)
	-- the last few, in case one needs copying again
	mod.char.reports = mod.char.reports or {}
	tinsert(mod.char.reports, code)
	while #mod.char.reports > 10 do tremove(mod.char.reports, 1) end
	if not codeFrame then
		codeFrame = CreateFrame("Frame", "OpenMapReport", UIParent)
		codeFrame:SetSize(520, 200)
		codeFrame:SetPoint("CENTER")
		codeFrame:SetFrameStrata("DIALOG")
		codeFrame:EnableMouse(true)
		Look:Panel(codeFrame, { inset = 0, alpha = 0.95 })
		tinsert(UISpecialFrames, "OpenMapReport")
		local close = CreateFrame("Button", nil, codeFrame, "UIPanelCloseButton")
		close:SetPoint("TOPRIGHT", 2, 2)
		local function Field(label, y)
			local fs = codeFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
			fs:SetPoint("TOPLEFT", 14, y)
			fs:SetText(label)
			local box = CreateFrame("EditBox", nil, codeFrame, "InputBoxTemplate")
			box:SetSize(480, 22)
			box:SetPoint("TOPLEFT", 20, y - 18)
			box:SetAutoFocus(false)
			box:SetScript("OnEditFocusGained", function(self) self:HighlightText() end)
			box:SetScript("OnEscapePressed", function() codeFrame:Hide() end)
			box:SetScript("OnTextChanged", function(self, user) if user then self:SetText(self.value) self:HighlightText() end end)
			return box
		end
		codeFrame.url = Field("1. Open this page (Ctrl-C, then paste in your browser):", -16)
		codeFrame.code = Field("2. Paste this code into the report, with a screenshot if you can:", -76)
		local tip = codeFrame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		tip:SetPoint("TOPLEFT", 14, -140)
		tip:SetWidth(490)
		tip:SetJustifyH("LEFT")
		tip:SetText("Thanks! The code says where you were looking and what you circled, so we can see exactly what you saw.")
	end
	codeFrame.url.value = ns.ISSUES_URL
	codeFrame.url:SetText(ns.ISSUES_URL)
	codeFrame.code.value = code
	codeFrame.code:SetText(code)
	codeFrame:Show()
	codeFrame.code:SetFocus()
	mod:ToggleReport(false)
end

--------------------------------------------------------------------------------
-- Circling on the map
--------------------------------------------------------------------------------

local function UpdateDrag()
	if not drawing then return end
	local u, v = mod.CursorWorld()
	if not u then return end
	local r = math.max(0.0005, math.sqrt((u - drawing[1]) ^ 2 + ((v - drawing[2]) / 1.5) ^ 2))
	circles[#circles] = { drawing[1], drawing[2], r }
	Redraw()
end

function mod:ToggleReport(on)
	if on == nil then on = not reporting end
	if on and not mod.IsStitched() then
		ns:Print("Open the world, a continent or a zone map to report a problem.")
		return
	end
	if on and mod.IsPainting and mod:IsPainting() then mod:TogglePaint(false) end
	reporting = on and true or false
	catcher:SetShown(reporting)
	bar:SetShown(reporting)
	S.SetMarksShown(reporting)
	if reporting then wipe(circles); Redraw() else S.ClearMarks() end
end

function mod:SetupReport(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer


	-- drags on the map draw circles; right-drag still pans, the wheel still zooms
	catcher = CreateFrame("Frame", nil, sc)
	catcher:SetAllPoints(sc)
	catcher:SetFrameLevel(math.min(sc:GetFrameLevel() + 9200, 9940))
	catcher:EnableMouse(true)
	catcher:EnableMouseWheel(true)
	catcher:Hide()
	local panning
	catcher:SetScript("OnMouseDown", function(_, b)
		if b == "LeftButton" then
			local u, v = mod.CursorWorld()
			if u then drawing = { u, v }; circles[#circles + 1] = { u, v, 0.0005 } end
		else
			panning = true
			sc:OnMouseDown("LeftButton")
		end
	end)
	catcher:SetScript("OnMouseUp", function(_, b)
		if b == "LeftButton" then
			drawing = nil
		elseif panning then
			panning = false
			sc.mouseButtonInfo.LeftButton.down = false
		end
	end)
	catcher:SetScript("OnMouseWheel", function(_, delta) mod.WheelZoom(delta) end)
	catcher:SetScript("OnUpdate", UpdateDrag)

	bar = CreateFrame("Frame", nil, map)
	bar:SetPoint("TOP", sc, "TOP", 0, -6)
	bar:SetSize(560, 34)
	bar:SetFrameLevel(math.min(sc:GetFrameLevel() + 9400, 9960))
	bar:EnableMouse(true)
	Look:Panel(bar, { inset = 0, alpha = 0.92 })
	local text = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	text:SetPoint("LEFT", 10, 0)
	text:SetText("|cffffd100Drag|r to circle the problem   |cffffd100Right-drag|r pan   |cffffd100Wheel|r zoom")
	local function Btn(label, x, fn)
		local b = CreateFrame("Button", nil, bar, "UIPanelButtonTemplate")
		b:SetSize(70, 22)
		b:SetPoint("RIGHT", x, 0)
		b:SetText(label)
		b:SetScript("OnClick", fn)
	end
	Btn("Next", -82, function() StaticPopup_Show("OPENMAP_REPORT_NOTE") end)
	Btn("Cancel", -8, function() mod:ToggleReport(false) end)
	Btn("Undo", -156, function() tremove(circles); Redraw() end)
	bar:Hide()
	map:HookScript("OnHide", function() if reporting then mod:ToggleReport(false) end end)
end
