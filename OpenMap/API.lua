--------------------------------------------------------------------------------
-- OpenMapAPI: for other addons (docs/api.md). OpenMapAPI.version goes up when something is added;
-- nothing in it is changed or taken away without a new major version (OpenMapAPI.major).
-- Read-only, plus "add your own": nothing here lets another addon change OpenMap's own settings
-- or state. Every function is safe to call before the map has opened (it returns nil then).
--
-- Positions: `u, v` are a point on OpenMap's stitched Azeroth, 0..1 across and down (the same
-- space as the in-game report codes); `x, y` a point on a uiMap, 0..1, as Blizzard's map APIs.
--
-- Callbacks (CallbackHandler-1.0: OpenMapAPI.RegisterCallback(owner, event, method)):
--   "OpenMap_StitchedChanged" (stitched)   the map switched between OpenMap's and Blizzard's own
--   "OpenMap_ViewChanged" (u, v, zoom)     the stitched view moved (a few times a second at most)
--   "OpenMap_DungeonMapShown" (info)       a dungeon's map is up: { mapID, instances = { { name,
--                                          minLevel, maxLevel, raid, bosses = { name, ... } } } }
--   "OpenMap_DungeonMapHidden" ()          and it went
--   "OpenMap_Showing" (kind)               (version 5) which of OpenMap's maps is on screen changed: "stitched",
--                                          "pad" (its controller view) or false
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

local API = { major = 1, version = 5 }
OpenMapAPI = API

local CBH = LibStub and LibStub("CallbackHandler-1.0", true)
local events = CBH and CBH:New(API, "RegisterCallback", "UnregisterCallback", "UnregisterAllCallbacks")
local function Fire(...) if events then events:Fire(...) end end

local VIEW_GAP = 0.15           -- seconds between ViewChanged callbacks (the last one always comes)

--------------------------------------------------------------------------------
-- Where things are
--------------------------------------------------------------------------------

-- whether the world map is showing OpenMap's stitched map now
function API.IsStitched() return mod.IsStitched and mod.IsStitched() or false end

-- a point on a uiMap (0..1) on the stitched world, and back; nil where the map isn't part of it
function API.WorldFromMap(uiMapID, x, y)
	if type(uiMapID) ~= "number" or type(x) ~= "number" or type(y) ~= "number" or not S.Rect(uiMapID) then return end
	return mod.ToWorld(uiMapID, x, y)
end

function API.MapFromWorld(uiMapID, u, v)
	if type(uiMapID) ~= "number" or type(u) ~= "number" or type(v) ~= "number" or not S.Rect(uiMapID) then return end
	return mod.FromWorld(uiMapID, u, v)
end

-- (version 2) a point in the game's world (a continent and yards, as UnitPosition and the taxi tables
-- give them) on the map the stitched view sits on: x, y as on WorldMapFrame's canvas (0..1 its own
-- map's rectangle, and past it: the view shows beyond it). For an addon that places frames on the
-- canvas itself, so they show over all of the stitched map, not only the map underneath
function API.CanvasFromWorldPos(continent, x, y)
	if type(continent) ~= "number" or type(x) ~= "number" or type(y) ~= "number" or not API.IsStitched() then return end
	-- (UnitPosition's can be secret on this client: nothing can be done with those)
	if ns.Safe.IsSecret(continent) or ns.Safe.IsSecret(x) or ns.Safe.IsSecret(y) then return end
	local u, v = S.FromYards(continent, x, y)
	local host = mod.HostMap and mod.HostMap()
	if not u or not host then return end
	return mod.FromWorld(host, u, v)
end

-- (version 2) the frame level the stitched art reaches on the canvas: a frame of yours at a fixed level
-- on it needs to be above this to show over the map
function API.ArtTopLevel() return S.artTop end

-- the zone (or city) at a point of the stitched world: its uiMapID
function API.MapAt(u, v)
	if type(u) ~= "number" or type(v) ~= "number" or not S.IsBuilt() then return end
	local chain = S.ChainAt(u, v)
	return chain[#chain]
end

-- the point of the stitched world under the cursor (u, v); nil when not stitched, or the cursor's off
-- the map. With MapAt: the zone under the cursor at any zoom (the map underneath follows the view,
-- so it's a zone, not the continent, once you're zoomed in: its GetMapInfoAtPosition sees no other)
function API.CursorPosition()
	if not API.IsStitched() or not mod.CursorWorld then return end
	local map = _G.WorldMapFrame
	if not (map and map:IsShown() and map.ScrollContainer and map.ScrollContainer:IsMouseOver()) then return end
	local u, v = mod.CursorWorld()
	return u, v
end

-- the stitched view: its centre (u, v) and zoom (1: the whole world fits); nil when not stitched
function API.GetView()
	if not API.IsStitched() then return end
	return mod.ViewNow()
end

-- glide the stitched map to a point (zoom optional: as it is)
function API.ShowWorld(u, v, zoom)
	if not API.IsStitched() or type(u) ~= "number" or type(v) ~= "number" then return false end
	local _, _, now = mod.ViewNow()
	mod.Glide(u, v, type(zoom) == "number" and zoom or now or 1)
	return true
end

--------------------------------------------------------------------------------
-- Adding your own
--------------------------------------------------------------------------------

local toggles = {}              -- { owner, id, label, icon, get, set, tab, section }
local sections = {}             -- owner -> fn

-- a switch of yours in OpenMap's menu: spec = { id, label, get = fn() -> bool, set = fn(bool),
-- icon = texture path or fileID (optional), tab = "show" | "look" | "more" (default "show"),
-- section = a heading (default "Other addons") }. It can be starred onto the map like OpenMap's own.
function API.RegisterMenuToggle(owner, spec)
	if type(owner) ~= "string" or type(spec) ~= "table" or type(spec.id) ~= "string" or type(spec.label) ~= "string"
		or type(spec.get) ~= "function" or type(spec.set) ~= "function" then
		error("OpenMapAPI.RegisterMenuToggle(owner, { id, label, get, set [, icon, tab, section] })", 2)
	end
	local tab = (spec.tab == "look" or spec.tab == "more") and spec.tab or "show"
	for i = #toggles, 1, -1 do if toggles[i].owner == owner and toggles[i].id == spec.id then tremove(toggles, i) end end
	toggles[#toggles + 1] = { owner = owner, id = spec.id, label = spec.label, icon = spec.icon, get = spec.get, set = spec.set,
		tab = tab, section = type(spec.section) == "string" and spec.section or nil }
	if mod.RefreshPanel then mod:RefreshPanel() end
end

-- a section of yours on a dungeon's map card: fn(info) returns a title and a list of lines (plain
-- text or colour codes; 40 at most), or nil for none. `info` is as DungeonMapShown's.
function API.RegisterDungeonSection(owner, fn)
	if type(owner) ~= "string" or (fn ~= nil and type(fn) ~= "function") then
		error("OpenMapAPI.RegisterDungeonSection(owner, fn(info) -> title, lines)", 2)
	end
	sections[owner] = fn
	if mod.RefreshDungeonCard then mod.RefreshDungeonCard() end
end

-- (version 4) townsfolk and rare mobs from your NPC database, in Questie's shape, for players without
-- Questie (with it too: yours is used): provider = { db = { NPCPointers = { [npcID] = ... }, npcFlags = {
-- VENDOR = bit, ... }, QueryNPCSingle = fn(npcID, field), QueryObjectSingle = fn(objectID, field) (for
-- mailboxes) }, zones = { GetUiMapIdByAreaId = fn(self, areaID) }, mailboxes = fn("A" | "H") -> { objectID,
-- ... } (optional) }. nil takes yours off. See docs/api.md
function API.RegisterTownsfolkProvider(owner, provider)
	if type(owner) ~= "string" or (provider ~= nil and (type(provider) ~= "table" or type(provider.db) ~= "table"
		or type(provider.zones) ~= "table" or type(provider.db.QueryNPCSingle) ~= "function"
		or type(provider.db.NPCPointers) ~= "table" or type(provider.zones.GetUiMapIdByAreaId) ~= "function")) then
		error("OpenMapAPI.RegisterTownsfolkProvider(owner, { db = { NPCPointers, npcFlags, QueryNPCSingle [, QueryObjectSingle] }, zones = { GetUiMapIdByAreaId } [, mailboxes] })", 2)
	end
	if mod.SetTownsfolkProvider then mod.SetTownsfolkProvider(provider) end
end

-- for Panel.lua: the toggles, as its checklist's rows (each tab's under its section's heading)
function mod.ExtraMenuRows(row)
	local out = {}
	for _, tab in ipairs({ "show", "look", "more" }) do
		local heads = {}
		for _, t in ipairs(toggles) do
			if t.tab == tab then
				local head = t.section or ns.L["Other addons"]
				if not heads[head] then
					heads[head] = true
					out[#out + 1] = { head, tab = tab }
				end
				local icon = t.icon and { texture = t.icon } or { texture = "Interface\\Icons\\INV_Misc_Gear_01", icon = true }
				out[#out + 1] = row(t.label, "ext." .. t.owner .. "." .. t.id, icon,
					function() local ok, v = pcall(t.get) return ok and v and true or false end,
					function(v) local ok, err = pcall(t.set, v) if not ok then geterrorhandler()(err) end end)
			end
		end
	end
	return out
end

-- for Dungeons.lua: the sections, in the order their addons' names sort
function mod.CardSections()
	local names, out = {}, {}
	for owner in pairs(sections) do names[#names + 1] = owner end
	table.sort(names)
	for _, owner in ipairs(names) do out[#out + 1] = sections[owner] end
	return out
end

--------------------------------------------------------------------------------
-- (version 5) A layer of your own: pins and lines placed in the world, on OpenMap's usual map and on its
-- controller view (PadView.lua) alike. They keep their size on screen as OpenMap's own icons do, and the
-- controller's cursor enters and leaves a pin as the mouse does (`enter`, `leave`: its tooltip; with the
-- Gamepad UI on, a tooltip frame of your own is the safe choice, as Questie keeps one there).
-- "OpenMap_Showing" (above) says when one of OpenMap's maps comes on screen: fill your layer then.
--------------------------------------------------------------------------------

-- which of OpenMap's maps is on screen now: "stitched", "pad" or false
function API.Showing()
	if mod.PadViewShown and mod.PadViewShown() then return "pad" end
	local map = _G.WorldMapFrame      -- (OpenMap's usual map stays "stitched" while it's closed: not on screen then)
	return API.IsStitched() and map ~= nil and map:IsShown() and "stitched" or false
end

local layers = {}               -- owner -> layer
local Layer = {}
Layer.__index = Layer

-- a point of a uiMap (0..1) in the world, or nil (not numbers, or a map that isn't part of the world)
local function World(uiMapID, x, y)
	if type(uiMapID) ~= "number" or type(x) ~= "number" or type(y) ~= "number" then return end
	local l, r, t, b = S.Rect(uiMapID)
	if not l then return end
	return l + x * (r - l), t + y * (b - t)
end

-- everything of yours taken off. (The pin under the controller's cursor is left first, its `leave` run:
-- the same frame may come back from the next AddPin, and is entered again then, its new `enter` run)
function Layer:Clear()
	if mod.PadViewForget then mod.PadViewForget(self.set.pins) end
	S.ClearPinSet(self.set)
end

-- shown or hidden as a whole
function Layer:SetShown(on) S.SetPinSetOn(self.set, on and true or false) end

-- a pin at a point of a uiMap: look = { atlas = or texture = (and coords =), size = (px, default 16),
-- color = { r, g, b, a } }; enter(pin), leave(pin): the mouse or the controller's cursor on and off it
-- (optional). Returns the pin (a Button of OpenMap's, yours to add textures and texts to: it's handed
-- back, with them, by a later AddPin after Clear), or nil where the map isn't part of the world.
-- The controller's A on it zooms into the zone under it, as beside it, unless you give the pin an
-- OnClick field (pin.OnClick = function(pin) ... end, taken off again by each AddPin): A runs that then
function Layer:AddPin(uiMapID, x, y, look, enter, leave)
	local u, v = World(uiMapID, x, y)
	if not u or type(look) ~= "table" then return end
	local pin = S.AddPin(self.set, u, v, look)
	pin.openmapNoPress = true     -- (PadView.lua: with no OnClick given it, A zooms in under it as beside it)
	if type(enter) == "function" then pin:SetScript("OnEnter", function(p) local ok, err = pcall(enter, p) if not ok then geterrorhandler()(err) end end) end
	if type(leave) == "function" then pin:SetScript("OnLeave", function(p) local ok, err = pcall(leave, p) if not ok then geterrorhandler()(err) end end) end
	return pin
end

-- a line between two points of a uiMap, `thickness` px on screen (default 3), coloured r, g, b, a
-- (default white); nil where the map isn't part of the world
function Layer:AddLine(uiMapID, x1, y1, x2, y2, thickness, r, g, b, a)
	local u1, v1 = World(uiMapID, x1, y1)
	local u2, v2 = World(uiMapID, x2, y2)
	if not (u1 and u2) then return end
	return S.AddLine(self.set, u1, v1, u2, v2, tonumber(thickness) or 3, tonumber(r) or 1, tonumber(g) or 1, tonumber(b) or 1, tonumber(a) or 1)
end

-- your layer, made the first time it's asked for: level 1 to 20 (default 6: over OpenMap's own icons,
-- which are at 5 at the most; the first call's: later calls hand back the same layer). nil until the
-- stitched art is built (the map opened once on one of OpenMap's maps: "OpenMap_Showing" says when)
function API.Layer(owner, level)
	if type(owner) ~= "string" then error("OpenMapAPI.Layer(owner [, level])", 2) end
	if layers[owner] then return layers[owner] end
	if not S.IsBuilt() then return end
	local set = S.PinSet("ext." .. owner, 0, math.max(1, math.min(20, math.floor(tonumber(level) or 6))))
	layers[owner] = setmetatable({ set = set }, Layer)
	return layers[owner]
end

local showingWas = false
local function ShowingChanged()
	local now = API.Showing()
	if now ~= showingWas then
		showingWas = now
		Fire("OpenMap_Showing", now)
	end
end
mod.OnPadView = function() ShowingChanged() end   -- (PadView.lua: its view shown or hidden)
-- the map opened or closed: OpenMap's usual map comes on screen and goes with it (WorldMap.lua says only
-- when the map turns stitched or back), and the controller view goes as soon as the map does
if EventUtil and EventUtil.ContinueOnAddOnLoaded then
	EventUtil.ContinueOnAddOnLoaded("Blizzard_WorldMap", function()
		local map = _G.WorldMapFrame
		if not (map and map.HookScript) then return end
		map:HookScript("OnShow", ShowingChanged)
		map:HookScript("OnHide", ShowingChanged)
	end)
end

--------------------------------------------------------------------------------
-- Telling other addons
--------------------------------------------------------------------------------

local stitchedChanged = mod.OnStitchedChanged
local wasStitched                -- (WorldMap.lua says so on every map change and resize: told only when it changes)
mod.OnStitchedChanged = function(on)
	if stitchedChanged then stitchedChanged(on) end
	on = on and true or false
	if on ~= wasStitched then
		wasStitched = on
		Fire("OpenMap_StitchedChanged", on)
	end
	ShowingChanged()
end

local viewWaiting, viewLast = false, 0
local function SendView()
	viewWaiting = false
	viewLast = GetTime()
	local u, v, zoom = API.GetView()
	if u then Fire("OpenMap_ViewChanged", u, v, zoom) end
end
mod.OnViewMoved = function()
	if viewWaiting or not events then return end
	local wait = VIEW_GAP - (GetTime() - viewLast)
	if wait <= 0 then SendView() return end
	viewWaiting = true
	C_Timer.After(wait, SendView)
end

mod.OnDungeonMap = function(info)
	if info then Fire("OpenMap_DungeonMapShown", info) else Fire("OpenMap_DungeonMapHidden") end
end
