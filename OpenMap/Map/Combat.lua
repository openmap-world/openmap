--------------------------------------------------------------------------------
-- The map in combat. Blizzard's map pins set their mouse input each time one is put on the map:
-- which buttons pass through them (MapCanvasPinMixin:CheckMouseButtonPassthrough: right-clicks go to
-- the map, to zoom out) and, for a pin you can super-track, whether its clicks go on to the map
-- (SuperTrackablePinMixin:UpdateMousePropagation). On this engine those setters (SetPassThroughButtons,
-- SetPropagateMouseClicks) are blocked in combat once the map's own code has met an addon's, and the
-- stitched map's zoom is OpenMap's (its zoom levels in Blizzard's scroll container): every map refresh
-- in combat (opening it, the quest log updating) was an "action blocked" error. So in combat each
-- pin's last request waits, and is applied as soon as combat ends; until then a right-click on a pin
-- placed in combat doesn't zoom the map out. (With thanks to Ironship, PR #22.)
--
-- CreateFromMixins copies methods, so every mixin made from Blizzard's, and every pin already made
-- from one, is pointed at ours; pins made after that inherit it as they're made. Mixins of addons
-- loaded later are pointed once after they load (one sweep a frame, not one an addon), and a new pool
-- of pins as the canvas first redraws with it (never every pin on every acquire: that's N squared).
-- The sweep (every global: some 20 ms) isn't at login but a few seconds into the world (a player:
-- OpenMap added to the load time, and this was most of its login), or as the map opens if that's
-- sooner; the pins made meanwhile are pointed with their pools as it opens.
--------------------------------------------------------------------------------

local _, ns = ...
local mod = ns:GetModule("worldmap")

local map
local original                  -- Blizzard's CheckMouseButtonPassthrough
local originalPropagation       -- ... and UpdateMousePropagation
local waiting = setmetatable({}, { __mode = "k" })   -- pin -> { passthrough = { n, ... }, propagation = { n, ... } }
local seen = setmetatable({}, { __mode = "k" })      -- pin pools already pointed
local sweepSoon = false
local swept = false             -- the globals swept since the last addon loaded (Sweep)
local owner = {}

local function Wait(pin, key, ...)
	local w = waiting[pin] or {}
	waiting[pin] = w
	w[key] = { n = select("#", ...), ... }
end

local function Done(pin, key)
	local w = waiting[pin]
	if not w then return end
	w[key] = nil
	if not w.passthrough and not w.propagation then waiting[pin] = nil end
end

local function Deferred(pin, ...)
	if InCombatLockdown() then return Wait(pin, "passthrough", ...) end
	Done(pin, "passthrough")
	return original(pin, ...)
end

local function DeferredPropagation(pin, ...)
	if InCombatLockdown() then return Wait(pin, "propagation", ...) end
	Done(pin, "propagation")
	return originalPropagation(pin, ...)
end

local function Point(t)
	if type(t) ~= "table" then return end
	local ok, method = pcall(rawget, t, "CheckMouseButtonPassthrough")   -- (a forbidden table: left alone)
	if ok and method == original then t.CheckMouseButtonPassthrough = Deferred end
	if originalPropagation then
		ok, method = pcall(rawget, t, "UpdateMousePropagation")
		if ok and method == originalPropagation then t.UpdateMousePropagation = DeferredPropagation end
	end
end

local function PointPool(pool)
	for _, enumerate in ipairs({ "EnumerateActive", "EnumerateInactive" }) do
		if type(pool[enumerate]) == "function" then
			local ok, iter, state, start = pcall(pool[enumerate], pool)
			if ok and iter then
				for pin in iter, state, start do Point(pin) end
			end
		end
	end
end

local function PointPins()
	for _, pool in pairs(map.pinPools or {}) do PointPool(pool) end
end

-- (pools not met before: the first pin of a new pool, as the canvas redraws with it)
local function ScanPools()
	for _, pool in pairs(map.pinPools or {}) do
		if not seen[pool] then
			seen[pool] = true
			PointPool(pool)
		end
	end
end

local function Sweep()
	sweepSoon = false
	swept = true
	for _, value in pairs(_G) do Point(value) end
	PointPins()
end

-- (addons loading one after another: one sweep, on the next frame with the map open, else a moment later)
local function SweepSoon(wait)
	swept = false
	if sweepSoon then return end
	sweepSoon = true
	C_Timer.After(map and map:IsShown() and 0 or wait or 2, function() sweepSoon = false if not swept then Sweep() end end)
end

local function Shown()
	if swept then PointPins() else Sweep() end
end

local function Flush()
	if InCombatLockdown() then return end
	for pin, w in pairs(waiting) do
		waiting[pin] = nil
		-- (a pin let go meanwhile has no map: its old setup isn't wanted)
		if pin.IsForbidden and not pin:IsForbidden() and (not pin.GetMap or pin:GetMap()) then
			if w.passthrough then pcall(original, pin, unpack(w.passthrough, 1, w.passthrough.n)) end
			if w.propagation then pcall(originalPropagation, pin, unpack(w.propagation, 1, w.propagation.n)) end
		end
	end
end

function mod:SetupCombat(worldMap)
	if map then return end
	original = MapCanvasPinMixin and MapCanvasPinMixin.CheckMouseButtonPassthrough
	if type(original) ~= "function" then return end
	local propagation = SuperTrackablePinMixin and SuperTrackablePinMixin.UpdateMousePropagation
	originalPropagation = type(propagation) == "function" and propagation or nil
	map = worldMap
	SweepSoon(5)
	ScanPools()
	map:HookScript("OnShow", Shown)
	local sc = map.ScrollContainer
	if sc and sc.MarkCanvasDirty then hooksecurefunc(sc, "MarkCanvasDirty", ScanPools) end
	ns.RegisterEvent(owner, "ADDON_LOADED", function() SweepSoon() end)
	ns.RegisterEvent(owner, "PLAYER_REGEN_ENABLED", Flush)
end
