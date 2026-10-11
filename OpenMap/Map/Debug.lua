--------------------------------------------------------------------------------
-- The debug overlay, for chasing lag: a small panel in the map's top-right corner with the
-- frame rate, each frame's time as a moving graph (a hitch shows as a spike), the worst
-- frame of the last two seconds, what OpenMap's own updates cost (the zoom update, the
-- close-up update) and how many of the art's textures are drawn. /openmap debug, or the
-- menu's Tools. It measures the game's frames while the map is open; its own cost is small
-- (one bar a frame, the text twice a second, the texture count once a second).
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local L = ns.L

mod.defaults.debugOverlay = false

local BARS = 120                -- frames in the graph
local GRAPH_MS = 50             -- the graph's height, in ms (a taller frame is clipped, and red)
local W, H = 240, 40            -- the graph
local WORST_WINDOW = 2          -- seconds the "worst" covers

local map, sc, panel
local bars, times = {}, {}
local cursor = 0
local textAt, countAt, drawn = 0, 0, 0

local function Color(ms)
	if ms <= 1000 / 55 then return 0.3, 0.85, 0.35 end   -- (60 fps, near enough)
	if ms <= 1000 / 30 then return 1, 0.8, 0.25 end
	return 1, 0.3, 0.25
end

-- the sum of the zoom update's parts (S.SetZoom, smoothed per part)
local function ZoomMs()
	local total = 0
	for _, st in pairs(S.zoomSteps or {}) do total = total + (st.ms or 0) end
	return total
end

local function Update(_, elapsed)
	local now = GetTime()
	local ms = elapsed * 1000
	cursor = cursor % BARS + 1
	times[cursor] = { now, ms }
	local bar = bars[cursor]
	bar:SetHeight(math.max(1, math.min(H, ms / GRAPH_MS * H)))
	bar:SetColorTexture(Color(ms))
	-- the newest bar's neighbour is the oldest: a gap shows where the graph wraps
	bars[cursor % BARS + 1]:SetColorTexture(0, 0, 0, 0)
	if now < textAt then return end
	textAt = now + 0.5
	local worst = 0
	for _, t in pairs(times) do
		if now - t[1] <= WORST_WINDOW and t[2] > worst then worst = t[2] end
	end
	if now >= countAt then
		countAt = now + 1
		drawn = mod.IsStitched() and S.DrawnCount and S.DrawnCount() or 0
	end
	local fps = GetFramerate()
	local cv = S.closeView or {}
	local _, _, zoom = mod.ViewNow()
	panel.fps:SetFormattedText("|cff%s%.0f fps|r  %.1f ms   worst %.0f ms", fps >= 55 and "4cd959" or fps >= 30 and "ffcc40" or "ff4d40",
		fps, fps > 0 and 1000 / fps or 0, worst)
	panel.ours:SetFormattedText(L["OpenMap: zoom update %.1f ms, close-up %.1f ms (worst %.1f)"], ZoomMs(), cv.ms or 0, cv.worst or 0)
	panel.art:SetFormattedText(L["zoom %.1f, %d textures drawn, %d minimap tiles"], zoom or 0, drawn, cv.tiles or 0)
end

local function Build()
	panel = CreateFrame("Frame", nil, map)
	panel:SetSize(W + 16, H + 58)
	panel:SetPoint("TOPRIGHT", sc, "TOPRIGHT", -8, -36)   -- (under Blizzard's buttons in that corner)
	panel:SetFrameLevel(math.min(sc:GetFrameLevel() + 9450, 9970))
	ns.Look:Panel(panel, { alpha = 0.8 })
	local function Line(y, template)
		local fs = panel:CreateFontString(nil, "OVERLAY", template or "GameFontHighlightSmall")
		fs:SetPoint("TOPLEFT", 8, y)
		fs:SetWidth(W)
		fs:SetJustifyH("LEFT")
		ns.Look:Font(fs, 11)
		return fs
	end
	panel.fps = Line(-6)
	ns.Look:Font(panel.fps, 12, "OUTLINE")
	panel.ours = Line(-22)
	panel.art = Line(-35)
	local graph = CreateFrame("Frame", nil, panel)
	graph:SetSize(W, H)
	graph:SetPoint("BOTTOMLEFT", 8, 6)
	local bg = graph:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(0, 0, 0, 0.35)
	-- 60 fps and 30 fps lines
	for _, ms in ipairs({ 1000 / 60, 1000 / 30 }) do
		local line = graph:CreateTexture(nil, "ARTWORK", nil, 1)
		line:SetColorTexture(1, 1, 1, 0.18)
		line:SetSize(W, 1)
		line:SetPoint("BOTTOMLEFT", 0, ms / GRAPH_MS * H)
	end
	local bw = W / BARS
	for i = 1, BARS do
		local t = graph:CreateTexture(nil, "ARTWORK")
		t:SetWidth(math.max(1, bw - 0.3))
		t:SetHeight(1)
		t:SetPoint("BOTTOMLEFT", (i - 1) * bw, 0)
		t:SetColorTexture(0, 0, 0, 0)
		bars[i] = t
	end
	panel:SetScript("OnUpdate", Update)
	panel:Hide()
end

function mod:IsDebugOverlay() return mod.db.debugOverlay and true or false end

function mod:ToggleDebugOverlay(on)
	if on == nil then on = not mod.db.debugOverlay end
	mod.db.debugOverlay = on and true or false
	if panel then
		wipe(times)
		panel:SetShown(mod.db.debugOverlay)
	end
	if mod.RefreshPanel then mod:RefreshPanel() end
end

function mod:SetupDebug(worldMap)
	map, sc = worldMap, worldMap.ScrollContainer
	Build()
	panel:SetShown(mod.db.debugOverlay)
end
