local _, ns = ...
local mod = ns.GetModule and ns:GetModule("worldmap") or ns.mod

-- Standalone QuestieDB (LibQuestieDB) support when Questie itself is not installed:
-- registers a provider through OpenMapAPI.RegisterTownsfolkProvider so Townsfolk and
-- Dungeons both read it without duplicating adapters.

local function DecodeTable(v)
	if type(v) == "table" then return v end
	if type(v) ~= "string" then return nil end
	local fn = (loadstring or load)(v)
	if not fn then return nil end
	local ok, t = pcall(fn)
	return ok and type(t) == "table" and t or nil
end

local function BuildQuestieDBProvider(ldb)
	if type(ldb) ~= "table" or not ldb.Npc or not ldb.Npc.GetAllIds or not ldb.Npc.Get or not ldb.Enum then
		return nil
	end
	local zdb = ldb.Support and ldb.Support.Get and ldb.Support.Get("ZoneDB")
	local zpriv = zdb and zdb.private
	local areaMap = DecodeTable(zpriv and zpriv.areaIdToUiMapId)
	if not areaMap then return nil end

	local areaToUiMap = {}
	for k, v in pairs(areaMap) do areaToUiMap[k] = v end
	for k, v in pairs(DecodeTable(zpriv.areaIdToUiMapIdOverride) or {}) do areaToUiMap[k] = v end

	local db = {
		NPCPointers = ldb.Npc.GetAllIds(true),
		npcFlags = ldb.Enum.npcFlags or {},
		QueryNPCSingle = ldb.Npc.Get,
		QueryObjectSingle = ldb.Object and ldb.Object.Get or nil,
	}

	local zones = {
		GetUiMapIdByAreaId = function(_, areaID) return areaToUiMap[areaID] end,
	}

	local dungeons = zpriv and zpriv.dungeons
	if ldb.Quest and ldb.Quest.GetAllIds and ldb.Quest.Get and type(dungeons) == "table" then
		local uiMapToArea = DecodeTable(zpriv.uiMapIdToAreaId) or {}
		local byName = {}
		local function AddName(n, areaId)
			if type(n) == "string" and n ~= "" and (not byName[n] or areaId < byName[n]) then
				byName[n] = areaId
			end
		end
		for areaId, e in pairs(dungeons) do
			local loc = C_Map and C_Map.GetAreaInfo and C_Map.GetAreaInfo(areaId)
			AddName(loc, areaId)
			if type(e) == "table" then AddName(e[1], areaId) end
		end
		db.QuestPointers = ldb.Quest.GetAllIds(true)
		db.QueryQuestSingle = ldb.Quest.Get
		zones.GetDungeons = function() return dungeons end
		zones.GetAreaIdByUiMapId = function(_, mapID) return uiMapToArea[mapID] end
		zones.GetAreaIdByName = function(_, name)
			if type(name) ~= "string" then return nil end
			if byName[name] then return byName[name] end
			local base = name:match("^(.-)%s*%-%s*[^-]+$")
			return base and byName[base] or nil
		end
	end

	return { db = db, zones = zones }
end

local function RegisterStandaloneQuestieDB()
	if _G.QuestieLoader then return end
	if mod.TownsfolkProvider and mod.TownsfolkProvider() then return end
	local api = _G.OpenMapAPI
	if type(api) ~= "table" or type(api.RegisterTownsfolkProvider) ~= "function" then return end
	local p = BuildQuestieDBProvider(_G.LibQuestieDB)
	if p then
		api.RegisterTownsfolkProvider("QuestieDB", p)
	end
end

mod.RegisterStandaloneQuestieDB = RegisterStandaloneQuestieDB
mod.DecodeQuestieDBTable = DecodeTable

if _G.LibQuestieDB then
	RegisterStandaloneQuestieDB()
end
