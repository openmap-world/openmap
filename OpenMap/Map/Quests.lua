--------------------------------------------------------------------------------
-- The quests in your log on the stitched map, from every zone and at any zoom. Blizzard's map
-- shows a zone's quests only on that zone's own map (its QuestDataProvider: MapUtil.
-- ShouldMapTypeShowQuests), so zoomed out, or over the next zone, there were none until the map
-- underneath became theirs. Here every stitched map's quests (C_QuestLog.GetQuestsOnMap) are
-- OpenMap's own icons, in the look of Blizzard's (its map legend's); the map underneath keeps
-- Blizzard's own pins for its quests (and a continent its super-tracked quest's).
--
-- In the controller view (PadView.lua) Blizzard's map is under the view, unseen, and so are its pins:
-- every quest is OpenMap's icon there, the zone Blizzard's map is on too (with "all quests" off, only
-- that zone's). A click there tracks the quest and zooms to it, but doesn't open Blizzard's quest
-- log: nothing of Blizzard's map or quest log is changed from OpenMap's code while that view is on.
-- The "!" of the quests you can start there are OpenMap's icons too: the zone Blizzard's map is on, its
-- quest lines' starts (C_QuestLine.GetAvailableQuestLines), as its own pins for them show.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local L = ns.L
-- (the quest log's functions: the game's, looked up as they're used)
local function G(name) return _G[name] end

mod.defaults.allQuests = true   -- the quests in your log from every zone (off: Blizzard's, the zone's own map only)

local BADGE = { atlas = "UI-QuestPoi-QuestNumber", texture = "Interface\\GossipFrame\\ActiveQuestIcon", size = 22 }
local IN_PROGRESS = { atlas = "Quest-In-Progress-Icon-yellow", texture = "Interface\\GossipFrame\\IncompleteQuestIcon" }
local TURN_IN = { atlas = "UI-QuestPoi-QuestBangTurnIn", texture = "Interface\\GossipFrame\\ActiveQuestIcon" }
local FOCUSED = { atlas = "UI-QuestPoi-QuestNumber-SuperTracked", texture = "Interface\\GossipFrame\\ActiveQuestIcon", size = 22 }
local OFFER = { atlas = "QuestNormal", texture = "Interface\\GossipFrame\\AvailableQuestIcon", size = 22 }
local SAME = 0.002              -- world (normalized): one quest's icons this close are one
local EVERY = 0.5               -- seconds: the quest log changes in bursts
local READ_MS = 3               -- ms a frame spent reading the zones' quests (READ_MAPS: zones a frame, with no clock)
local READ_MAPS = 3
local NONE = {}
local set, offerSet, map, maps, events
local dirty = false             -- a refresh is wanted (Soon)
local waiting = false           -- ... and on its timer
local reading                   -- the zones being read: { list, at, found, seen, ids, ... } (RefreshQuests)
local lastRead                  -- the last reading, for /openmap status: { zones, ms, frames, worst }

-- the controller view is the map now (Blizzard's under it, unseen)
-- (and the own view in a fight, OwnView.lua: Blizzard's quest pins under it, unseen)
local function PadView() return (mod.PadViewOn and mod.PadViewOn()) or (mod.OwnViewOn and mod.OwnViewOn()) end

-- the maps the quests are read from: the stitched zones and cities (a city's quests are its zone's
-- too, at the same place: one icon, SAME)
local function Maps()
	if maps then return maps end
	maps = {}
	for _, info in ipairs(C_Map.GetMapChildrenInfo(S.WORLD, Enum.UIMapType.Zone, true) or NONE) do
		if S.Rect(info.mapID) then maps[#maps + 1] = info.mapID end
	end
	return maps
end

local function Enter(pin)
	local q = pin.data
	if not q then return end
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	local title = C_QuestLog.GetTitleForQuestID and C_QuestLog.GetTitleForQuestID(q.id)
	-- (its level and difficulty colour, "[39+] ", as Blizzard's own quest pins show it: their
	-- QuestPinMixin:OnMouseEnter, WoW Forever's DifficultyUtil)
	local decorate = G("SetQuestTitleLevelAndDifficultyColor")
	if title and decorate then title = decorate(q.id, title) end
	GameTooltip:SetText(title or "?", 1, 0.82, 0)
	local index = C_QuestLog.GetLogIndexForQuestID and C_QuestLog.GetLogIndexForQuestID(q.id)
	if q.complete then
		GameTooltip:AddLine(_G.QUEST_WATCH_QUEST_READY or L["Completed"], 0.5, 0.95, 0.4)
	elseif index and G("GetNumQuestLeaderBoards") and G("GetQuestLogLeaderBoard") then
		for i = 1, G("GetNumQuestLeaderBoards")(index) or 0 do
			local text, _, finished = G("GetQuestLogLeaderBoard")(i, index)
			if text and not finished then GameTooltip:AddLine((_G.QUEST_DASH or "- ") .. text, 1, 1, 1, true) end
		end
	end
	GameTooltip:AddLine((PadView() or (map and map.IsMaximized and map:IsMaximized())) and L["Click: track this quest and zoom to it"]
		or L["Click: track this quest, zoom to it and show it in the quest log"], 0.6, 0.6, 0.6)
	GameTooltip:Show()
	-- (the controller view: the quest's area, as Blizzard's map shows it for its own icons: PadView.lua)
	if PadView() and mod.PadQuestArea then mod.PadQuestArea(q.id, q.map) end
end

local function Leave()
	GameTooltip_Hide()
	if mod.PadQuestArea then mod.PadQuestArea(nil) end
end

-- The controller view: the focused (super-tracked) quest's icon in Blizzard's look for it (gold), and
-- its area shown while no other quest is hovered (PadView.lua), as Blizzard's map shows its own. (The
-- usual map has Blizzard's own icons and areas for this: left as it is)
local focusTint                 -- (a client without the gold atlas: the badge tinted gold instead)
local drawn = {}                -- the quests' icons up now (Draw)
local focusedPin                -- the one of them in the focused look (Focus)
-- one icon in a look: the badge, or the focused quest's gold one
local function Style(pin, on)
	local look = on and FOCUSED or BADGE
	pin.look = look
	S.Look(pin.Icon, look)
	S.Look(pin.Highlight, look)
	if on and focusTint then pin.Icon:SetVertexColor(1, 0.82, 0) else pin.Icon:SetVertexColor(1, 1, 1) end
end

local function Focus()
	if not set or not PadView() then return end
	if focusTint == nil then
		focusTint = not (C_Texture and C_Texture.GetAtlasInfo and C_Texture.GetAtlasInfo(FOCUSED.atlas))
	end
	local tracked = C_SuperTrack and C_SuperTrack.GetSuperTrackedQuestID and C_SuperTrack.GetSuperTrackedQuestID()
	local found
	if tracked then
		for _, pin in ipairs(drawn) do
			if pin.data and pin.data.id == tracked then found = pin break end
		end
	end
	if found ~= focusedPin then
		if focusedPin then Style(focusedPin, false) end
		if found then Style(found, true) end
		focusedPin = found
	end
	if mod.PadQuestFocus then mod.PadQuestFocus(found and tracked or nil, found and found.data.map or nil) end
end

-- a quest you can start: its name, and the quest line it begins (the game's own words)
local function EnterOffer(pin)
	local q = pin.data
	if not q then return end
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	GameTooltip:SetText(q.name or "?", 1, 0.82, 0)
	if q.line and q.line ~= "" and q.line ~= q.name then GameTooltip:AddLine(q.line, 0.6, 0.6, 0.6) end
	GameTooltip:Show()
end

-- a click: the quest tracked (as Blizzard's own quest icons do), the view in on it, and on the windowed
-- map its details in the quest log beside it, opened if it was closed. Not full screen: Blizzard's
-- details call takes the map out of full screen into the windowed map with its log. Never in combat:
-- opening the log lays the window out again
local ZOOM_TO = 6
local function Click(pin)
	local q = pin.data
	if not q then return end
	if C_SuperTrack and C_SuperTrack.SetSuperTrackedQuestID then
		if C_QuestLog.AddQuestWatch and not (C_QuestLog.GetQuestWatchType and C_QuestLog.GetQuestWatchType(q.id)) then
			pcall(C_QuestLog.AddQuestWatch, q.id)
		end
		C_SuperTrack.SetSuperTrackedQuestID(q.id)
	end
	Focus()                                         -- (at once: the redraw the event asks for comes later)
	if S.GlideToWorld then S.GlideToWorld(pin.u, pin.v, ZOOM_TO) end
	-- (the controller view: Blizzard's quest log is left as it is, as a dungeon's map is: its details
	-- would set the pad's buttons from OpenMap's code)
	if PadView() then return end
	-- (in combat with the gamepad's UI, Blizzard's quest details would set the pad's buttons from
	-- OpenMap's code, which combat blocks: they wait, as a dungeon's map does)
	if mod.PadWaits and mod.PadWaits() then return end
	local log = map and map.QuestLog
	local details = G("QuestMapFrame_ShowQuestDetails")
	if not log or not details or (map.IsMaximized and map:IsMaximized()) then return end
	if not log:IsShown() and not InCombatLockdown() and map.HandleUserActionOpenSidePanel then
		map:HandleUserActionOpenSidePanel()
		if map.SidePanelToggle and map.SidePanelToggle.Refresh then map.SidePanelToggle:Refresh() end
	end
	if log:IsShown() then details(q.id) end
end

-- the state mark over a pin's badge (made once: pins are pooled, and this set's are only ever quests)
local function Mark(pin, complete)
	if not pin.questMark then
		pin.questMark = pin:CreateTexture(nil, "OVERLAY")
		pin.questMark:SetPoint("CENTER")
	end
	local m, size = pin.questMark, BADGE.size * 0.6
	m:SetSize(size, size)
	S.Look(m, complete and TURN_IN or IN_PROGRESS)
	m:Show()
end

-- the controller view's "!": the quests you can start in the zone Blizzard's map is on (its quest
-- lines' pins, unseen under the view, show the same); not those in your log (drawn above), nor
-- another floor's, nor a hidden one
local function Offers(ids)
	local zone = map and map.GetMapID and map:GetMapID()
	if not (offerSet and zone and S.Rect(zone) and C_QuestLine and C_QuestLine.GetAvailableQuestLines) then return end
	S.SetPinSetOn(offerSet, true)
	local same = Enum.QuestLineFloorLocation and Enum.QuestLineFloorLocation.Same or 2
	local seen = {}
	for _, q in ipairs(C_QuestLine.GetAvailableQuestLines(zone) or NONE) do
		local id = q.questID
		if id and q.x and q.y and not q.isHidden and not q.inProgress and not ids[id] and not seen[id]
			and (q.floorLocation == nil or q.floorLocation == same) then
			seen[id] = true
			local u, v = mod.ToWorld(zone, q.x, q.y)
			local pin = S.AddPin(offerSet, u, v, OFFER, { id = id, name = q.questName, line = q.questLineName })
			pin:SetScript("OnEnter", EnterOffer)
			pin:SetScript("OnLeave", GameTooltip_Hide)
		end
	end
end

-- Reading the zones' quests is a call into the game for every stitched zone and city (C_QuestLog.
-- GetQuestsOnMap: dozens of them), and it all landed in one frame half a second after every opening of
-- the map, again after each burst of quest log updates while it was open (and once more after it
-- closed, if one was still waiting). So: the zones are read a few a frame (READ_MS), and the icons are
-- put up together once every zone is in, those on the map staying until then; and nothing is read
-- while the map is closed (it's read as it next opens). /openmap status says what the last reading cost.

-- one zone's quests into the reading `r`
local function ReadMap(r, mapID)
	if mapID == r.host then return end
	local have = G("HaveQuestData")
	for _, q in ipairs(C_QuestLog.GetQuestsOnMap(mapID) or NONE) do
		local id = q.questID
		if id and q.x and q.y and not q.isMapIndicatorQuest and (not have or have(id))
			and not (r.continent and id == r.tracked) then
			local u, v = mod.ToWorld(mapID, q.x, q.y)
			local key = u and (id .. ":" .. math.floor(u / SAME) .. ":" .. math.floor(v / SAME))
			local onHost = u and r.hostQuests[id] and r.hl and u >= r.hl and u <= r.hr and v >= r.ht and v <= r.hb
			if key and not r.seen[key] and not onHost then
				r.seen[key] = true
				r.ids[id] = true
				r.found[#r.found + 1] = { u, v, id, C_QuestLog.IsComplete and C_QuestLog.IsComplete(id) or false, mapID }
			end
		end
	end
end

-- every zone read: the icons, all at once
local function Draw(r)
	if offerSet then
		S.ClearPinSet(offerSet)
		S.SetPinSetOn(offerSet, false)
	end
	if focusedPin then Style(focusedPin, false) focusedPin = nil end   -- (its tint: AddPin keeps it)
	S.ClearPinSet(set)
	wipe(drawn)
	for _, f in ipairs(r.found) do
		local pin = S.AddPin(set, f[1], f[2], BADGE, { id = f[3], complete = f[4], map = f[5] })
		Mark(pin, f[4])
		pin:SetScript("OnEnter", Enter)
		pin:SetScript("OnLeave", Leave)
		pin.OnClick = Click
		drawn[#drawn + 1] = pin
	end
	Focus()
	if r.pad then Offers(r.ids) end
end

local Soon
local reader = CreateFrame("Frame")
reader:Hide()
reader:SetScript("OnUpdate", function(self)
	local r = reading
	if not r then self:Hide() return end
	local list, n = r.list, 0
	local t0 = debugprofilestop and debugprofilestop()
	while r.at <= #list do
		local mapID = list[r.at]
		r.at, n = r.at + 1, n + 1
		local ok, err = pcall(ReadMap, r, mapID)
		if not ok then                               -- (a client difference: said once, the icons left as they are)
			reading = nil
			self:Hide()
			geterrorhandler()(err)
			return
		end
		if t0 and debugprofilestop() - t0 >= READ_MS or not t0 and n >= READ_MAPS then break end
	end
	r.frames = r.frames + 1
	if t0 then
		local ms = debugprofilestop() - t0
		r.ms, r.worst = r.ms + ms, math.max(r.worst, ms)
	end
	if r.at <= #list then return end
	reading = nil
	self:Hide()
	lastRead = { zones = #list, ms = r.ms, frames = r.frames, worst = r.worst }
	Draw(r)
	if dirty then Soon() end                        -- (the quest log changed while it was read: once more)
end)

-- for /openmap status: what the last reading of the zones' quests cost
function mod.QuestsStatus()
	if not lastRead then return "Quests from every zone: not read yet." end
	return ("Quests from every zone: %d zones read in %.0f ms over %d frames (the longest %.1f ms)%s."):format(
		lastRead.zones, lastRead.ms, lastRead.frames, lastRead.worst, reading and "; reading again now" or "")
end

function mod:RefreshQuests()
	dirty = false
	reading = nil                                   -- (one under way was for how things were)
	reader:Hide()
	if not set and S.IsBuilt() then set = S.PinSet("quests", 1, 5) end   -- (built as the map first opens)
	if not set then return end
	if not offerSet and S.IsBuilt() then offerSet = S.PinSet("questoffers", 1, 4) end   -- (under the quests' icons)
	-- (and as Blizzard's own quests: not with the map's Quest Objectives off, its questPOI)
	local pad = PadView()
	local all = mod.db.allQuests ~= false
	local on = (all or pad) and (mod.IsStitched() or pad) and C_QuestLog.GetQuestsOnMap ~= nil
		and not (GetCVarBool and not GetCVarBool("questPOI"))
	S.SetPinSetOn(set, on)
	if not on then                                  -- (off: gone at once)
		if offerSet then
			S.ClearPinSet(offerSet)
			S.SetPinSetOn(offerSet, false)
		end
		if focusedPin then Style(focusedPin, false) focusedPin = nil end
		S.ClearPinSet(set)
		wipe(drawn)
		if mod.PadQuestFocus then mod.PadQuestFocus(nil) end   -- (no icons: no focused quest's area either)
		return
	end
	-- the controller view with "all quests" off: the zone (or city) Blizzard's map is on, whose quests
	-- no pin of Blizzard's shows there
	local list = Maps()
	if pad and not all then
		local zone = map and map.GetMapID and map:GetMapID()
		list = zone and S.Rect(zone) and { zone } or NONE
	end
	-- the map underneath: Blizzard draws its quests (a continent, only the super-tracked one). Not under the
	-- controller view, nor the own view in a fight: its pins are there unseen, so its quests are OpenMap's too
	local host = not pad and mod.HostMap() or nil
	local hostInfo = host and C_Map.GetMapInfo(host)
	local continent = hostInfo and hostInfo.mapType == Enum.UIMapType.Continent
	local tracked = C_SuperTrack and C_SuperTrack.GetSuperTrackedQuestID and C_SuperTrack.GetSuperTrackedQuestID()
	local hostQuests = {}
	if host and not continent then
		for _, q in ipairs(C_QuestLog.GetQuestsOnMap(host) or NONE) do hostQuests[q.questID] = true end
	end
	local hl, hr, ht, hb
	if host then hl, hr, ht, hb = S.Rect(host) end
	-- (the zones read over the next frames, the icons put up once all are in: the reader, above)
	reading = { list = list, at = 1, found = {}, seen = {}, ids = {}, pad = pad, host = host, hostQuests = hostQuests,
		continent = continent, tracked = tracked, hl = hl, hr = hr, ht = ht, hb = hb, ms = 0, frames = 0, worst = 0 }
	reader:Show()
end

-- (a burst of quest log updates: one refresh)
Soon = function()
	dirty = true
	if waiting then return end
	waiting = true
	C_Timer.After(EVERY, function()
		waiting = false
		-- (the map closed meanwhile: it's read as it next opens; a reading under way: again once it's done)
		if dirty and not reading and map and map:IsShown() then mod:RefreshQuests() end
	end)
end

function mod:SetupQuests(worldMap)
	map = worldMap
	if events then return end                   -- (once: its events and hooks)
	events = CreateFrame("Frame")
	for _, e in ipairs({ "QUEST_LOG_UPDATE", "QUEST_POI_UPDATE", "QUEST_WATCH_LIST_CHANGED", "SUPER_TRACKING_CHANGED", "CVAR_UPDATE", "QUESTLINE_UPDATE" }) do
		pcall(events.RegisterEvent, events, e)
	end
	events:SetScript("OnEvent", function(_, event, cvar)
		if event == "CVAR_UPDATE" and cvar ~= "questPOI" then return end
		if map:IsShown() then Soon() end
	end)
	hooksecurefunc(map, "OnMapChanged", Soon)
	map:HookScript("OnShow", Soon)
	-- (closed while its zones were being read: left there, and read as the map next opens)
	map:HookScript("OnHide", function()
		if reading then
			reading = nil
			reader:Hide()
			dirty = true
		end
	end)
end
