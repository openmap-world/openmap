--------------------------------------------------------------------------------
-- Init: loaded last. Settings at ADDON_LOADED; the map, options and slash
-- commands at PLAYER_LOGIN.
--
--   /openmap (/omap)        options
--   /openmap status         what the map is doing
--   /openmap paint          paint & notes (marking up the map for contributors)
--------------------------------------------------------------------------------

local ADDON, ns = ...

local function Options()
	local mod = ns:GetModule("worldmap")
	local args = mod.Options and mod:Options() or {}
	args.enabled = { type = "toggle", name = "Enable OpenMap", order = 0, width = "full",
		desc = "Turning OpenMap off takes a reload.",
		get = function() return mod.db.enabled end,
		set = function(_, v) mod.db.enabled = v; ns:Print("Takes effect after a /reload.") end }
	return { type = "group", name = "|cff" .. ns.ACCENT .. "OpenMap|r " .. ns.version, args = args }
end

local function OpenOptions()
	local ACD = LibStub("AceConfigDialog-3.0", true)
	if ACD then ACD:Open("OpenMap") end
end
ns.OpenOptions = OpenOptions

local function Slash(msg)
	msg = (msg or ""):lower():match("^%s*(.-)%s*$")
	local mod = ns:GetModule("worldmap")
	local run = {
		status = "Diag", paint = "TogglePaint",
	}
	if run[msg] then
		if mod.enabled and mod[run[msg]] then mod[run[msg]](mod) else ns:Print("The map is off.") end
	else
		OpenOptions()
	end
end

local boot = CreateFrame("Frame")
boot:RegisterEvent("ADDON_LOADED")
boot:RegisterEvent("PLAYER_LOGIN")
boot:SetScript("OnEvent", function(self, event, name)
	if event == "ADDON_LOADED" and name == ADDON then
		ns:InitDB()
		self:UnregisterEvent("ADDON_LOADED")
	elseif event == "PLAYER_LOGIN" then
		ns:EnableModules()
		local AC = LibStub("AceConfig-3.0", true)
		if AC then AC:RegisterOptionsTable("OpenMap", Options) end
		-- a page in Blizzard's settings that opens the options window
		if Settings and Settings.RegisterCanvasLayoutCategory then
			local panel = CreateFrame("Frame")
			local title = panel:CreateFontString(nil, "ARTWORK", "GameFontNormalHuge")
			title:SetPoint("TOPLEFT", 16, -16)
			title:SetText("|cff" .. ns.ACCENT .. "Open|rMap")
			local button = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
			button:SetSize(180, 26)
			button:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -12)
			button:SetText("Open OpenMap options")
			button:SetScript("OnClick", function()
				if SettingsPanel then HideUIPanel(SettingsPanel) end
				OpenOptions()
			end)
			Settings.RegisterAddOnCategory(Settings.RegisterCanvasLayoutCategory(panel, "OpenMap"))
		end
		SLASH_OPENMAP1, SLASH_OPENMAP2 = "/openmap", "/omap"
		SlashCmdList.OPENMAP = Slash
		self:UnregisterEvent("PLAYER_LOGIN")
	end
end)

function ns.NotifyOptions()
	local ACR = LibStub("AceConfigRegistry-3.0", true)
	if ACR then ACR:NotifyChange("OpenMap") end
end
