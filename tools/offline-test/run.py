"""Offline load test: runs OpenMap's toc in a stubbed WoW environment (Lua 5.1).

Usage:  python tools/offline-test/run.py [plain|combat|secret]
Needs:  pip install lupa

Loads every toc file, fires ADDON_LOADED / PLAYER_LOGIN / combat events, runs
timers, builds + validates the options table and calls every option getter,
then runs the slash commands. "secret" makes combat values behave like the
client's secret values. Exit code 1 on any error. (The stub has no real world
map, so the stitched map itself isn't built here: check that with
tools/map-preview and in game.) Stubs can't catch nil-tests on secrets or layout problems: always
confirm in game.
"""
import os, re, sys
import lupa.lua51 as lupa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "OpenMap"))

def toc_files():
    out = []
    for line in open(os.path.join(ROOT, "OpenMap.toc"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.extend(expand(line.replace("\\", os.sep)))
    return out

def expand(rel):
    path = os.path.join(ROOT, rel)
    if rel.endswith(".xml"):
        base = os.path.dirname(rel)
        files = []
        for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', re.sub(r'<!--.*?-->', '', open(path, encoding="utf-8").read(), flags=re.S)):
            files.extend(expand(os.path.join(base, m.group(2).replace("\\", os.sep))))
        return files
    return [rel]

L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute(open(os.path.join(HERE, "stub.lua"), encoding="utf-8").read())
ns = L.eval("{}")
load = L.eval("""function(src, name, ns)
    local fn, err = loadstring(src, "@" .. name)
    if not fn then return false, err end
    local ok, e = xpcall(function() return fn("OpenMap", ns) end, function(m) return tostring(m) .. "\\n" .. debug.traceback() end)
    return ok, e
end""")

failed = False
for rel in toc_files():
    if not os.path.exists(os.path.join(ROOT, rel)):
        print("SKIP (missing)", rel); continue
    src = open(os.path.join(ROOT, rel), encoding="utf-8-sig").read()
    ok, err = load(src, rel, ns)
    if not ok:
        failed = True
        print("LOAD ERROR", rel, "\n", err)

steps = L.eval("""function(ns, scenario)
    FireEvent("ADDON_LOADED", "OpenMap")
    FireEvent("PLAYER_LOGIN")
    FireEvent("PLAYER_ENTERING_WORLD", true, false)
    RunTimers(3)
    if scenario == "secret" then ENABLE_SECRETS() end
    if scenario == "combat" or scenario == "secret" then
        IN_COMBAT = true
        FireEvent("PLAYER_REGEN_DISABLED")
        RunTimers(3)
        IN_COMBAT = false
        FireEvent("PLAYER_REGEN_ENABLED")
        RunTimers(3)
    end
    local ACR = LibStub("AceConfigRegistry-3.0")
    local ok, err = pcall(function() return ACR:GetOptionsTable("OpenMap", "dialog", "AceGUI-3.0") end)
    if not ok then ERRORS[#ERRORS + 1] = "options: " .. tostring(err) end
    if ok then WalkOptions(err, {}, {}) end
    for _, cmd in ipairs({ "status", "paint", "news" }) do
        local ok2, e2 = pcall(SlashCmdList.OPENMAP, cmd)
        if not ok2 then ERRORS[#ERRORS + 1] = "slash " .. cmd .. ": " .. tostring(e2) end
    end
    RunTimers(2)
end""")

L.execute(r'''
function WalkOptions(node, path, inherited)
    local inh = {}
    for k, v in pairs(inherited) do inh[k] = v end
    for _, k in ipairs({ "get", "set", "disabled", "hidden", "handler" }) do
        if node[k] ~= nil then inh[k] = node[k] end
    end
    local info = { options = node, option = node, type = node.type, handler = inh.handler, uiType = "dialog", uiName = "AceGUI-3.0", appName = "OpenMap" }
    for i, p in ipairs(path) do info[i] = p end
    local function call(field, ...)
        local v = node[field]
        if type(v) == "function" then
            local ok, err = pcall(v, info, ...)
            if not ok then ERRORS[#ERRORS + 1] = "option " .. table.concat(path, ".") .. " " .. field .. ": " .. tostring(err) end
            return err
        end
        return v
    end
    call("name") call("desc")
    local function callInh(field, ...)
        local v = inh[field]
        if type(v) == "function" then
            local ok, err = pcall(v, info, ...)
            if not ok then ERRORS[#ERRORS + 1] = "option " .. table.concat(path, ".") .. " " .. field .. ": " .. tostring(err) end
        end
    end
    callInh("hidden") callInh("disabled")
    local values = call("values")
    if node.type and node.type ~= "group" and node.type ~= "header" and node.type ~= "description" and node.type ~= "execute" then
        if node.type == "multiselect" and type(values) == "table" then
            for key in pairs(values) do callInh("get", key) end
        else
            callInh("get")
        end
    end
    if node.args then
        for k, child in pairs(node.args) do
            local p = { unpack(path) } p[#p + 1] = k
            WalkOptions(child, p, inh)
        end
    end
end
''')

steps(ns, sys.argv[1] if len(sys.argv) > 1 else "combat")
print("INSPECT", L.eval("""(function()
  local m = OpenMap.modules.worldmap
  local P = OpenMap.MapPlaces or {}
  local reveal = 0 for _ in pairs(OpenMap.MapReveal or {}) do reveal = reveal + 1 end
  return "enabled=" .. tostring(m and m.enabled) .. " revealArts=" .. reveal .. " instances=" .. #(P.instances or {}) .. " docks=" .. #(P.transports or {})
end)()"""))
errs = L.eval("ERRORS")
n = len(errs)
seen = set()
for i in range(1, n + 1):
    e = errs[i]
    key = e.split("\n")[0]
    if key in seen: continue
    seen.add(key)
    print("ERROR:", e[:1500]); print("-" * 60)
logs = L.eval("LOG")
print("log lines:", len(logs), "| errors:", n, "| unique:", len(seen))
for i in range(1, min(len(logs), 40) + 1):
    print("  LOG:", logs[i])
sys.exit(1 if (failed or n) else 0)
