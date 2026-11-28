--------------------------------------------------------------------------------
-- Townsfolk and rare mobs on the world map, from Questie's NPC database
-- (npcFlags, rank, spawns), or another addon's database of the same shape
-- (OpenMapAPI.RegisterTownsfolkProvider). Each kind is a pin set, built the first time it's
-- turned on (a few hundred NPCs a frame, so nothing stalls).
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")

-- the game's own icon for a kind: the first of `atlases` this client has, else the first of
-- `textures` it has (an Interface\Icons one cropped of its dark edge), else the trainer bubble
local function Pick(atlases, textures, size)
	for _, a in ipairs(atlases) do
		if C_Texture and C_Texture.GetAtlasInfo and C_Texture.GetAtlasInfo(a) then return { atlas = a, size = size } end
	end
	for _, t in ipairs(textures) do
		if not GetFileIDFromPath or GetFileIDFromPath(t) then
			local look = { texture = t, size = size }
			if t:find("\\Icons\\", 1, true) then look.coords = { 0.08, 0.92, 0.08, 0.92 } end
			return look
		end
	end
	return { texture = "Interface\\GossipFrame\\TrainerGossipIcon", size = size }
end

local MY_CLASS = select(2, UnitClass("player")) or "WARRIOR"

-- kind -> look, the zoom it shows from, and what picks its NPCs
local KINDS = {
	{ key = "vendor", name = ns.L["Vendors"], flag = "VENDOR", zoom = 8,
		look = { texture = "Interface\\GossipFrame\\VendorGossipIcon", size = 14 } },
	-- ammo: the NPCs who sell arrows or bullets (the items' vendors in Questie's database, every
	-- level of ammo, Questie's own list of them)
	{ key = "ammo", name = ns.L["Ammo"], items = { 2512, 2515, 3030, 11285, 19316, 28053, 28056,
		2516, 2519, 3033, 11284, 19317, 28060, 28061 }, zoom = 6,
		look = Pick({ "Ammunition", "Mobile-Ammo" }, { "Interface\\Minimap\\Tracking\\Ammunition",
			"Interface\\Icons\\INV_Ammo_Arrow_02", "Interface\\Icons\\INV_Ammo_Bullet_02" }, 20) },
	{ key = "repair", name = ns.L["Repair"], flag = "REPAIR", zoom = 6,
		look = { texture = "Interface\\Minimap\\Tracking\\Repair", fallback = "Interface\\GossipFrame\\VendorGossipIcon", size = 16 } },
	{ key = "innkeeper", name = ns.L["Innkeepers"], flag = "INNKEEPER", zoom = 4,
		look = { texture = "Interface\\Minimap\\Tracking\\Innkeeper", fallback = "Interface\\GossipFrame\\BinderGossipIcon", size = 16 } },
	{ key = "banker", name = ns.L["Bankers"], flag = "BANKER", zoom = 6,
		look = { texture = "Interface\\Minimap\\Tracking\\Banker", fallback = "Interface\\GossipFrame\\BankerGossipIcon", size = 16 } },
	-- mailboxes: objects, not NPCs (Questie's list of them, Townsfolk.GetMailboxes)
	{ key = "mailbox", name = ns.L["Mailboxes"], mailbox = true, zoom = 6,
		look = { texture = "Interface\\Minimap\\Tracking\\Mailbox", fallback = "Interface\\Icons\\INV_Letter_15", size = 16 } },
	{ key = "auctioneer", name = ns.L["Auctioneers"], flag = "AUCTIONEER", zoom = 6,
		look = { texture = "Interface\\Minimap\\Tracking\\Auctioneer", fallback = "Interface\\GossipFrame\\VendorGossipIcon", size = 16 } },
	{ key = "stable", name = ns.L["Stable masters"], flag = "STABLEMASTER", zoom = 6,
		look = { texture = "Interface\\Minimap\\Tracking\\StableMaster", fallback = "Interface\\GossipFrame\\PetitionGossipIcon", size = 16 } },
	-- (your class's own icon: classicon-warrior ..., ClassIcon_Warrior ...)
	{ key = "classTrainer", name = ns.L["Class trainers"], flag = "TRAINER", class = true, zoom = 6,
		look = Pick({ "classicon-" .. MY_CLASS:lower() },
			{ "Interface\\Icons\\ClassIcon_" .. MY_CLASS:sub(1, 1) .. MY_CLASS:sub(2):lower(), "Interface\\Minimap\\Tracking\\Class" }, 18) },
	-- hunters' pet trainers, out of the other trainers
	{ key = "petTrainer", name = ns.L["Pet trainers"], flag = "TRAINER", pet = true, zoom = 6,
		look = Pick({}, { "Interface\\Icons\\Ability_Hunter_BeastTraining", "Interface\\Icons\\Ability_Hunter_BeastCall" }, 18) },
	-- profession trainers, one kind per profession (picked by subname, PROF_WORDS below); the
	-- trainers that are neither a class's nor a profession's (riding, weapons, pets ...) after them
	{ key = "prof_alchemy", name = ns.L["Alchemy"], flag = "TRAINER", prof = "alchemy", zoom = 8,
		look = Pick({ "Mobile-Alchemy" }, { "Interface\\Icons\\Trade_Alchemy" }, 20) },
	{ key = "prof_blacksmithing", name = ns.L["Blacksmithing"], flag = "TRAINER", prof = "blacksmithing", zoom = 8,
		look = Pick({ "Mobile-Blacksmithing" }, { "Interface\\Icons\\Trade_BlackSmithing" }, 20) },
	{ key = "prof_enchanting", name = ns.L["Enchanting"], flag = "TRAINER", prof = "enchanting", zoom = 8,
		look = Pick({ "Mobile-Enchanting" }, { "Interface\\Icons\\Trade_Engraving" }, 20) },
	{ key = "prof_engineering", name = ns.L["Engineering"], flag = "TRAINER", prof = "engineering", zoom = 8,
		look = Pick({ "Mobile-Enginnering", "Mobile-Engineering" }, { "Interface\\Icons\\Trade_Engineering" }, 20) },
	{ key = "prof_herbalism", name = ns.L["Herbalism"], flag = "TRAINER", prof = "herbalism", zoom = 8,
		look = Pick({ "Mobile-Herbalism" }, { "Interface\\Icons\\Trade_Herbalism" }, 20) },
	{ key = "prof_leatherworking", name = ns.L["Leatherworking"], flag = "TRAINER", prof = "leatherworking", zoom = 8,
		look = Pick({ "Mobile-Leatherworking" }, { "Interface\\Icons\\Trade_LeatherWorking" }, 20) },
	{ key = "prof_mining", name = ns.L["Mining"], flag = "TRAINER", prof = "mining", zoom = 8,
		look = Pick({ "Mobile-Mining" }, { "Interface\\Icons\\Trade_Mining" }, 20) },
	{ key = "prof_skinning", name = ns.L["Skinning"], flag = "TRAINER", prof = "skinning", zoom = 8,
		look = Pick({ "Mobile-Skinning" }, { "Interface\\Icons\\INV_Misc_Pelt_Wolf_01" }, 20) },
	{ key = "prof_tailoring", name = ns.L["Tailoring"], flag = "TRAINER", prof = "tailoring", zoom = 8,
		look = Pick({ "Mobile-Tailoring" }, { "Interface\\Icons\\Trade_Tailoring" }, 20) },
	{ key = "prof_cooking", name = ns.L["Cooking"], flag = "TRAINER", prof = "cooking", zoom = 8,
		look = Pick({ "Mobile-Cooking" }, { "Interface\\Icons\\INV_Misc_Food_15" }, 20) },
	{ key = "prof_fishing", name = ns.L["Fishing"], flag = "TRAINER", prof = "fishing", zoom = 8,
		look = Pick({}, { "Interface\\Icons\\Trade_Fishing" }, 20) },   -- (the game's Mobile-Fishing emblem is faint on the map: the trade icon, cropped)
	{ key = "prof_firstaid", name = ns.L["First Aid"], flag = "TRAINER", prof = "firstaid", zoom = 8,
		look = Pick({ "Mobile-FirstAid" }, { "Interface\\Icons\\Spell_Holy_SealOfSacrifice" }, 20) },
	{ key = "profTrainer", name = ns.L["Other trainers"], flag = "TRAINER", profession = true, zoom = 8,
		look = { texture = "Interface\\Minimap\\Tracking\\Profession", fallback = "Interface\\GossipFrame\\TrainerGossipIcon", size = 14 } },
	-- spirit healers: the game ships no graveyard table for this client, so they come from
	-- Questie's NPC spawns too (the Spirit Healer NPC; both factions use the same ones)
	{ key = "spirit", name = ns.L["Spirit healers"], ids = { [6491] = true }, zoom = 3, hostile = true,
		look = { atlas = "poi-soulspiritghost", texture = "Interface\\Minimap\\ObjectIcons", size = 16 } },
	{ key = "rare", name = ns.L["Rare mobs"], rare = true, zoom = 3, hostile = true,
		look = { atlas = "VignetteKillElite", texture = "Interface\\TargetingFrame\\UI-RaidTargetingIcon_8", size = 18 } },
}
mod.TOWNSFOLK = KINDS
-- ammo's icon lit, brighter than at mouseover, all the time (Stitch.lua look.glow)
for _, k in ipairs(KINDS) do if k.key == "ammo" then k.look.glow = 0.7 end end

local d = mod.defaults
d.townsfolk = {}
for _, k in ipairs(KINDS) do d.townsfolk[k.key] = false end

local built = {}                -- kind key -> true once its pins exist
local building = false
local tries = 0                 -- retries while Questie's database loads
local RANK = { [2] = ns.L["Rare Elite"], [4] = ns.L["Rare"] }
-- the classes' English names, as Questie's subnames have them on every client
local ENGLISH_CLASS_NAMES = {
	WARRIOR = "Warrior", PALADIN = "Paladin", HUNTER = "Hunter", ROGUE = "Rogue", PRIEST = "Priest",
	SHAMAN = "Shaman", MAGE = "Mage", WARLOCK = "Warlock", DRUID = "Druid", DEATHKNIGHT = "Death Knight",
	MONK = "Monk", DEMONHUNTER = "Demon Hunter", EVOKER = "Evoker",
}
-- a profession trainer's profession from its (English, lower-case) subname: "Expert Alchemist",
-- "Journeyman Blacksmith", "Weaponsmith Trainer", "Gnome Engineer", "Master Leatherworker" ...
local PROF_WORDS = {
	{ "alchem", "alchemy" },
	{ "blacksmith", "blacksmithing" }, { "armorsmith", "blacksmithing" }, { "weaponsmith", "blacksmithing" },
	{ "swordsmith", "blacksmithing" }, { "axesmith", "blacksmithing" }, { "hammersmith", "blacksmithing" },
	{ "enchant", "enchanting" },
	{ "engineer", "engineering" },
	{ "herbal", "herbalism" },
	{ "leatherwork", "leatherworking" },
	{ "mining", "mining" }, { "miner", "mining" },
	{ "skinn", "skinning" },
	{ "tailor", "tailoring" },
	{ "cook", "cooking" }, { "chef", "cooking" },
	{ "fishing", "fishing" }, { "fisherman", "fishing" },
	{ "first aid", "firstaid" }, { "physician", "firstaid" },
}
local function ProfOf(sub)
	for _, w in ipairs(PROF_WORDS) do
		if sub:find(w[1], 1, true) then return w[2] end
	end
end
local told = false              -- said once this session that Questie isn't installed

-- another addon's NPC database in Questie's shape (OpenMapAPI.RegisterTownsfolkProvider): { db, zones,
-- mailboxes = fn(faction "A" / "H") -> object IDs (optional) }
local provider
function mod.SetTownsfolkProvider(p)
	provider = p
	for k in pairs(built) do
		built[k] = nil
		local set = S.GetPinSet("tf_" .. k)
		if set then S.ClearPinSet(set) end
	end
	tries = 0
	if mod.RefreshPanel then mod:RefreshPanel() end
	mod:RefreshTownsfolk()
end

-- whether there's a database to read: Questie's, or one given (a player's own: Questie's database
-- without Questie)
function mod.HasTownsfolk()
	local loaded = C_AddOns and C_AddOns.IsAddOnLoaded or IsAddOnLoaded
	return provider ~= nil or _G.QuestieLoader ~= nil or (loaded and loaded("Questie")) and true or false
end

local function Questie()
	if provider then return provider.db, provider.zones end
	local loader = _G.QuestieLoader
	if not loader then return end
	local ok, db = pcall(loader.ImportModule, loader, "QuestieDB")
	local ok2, zones = pcall(loader.ImportModule, loader, "ZoneDB")
	if ok and ok2 and db and db.NPCPointers and db.QueryNPCSingle and zones then return db, zones end
end

-- An NPC that walks about (Girl with Puppies round Orgrimmar) has every point of its path among its
-- spawns: past WANDER of them in one zone, one pin, at the spawn nearest the middle of them all
local WANDER = 6
local function Middle(coords)
	local sx, sy, n = 0, 0, 0
	for _, c in ipairs(coords) do
		if c[1] and c[1] >= 0 then sx, sy, n = sx + c[1], sy + c[2], n + 1 end
	end
	if n == 0 then return coords end
	sx, sy = sx / n, sy / n
	local best, bestD
	for _, c in ipairs(coords) do
		if c[1] and c[1] >= 0 then
			local d = (c[1] - sx) ^ 2 + (c[2] - sy) ^ 2
			if not bestD or d < bestD then best, bestD = c, d end
		end
	end
	return { best }
end

local function PinEnter(pin)
	local n = pin.data
	GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
	GameTooltip:AddLine(n.name, 1, 0.82, 0)
	if n.sub then GameTooltip:AddLine(n.sub, 1, 1, 1) end
	local lv = n.min and (n.min == n.max and tostring(n.min) or (n.min .. "-" .. (n.max or n.min)))
	if lv or n.rank then
		GameTooltip:AddLine(((lv and (LEVEL .. " " .. lv)) or "") .. (n.rank and ("  " .. n.rank) or ""), 0.8, 0.8, 0.8)
	end
	GameTooltip:Show()
end

-- every wanted NPC, sorted into kinds; then pins for the kinds that are on
local function Build(kinds, done)
	local QDB, ZoneDB = Questie()
	if not QDB then return done(false) end
	local flags = QDB.npcFlags or {}
	local faction = UnitFactionGroup("player") == "Horde" and "H" or "A"
	local myClass = select(2, UnitClass("player"))
	-- a trainer's class from its subname, by class token: Questie's subnames are English ("Warrior
	-- Trainer") whatever the client's language, or translated by Questie, so both are looked for, in
	-- lower case ("Maître des guerriers"); longest first (Demon Hunter before Hunter)
	local classNames = {}
	local function AddNames(t)
		for token, n in pairs(t or {}) do
			if type(n) == "string" and n ~= "" then classNames[#classNames + 1] = { n:lower(), token } end
		end
	end
	AddNames(ENGLISH_CLASS_NAMES)
	AddNames(LOCALIZED_CLASS_NAMES_MALE)
	AddNames(LOCALIZED_CLASS_NAMES_FEMALE)
	table.sort(classNames, function(a, b) return #a[1] > #b[1] end)

	-- a kind's pins at each of its spawns ({ [areaID] = { { x, y }, ... } }, as Questie keeps them);
	-- `walker`: one NPC's, a path walked taken as one place (Middle)
	local function Pins(k, spawns, info, walker)
		-- (the lowest of OpenMap's icons, with the route lines: under quests' icons, OpenMap's and Questie's, a pin
		-- of yours, a dungeon, a flight master, your group's dots and your arrow)
		local set = S.PinSet("tf_" .. k.key, k.zoom, 1)
		for areaID, coords in pairs(spawns) do
			if walker and #coords > WANDER then coords = Middle(coords) end
			local uiMapID = ZoneDB:GetUiMapIdByAreaId(areaID)
			local l, r, t, b
			if uiMapID then l, r, t, b = S.Rect(uiMapID) end
			if l then
				for _, c in ipairs(coords) do
					if c[1] and c[1] >= 0 then
						local pin = S.AddPin(set, l + c[1] / 100 * (r - l), t + c[2] / 100 * (b - t), k.look, info)
						pin:SetScript("OnEnter", PinEnter)
						pin:SetScript("OnLeave", GameTooltip_Hide)
					end
				end
			end
		end
	end
	-- the mailboxes, all at once (a few dozen objects): your faction's, as Questie sorts them, or
	-- every one where it can't
	local function Mailboxes(k)
		if provider then
			if not (provider.mailboxes and QDB.QueryObjectSingle) then return end
			local info = { name = MINIMAP_TRACKING_MAILBOX or "Mailbox" }
			for _, id in ipairs(provider.mailboxes(faction) or {}) do
				local spawns = QDB.QueryObjectSingle(id, "spawns")
				if spawns then Pins(k, spawns, info) end
			end
			return
		end
		local folk = _G.QuestieLoader and select(2, pcall(_G.QuestieLoader.ImportModule, _G.QuestieLoader, "Townsfolk"))
		if type(folk) ~= "table" or not folk.GetMailboxes or not QDB.QueryObjectSingle then return end
		local list
		if folk.GetFactionSpecificMailboxes then
			local ok, alliance, horde = pcall(folk.GetFactionSpecificMailboxes)
			if ok then list = faction == "H" and horde or alliance end
		end
		list = (type(list) == "table" and #list > 0) and list or folk.GetMailboxes() or {}
		local info = { name = MINIMAP_TRACKING_MAILBOX or "Mailbox" }
		for _, id in ipairs(list) do
			local spawns = QDB.QueryObjectSingle(id, "spawns")
			if spawns then Pins(k, spawns, info) end
		end
	end

	-- the kinds picked by what they sell: their items' vendors, once
	local sells = {}
	for _, k in ipairs(kinds) do
		if k.items and QDB.QueryItemSingle then
			local set = {}
			for _, item in ipairs(k.items) do
				local ok, vendors = pcall(QDB.QueryItemSingle, item, "vendors")
				if ok and type(vendors) == "table" then
					for _, v in ipairs(vendors) do set[v] = true end
				end
			end
			sells[k] = set
		end
	end

	local ids = {}
	for id in pairs(QDB.NPCPointers) do ids[#ids + 1] = id end
	local i = 0
	local Step
	-- (what's asked of every NPC, once: the rank only when rare mobs are wanted; a trainer's kind
	-- from its subname once per NPC, not once per trainer kind)
	local needRank = false
	for _, k in ipairs(kinds) do if k.rare then needRank = true end end
	local function TrainerOf(id)
		local sub = (QDB.QueryNPCSingle(id, "subName") or ""):lower()
		for _, c in ipairs(classNames) do
			if sub:find(c[1], 1, true) then return "class", c[2] end
		end
		if sub:find("pet trainer", 1, true) then return "pet" end
		local prof = ProfOf(sub)
		if prof then return "prof", prof end
		return "other"
	end
	local want = {}
	local function Chunk()
		for _ = 1, 400 do
			i = i + 1
			local id = ids[i]
			if not id then return true end
			local f = QDB.QueryNPCSingle(id, "npcFlags") or 0
			local rank = needRank and QDB.QueryNPCSingle(id, "rank") or 0
			local tKind, tWhat           -- (the trainer's kind, read the first time a trainer kind asks)
			wipe(want)
			for _, k in ipairs(kinds) do
				local hit
				if k.items then
					hit = sells[k] and sells[k][id] or false
				elseif k.ids then
					hit = k.ids[id] or false
				elseif k.rare then
					hit = RANK[rank] ~= nil
				elseif flags[k.flag] and bit.band(f, flags[k.flag]) ~= 0 then
					hit = true
					if k.class or k.profession or k.prof or k.pet then
						if not tKind then tKind, tWhat = TrainerOf(id) end
						if k.class then hit = tKind == "class" and tWhat == myClass
						elseif k.pet then hit = tKind == "pet"
						elseif k.prof then hit = tKind == "prof" and tWhat == k.prof
						else hit = tKind == "other" end
					end
				end
				if hit then want[#want + 1] = k end
			end
			if #want > 0 then
				local friendly = QDB.QueryNPCSingle(id, "friendlyToFaction") or ""
				local spawns = QDB.QueryNPCSingle(id, "spawns")
				local info = {
					name = QDB.QueryNPCSingle(id, "name") or "?", sub = QDB.QueryNPCSingle(id, "subName"),
					min = QDB.QueryNPCSingle(id, "minLevel"), max = QDB.QueryNPCSingle(id, "maxLevel"),
					rank = RANK[needRank and rank or QDB.QueryNPCSingle(id, "rank") or 0],
				}
				for _, k in ipairs(want) do
					-- (not spirit healers or rare mobs: one NPC at many places, each a place of its own)
					if (k.hostile or friendly:find(faction, 1, true)) and spawns then Pins(k, spawns, info, not (k.ids or k.rare)) end
				end
			end
		end
	end
	local npcs = false              -- (any kind picked from the NPCs: else no NPC to go through)
	for _, k in ipairs(kinds) do
		if k.mailbox then
			local ok, err = pcall(Mailboxes, k)
			if not ok then geterrorhandler()(err) end
		else
			npcs = true
		end
	end
	if not npcs then return done(true) end
	function Step()
		local ok, finished = pcall(Chunk)
		if not ok then
			geterrorhandler()(finished)
			return done(false)
		end
		if finished then return done(true) end
		C_Timer.After(0, Step)
	end
	Step()
end

-- shows / hides each kind; builds the ones turned on for the first time
function mod:RefreshTownsfolk()
	if not S.IsBuilt() then return end
	-- (once: "Profession trainers" on, from before they were split by profession -> every profession on)
	local tf = self.db.townsfolk
	if tf.profTrainer and not tf.profSplit then
		for _, k in ipairs(KINDS) do if k.prof then tf[k.key] = true end end
	end
	tf.profSplit = true
	local todo = {}
	for _, k in ipairs(KINDS) do
		local on = self.db.townsfolk[k.key]
		if on and not built[k.key] then todo[#todo + 1] = k end
		local set = S.GetPinSet("tf_" .. k.key)
		if set then S.SetPinSetOn(set, on) end
	end
	if #todo == 0 or building then return end
	-- no Questie at all (not just its database still loading): nothing to wait for
	if not mod.HasTownsfolk() then
		if not told then
			told = true
			ns:Print(ns.L["World map: townsfolk and rare mobs come from Questie's database. Install and enable Questie to see them."])
		end
		return
	end
	building = true
	for _, k in ipairs(todo) do built[k.key] = true end
	Build(todo, function(ok)
		building = false
		if not ok then
			-- Questie's database isn't ready yet (it loads after login), or a build failed: try again shortly
			for _, k in ipairs(todo) do
				built[k.key] = nil
				local set = S.GetPinSet("tf_" .. k.key)
				if set then S.ClearPinSet(set) end
			end
			tries = tries + 1
			if tries <= 30 then C_Timer.After(2, function() self:RefreshTownsfolk() end)
			else ns:Print(ns.L["World map: townsfolk and rares need Questie's database, which isn't available."]) end
			return
		end
		tries = 0
		self:RefreshTownsfolk()
	end)
end
