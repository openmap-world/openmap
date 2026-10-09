--------------------------------------------------------------------------------
-- OpenMap's core: saved settings, events, chat output, options plumbing and
-- the few look helpers the map uses. Loaded first; the map files (Map/*.lua)
-- add a module with ns:NewModule and Init.lua starts it at login.
--
-- Settings: OpenMapDB (account), OpenMapCharDB (per character), filled from
-- the module's defaults (missing keys only, so new defaults reach old saves).
--------------------------------------------------------------------------------

local ADDON, ns = ...
_G.OpenMap = ns

ns.name = ADDON
ns.version = (C_AddOns and C_AddOns.GetAddOnMetadata or GetAddOnMetadata)(ADDON, "Version") or "dev"
if ns.version:find("^@") then ns.version = "dev" end   -- (a checkout: the packager fills it in for releases)
ns.ACCENT = "e6b85c"
-- where players send reports (the "Report a problem" button shows it to copy)
ns.ISSUES_URL = "https://github.com/openmap-world/openmap/issues/new?template=map-problem.yml"
ns.Media = { path = "Interface\\AddOns\\" .. ADDON .. "\\Media\\" }

-- Translations: ns.L["English text"] gives the text for the player's language once a
-- translation fills it in (none yet), else the English. Place names come from the game.
ns.L = setmetatable({}, { __index = function(_, k) return k end })

function ns:Print(fmt, ...)
	local msg = select("#", ...) > 0 and fmt:format(...) or tostring(fmt)
	DEFAULT_CHAT_FRAME:AddMessage("|cff" .. ns.ACCENT .. "OpenMap|r: " .. msg)
end

--------------------------------------------------------------------------------
-- Secret-safe reads (clients with secret values, e.g. WoW Forever)
--------------------------------------------------------------------------------

local Safe = {}
ns.Safe = Safe

function Safe.IsSecret(v)
	return issecretvalue ~= nil and issecretvalue(v) or false
end

function Safe.Value(v)
	if issecretvalue and issecretvalue(v) then return nil end
	return v
end

-- a position's x, y: Blizzard's vectors have GetXY, but some APIs on this client hand back
-- a plain { x, y } table
function Safe.XY(vec)
	if type(vec) ~= "table" then return end
	if vec.GetXY then return vec:GetXY() end
	return vec.x, vec.y
end

-- calls fn(...) and returns its first result when it is plain, else nil
function Safe.Call(fn, ...)
	if type(fn) ~= "function" then return nil end
	local ok, v = pcall(fn, ...)
	if not ok then return nil end
	return Safe.Value(v)
end

--------------------------------------------------------------------------------
-- Events: any number of handlers per event, keyed by owner
--------------------------------------------------------------------------------

local eventFrame = CreateFrame("Frame")
local handlers = {}
eventFrame:SetScript("OnEvent", function(_, event, ...)
	for owner, fn in pairs(handlers[event] or {}) do
		local ok, err = pcall(fn, owner, event, ...)
		if not ok then geterrorhandler()(err) end
	end
end)

function ns.RegisterEvent(owner, event, fn)
	if not handlers[event] then
		if not pcall(eventFrame.RegisterEvent, eventFrame, event) then return false end
		handlers[event] = {}
	end
	handlers[event][owner] = fn or owner[event]
	return true
end

function ns.UnregisterEvent(owner, event)
	local list = handlers[event]
	if not list then return end
	list[owner] = nil
	if next(list) == nil then
		handlers[event] = nil
		eventFrame:UnregisterEvent(event)
	end
end

--------------------------------------------------------------------------------
-- Modules (OpenMap has one, "worldmap")
--------------------------------------------------------------------------------

ns.modules = {}

function ns:NewModule(key, spec)
	local mod = spec or {}
	mod.key = key
	mod.defaults = mod.defaults or {}
	if mod.defaults.enabled == nil then mod.defaults.enabled = true end
	ns.modules[key] = mod
	return mod
end

function ns:GetModule(key)
	return ns.modules[key]
end

-- missing keys from defaults, recursively
local function Fill(t, defaults)
	for k, v in pairs(defaults) do
		if t[k] == nil then
			t[k] = type(v) == "table" and Fill({}, v) or v
		elseif type(v) == "table" and type(t[k]) == "table" then
			Fill(t[k], v)
		end
	end
	return t
end

function ns:InitDB()
	OpenMapDB = OpenMapDB or {}
	OpenMapCharDB = OpenMapCharDB or {}
	for key, mod in pairs(ns.modules) do
		OpenMapDB[key] = Fill(OpenMapDB[key] or {}, mod.defaults)
		OpenMapCharDB[key] = OpenMapCharDB[key] or {}
		mod.db, mod.char = OpenMapDB[key], OpenMapCharDB[key]
	end
end

function ns:EnableModules()
	for _, mod in pairs(ns.modules) do
		if mod.db.enabled and not mod.enabled then
			mod.enabled = true
			if mod.OnEnable then
				local ok, err = pcall(mod.OnEnable, mod)
				if not ok then
					mod.enabled = false
					ns:Print("|cffff6060failed to start|r: %s", tostring(err):sub(1, 300))
					geterrorhandler()(err)
				end
			end
		end
	end
end

--------------------------------------------------------------------------------
-- Options (AceConfig tables)
--------------------------------------------------------------------------------

-- get / set for options stored in getTable(info)[key]; refresh() after a change
function ns.Bind(getTable, refresh)
	local function get(info)
		local v = getTable(info)[info[#info]]
		if info.type == "color" then
			v = v or { 1, 1, 1, 1 }
			return v[1], v[2], v[3], v[4] or 1
		end
		return v
	end
	local function set(info, a, b, c, d)
		local t = getTable(info)
		if info.type == "color" then
			t[info[#info]] = { a, b, c, d or 1 }
		else
			t[info[#info]] = a
		end
		if refresh then refresh(info) end
	end
	return get, set
end

function ns.Header(name, order)
	return { type = "header", name = name, order = order }
end

function ns.Desc(text, order)
	return { type = "description", name = text, order = order, fontSize = "medium" }
end

--------------------------------------------------------------------------------
-- Look: fonts and a plain dark panel (other addons may restyle these: every
-- panel is frame.omBackdrop, every font goes through ns.Look:Font)
--------------------------------------------------------------------------------

local Look = {}
ns.Look = Look

function Look:Font(fs, size, flags)
	if not fs:SetFont(STANDARD_TEXT_FONT, size or 12, flags or "") then
		fs:SetFontObject(GameFontHighlight)
	end
	fs:SetShadowColor(0, 0, 0, 1)
	fs:SetShadowOffset(1, -1)
	return fs
end

-- a dark backdrop with a thin border behind `frame`; opts: inset, alpha
function Look:Panel(frame, opts)
	opts = opts or {}
	local bd = frame.omBackdrop
	if not bd then
		bd = CreateFrame("Frame", nil, frame, "BackdropTemplate")
		bd:SetFrameLevel(math.max(0, frame:GetFrameLevel() - 1))
		frame.omBackdrop = bd
	end
	local inset = opts.inset or 0
	bd:ClearAllPoints()
	bd:SetPoint("TOPLEFT", -inset, inset)
	bd:SetPoint("BOTTOMRIGHT", inset, -inset)
	bd:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
	bd:SetBackdropColor(0.06, 0.06, 0.07, opts.alpha or 0.9)
	bd:SetBackdropBorderColor(0, 0, 0, 1)
	return bd
end
