--------------------------------------------------------------------------------
-- Dungeon Journal (by Exehn, for WoW Forever): open its dungeon pages and let its
-- world map overlay use a wing OpenMap has identified.
--------------------------------------------------------------------------------

local _, ns = ...
local mod = ns:GetModule("worldmap")
local Safe = ns.Safe

local function Journal()
	local dj = _G.ForeverDungeonJournal_NS
	if type(dj) == "table" and type(dj.DB) == "table" and type(dj.OpenBossPage) == "function" then return dj end
end

function mod.HasDungeonJournal() return Journal() ~= nil end

-- Journal's page names can use different punctuation ("Scarlet Monastery: Graveyard").
function mod.DungeonJournalPage(inst, dj)
	dj = dj or Journal()
	if not dj then return end
	-- (its own name, then the others it goes by in the Journal: "Stormwind Stockade", "The Stockade", #289)
	local wants = { mod.DungeonNameKey(inst[2]) }
	for _, alt in ipairs(mod.DungeonNameAliases and mod.DungeonNameAliases[inst[2]] or {}) do wants[#wants + 1] = mod.DungeonNameKey(alt) end
	for _, want in ipairs(wants) do
		for key, entry in pairs(dj.DB) do
			if type(entry) == "table" and not entry.previewOnly and mod.DungeonNameKey(key) == want then return key end
		end
	end
end

function mod.OpenDungeonJournal(inst, quests)
	local dj = Journal()
	if not dj then return false end
	local key = mod.DungeonJournalPage(inst, dj)
	if not key then return false end
	-- Showing the window puts up the page it was last on.
	local frame, toggle = _G.ForeverDungeonJournalFrame, _G.ForeverDungeonJournal_Toggle
	if not (frame and frame:IsShown()) and type(toggle) == "function" then pcall(toggle) end
	local open = quests and type(dj.OpenQuestPage) == "function" and dj.OpenQuestPage or dj.OpenBossPage
	return (pcall(open, key))
end

local journalHint, journalLookup
local journalRefreshDue, journalRefreshOwner = false, {}   -- (a refresh waiting out a fight)

-- A wing saved from an earlier visit only fills in a missing answer from Journal.
local function WingResult(key, confirmed, native, ...)
	if not Safe.IsSecret(native) and (native == nil or (native ~= key and confirmed)) then return key end
	return native, ...
end

local function OfferWing(dj, key, record)
	local current, refresh = dj.CurrentDungeon, dj.RefreshWorldMapOverlay
	if type(current) ~= "function" or type(refresh) ~= "function" then return end
	local installLookup = current ~= journalLookup
	local active, confirmed = mod.ActiveDungeonWing()
	confirmed = active == record and confirmed
	local hint = journalHint
	if not installLookup and hint and hint.journal == dj and hint.key == key and hint.record == record
		and hint.confirmed == confirmed then return end
	journalHint = { journal = dj, key = key, record = record, confirmed = confirmed }
	if installLookup then
		-- Journal consults this lookup again when its World Map/Dungeon Map button is clicked.
		journalLookup = function(...)
			local selected = journalHint
			if selected and selected.journal == dj then
				local wing, fresh = mod.ActiveDungeonWing()
				if wing == selected.record then return WingResult(selected.key, fresh, current(...)) end
			end
			return current(...)
		end
		dj.CurrentDungeon = journalLookup
	end
	-- Journal applies its own map setting, RPG lock and World Map choice to this wing. (Not from OpenMap's code
	-- in a fight: its refresh works on Blizzard's map, which OpenMap leaves alone then; done as combat ends)
	if InCombatLockdown() then
		if not journalRefreshDue then
			journalRefreshDue = true
			ns.RegisterEvent(journalRefreshOwner, "PLAYER_REGEN_ENABLED", function()
				ns.UnregisterEvent(journalRefreshOwner, "PLAYER_REGEN_ENABLED")
				journalRefreshDue = false
				Safe.Call(refresh)
			end)
		end
		return
	end
	Safe.Call(refresh)
end

function mod.DungeonJournalHandlesMap(inst, record, sharedInstance)
	local dj = Journal()
	if not dj then return end
	-- A Journal page can exist even when its dungeon overlay is turned off.
	local settings = _G.ForeverDungeonJournalDB
	if type(settings) == "table" and settings.worldMapOverlay == false then return end
	local key = mod.DungeonJournalPage(inst, dj)
	if key then
		if record and type(dj.DUNGEON_MAPS) == "table" and dj.DUNGEON_MAPS[key] then OfferWing(dj, key, record) end
		return true
	end
	if sharedInstance then
		local toggle = _G.ForeverDungeonJournalWorldMapToggle
		return Safe.Call(dj.IsWorldMapOverlayAttached) or (toggle and Safe.Call(toggle.IsVisible, toggle))
	end
end
