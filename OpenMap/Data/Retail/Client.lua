-- Which client this toc is for: its data is in Data\Retail and its textures in Media\Textures\Retail
-- (Core.lua's ns.Media.tex). Each client's toc loads its own Client.lua first.
-- Written by hand (not generated): what about retail's maps the map code can't read from the game.

local _, ns = ...
ns.Client = "Retail"

ns.ClientMaps = {
	-- Retail's Azeroth holds twelve continents, so a zone is about half as wide on it as on WoW Forever's
	-- (Elwynn Forest: 0.033 of the world's width, against 0.078): the layers' fades, set by how much of
	-- the world is in view, go by twice the zoom (WorldMap.lua's DetailK), so each comes in on a zone
	-- the size it does there
	zoom = 2,
	-- the cities under the surface, whose minimap shows the surface (Stitch.lua): Undercity, Ironforge
	underground = { [90] = true, [87] = true },
	cityFadeOf = {},            -- (no city of retail's comes in sooner than the rest: Stitch.lua's CITY_FADE_OF)
	cityMiniOf = {},            -- (nor has less of the minimap over it: Close.lua's CITY_MINI_OF)
}
