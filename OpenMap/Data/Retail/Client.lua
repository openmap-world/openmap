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
	-- Retail's maps are painted whole, as Blizzard has drawn them since the Cataclysm: the world's and each
	-- continent's art paints its own sea and every coast, and a zone's base art is the whole zone (its
	-- explored-area pieces are the same art again). So the stitched map is that art as it is (Stitch.lua):
	-- no sea of OpenMap's under it (sea = false: the world and continent art stay as Blizzard painted them,
	-- never muted to it), no explored-area pieces drawn over the zones' art (overlays = false), and the
	-- world and continent art drawn only near the view (cullBackdrop: thousands of tiles at 3840 x 2560)
	sea = false,
	overlays = false,
	cullBackdrop = true,
	-- its continents' art is four to eight times as fine as WoW Forever's (3840 x 2560, a continent half
	-- as wide on the world), so it carries the zones much further in: they come in later, where its
	-- pixels run out (Stitch.lua's DETAIL_FADE, in the zoom above), with no faint hint of them before
	detailFade = { 6, 9 },
	detailHint = false,
}
