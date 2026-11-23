# OpenMap changelog

## Unreleased

### Fixed

- **Place names whole in other languages** (#377): where two zones meet, a name longer than the English one
  went under the zone next to it ("Acampamento Taurajo" lost its first letters under Mulgore, and "Fortaleza
  da Guardanorte" and "Platô do Vigia dos Céus" didn't show at all, on the Brazilian Portuguese client), and
  one at a zone's edge faded with it ("Charco de Lodo" at the Barrens' top). Each zone's names now stay whole
  over its neighbours, in the 20 zones where that happened. Done for Brazilian
  Portuguese so far (it needs that language's art). By cscoder69.
- **A capital's name banner whole over its map in other languages**: on a client not in English, the city's
  own map, coming in as you zoom, covered the zone's banner for it (Thunder Bluff showed only the last
  letter of "Penhasco do Trovão"). The banner is now drawn over the city in your language, and goes as you
  close in, as it does in English. By cscoder69.
- **No bits of neighbours' names in other languages**: a zone's map letters its neighbours' names round its
  land, and the map leaves those out, but only as long as the English ones. The longer names showed their
  ends ("Flo… P…" of "Floresta de Pinhaprata" by Tirisfal, "Eira dos Montes", "Floresta do Crepúsculo",
  "Estepes Ardentes"). They're now left out whole, in 33 zones, for Brazilian Portuguese so far. By cscoder69.
- **Orgrimmar's map fades out at its gate**: up close, the city's map ended in a straight line across the
  foot of its gate, where its art stops. It now fades out inside the art's edge, as Ironforge's does. By
  cscoder69.

## v0.8.13 (2026-11-22)

### Fixed

- **Places you've explored show on the map**: the map read what you'd explored as it was built at login,
  maybe before the game had sent it, and then only when the game said something new was explored. It reads
  it again as the map first opens and after you enter a new subzone (#422, #410).
- **No lag zooming with Show places to explore on**: every zone you'd looked at kept its outlines, thousands
  of lines laid out again on every frame of each zoom and pan, nine times the map's own. Only the zones in
  view and a few recent ones keep them now (#411, #413, #419).
- **No stack overflow as the map closes** with Show places to explore on and Keep warm (#414).
- **Places to explore count what you've already explored**: it read the map's own record, which can be from
  before the game sent your exploring after login; it asks the game now, and again as you explore (#417,
  #418, the Barrens showed 3 of 25).
- **The map's art ready before it opens, in more cases** (keep-warm round you, v0.8.12): the art round you
  is warmed again each time the map closes (closed on another place, the next opening, centred on you,
  came in cold); in a cave or another small map its zone is warmed (nothing was); and in a big zone its
  own art comes first, the farther tiles last (they filled the 400 files and left it out). By cscoder69.
- **The map closed in a fight reopens where you left it**: it reopened on the view from before the fight.
- **Opening the map after you've moved is lighter with Show places to explore on**: only zones where you've
  explored something since are drawn again, not all of them.

### Improved

- **Close-up map performance**: with minimap detail on and unexplored areas hidden, the map
  draws fewer masked fragments and skips the ones outside the view. By benjaminrobinet.
- **Supporting OpenMap**: the foot of What's new's Credits page has a link to copy, for those who'd like to.

### Known issue

- Opening the map in a fight can print "Interface action failed because of an AddOn" once a session. It's
  harmless: the map, the quest log and the tracker all work; only the quest log's controller navigation
  marks are skipped for that one refresh.

## v0.8.12 (2026-11-21)

### New

- **Show places to explore** (the map's menu and Options, off until turned on): for each zone's Explore
  achievement, the places you haven't explored yet, each with a soft gold outline of the ground that
  explores it (read from the game's own terrain) and a pin where to go; its tooltip names the place and
  the achievement's progress. Further out, each zone shows how many places it has left.

### Improved

- **The map works in a fight**: since v0.8.11 the map stood still in combat (the game's map can't be moved
  by an addon then without breaking the quest tracker, #345). In a fight OpenMap's map now moves onto frames
  of its own, over the game's, which is left as it is: zoom, drag, click and resize it as usual, with your
  arrow, your party and raid, your quests and their areas, the name of the place under the cursor, Questie's
  and other addons' map icons, and Ctrl-click's waypoint. As the fight ends it all goes back on the game's
  map, where you left it (#386, #389). (New files: restart the game after updating, a /reload isn't enough.)

- **Unexplored land darkens as one, the same at every zoom** (Unexplored areas: Darken): in a zone you've been
  to, the unexplored parts were darker where the game's map pieces overlap, a different shade once the
  minimap's detail came in, and could jump between the two as you zoomed. Each piece's share of the darkening
  is now worked out ahead of time so that, whichever pieces you've explored, the rest come to one even shade,
  drawn over the map and the minimap alike (#317). By wealdly.

- **German reads better**: missing German texts filled in and others reworded, in the game's own terms.
  By gOOvER.

- **Right-click can be left to other addons**: Options' "Right-click zooms out" (on, as before) turned off
  leaves right-click on the map to the map and other addons, such as Questie's objectives (#117).

- **Colour matching says what it costs**: below 100% the ready-made zone tiles aren't used, and its
  description now says so (#29).

- **The map's art ready before it opens**: the art round you is read in while the map is closed, a few
  files a frame and out of combat, once the map is built after a login or a /reload and again when you
  reach a new zone. At a session's first opening, and after travelling, it used to come in over a moment
  (the files held from the last opening were another place's, or none). The part of the view still
  fading in as you closed the map is held too. By cscoder69.

- **The game's map-pin button works on the stitched map**: armed, a click on the map drops your pin there,
  as on the game's own map (#324). By gOOvER.

- **Your arrow, bigger if you like**: Options' "Arrow size" (100% as before) and "Your arrow over
  everything", which lifts OpenMap's arrow over every icon on the map (#329). By gOOvER.

### Fixed

- **No stutter when the map opens**: since v0.8.11 every set of icons was laid out twice as the map opened,
  for the whole world and then for your view; once now, as in v0.8.10 (#293, measured by protella: the
  opening 384 ms to 45).

- **A resized window keeps its view**: since v0.8.11 dragging the window's corner zoomed the map out to the
  whole continent; the place you were looking at stays put now, at the same scale.

- **Your position read safely everywhere**: the map, dungeon entrances, flight routes and the controller view
  all read where you are the same careful way, so a hidden position in combat or in a restricted instance
  can't raise a Lua error. By gOOvER.

- **A dungeon's map fills the screen when maximized**: going from the quest log (L) to the maximized map (M)
  inside a dungeon left its map small in the middle (#297). By gOOvER.

- **The Stockade's entrance opens its map**: clicking it found neither the game's dungeon map nor its
  Dungeon Journal page (#289). By gOOvER.

- **A map window saved off the screen comes back**: dragged out of reach, it opens where Blizzard puts it
  again (`/openmap reset` does the same at any time) (#375).

- **No Lua error from the cursor's coordinates** over a part of the map with no zone of its own, as on
  retail's maps outside the stitched world (#343).

- **Explored land keeps its detail up close with Hide unexplored areas**: zoomed in where the minimap's
  detail comes in, land you'd explored near an unexplored part (Redridge, Tarren Mill and others) got the
  painted map back over it, as if unexplored. Only the unexplored parts' own shapes are hidden now
  (#166, #156, #163, #247, #279, #370).

- **Appear Offline keeps your place to yourself**: with Battle.net's Appear Offline on, OpenMap sends your
  friends and guild nothing (not your place, not even a hello), and tells them to stop showing where you
  were (#395).

- **Questie's quest icons over a town's icons**: a quest under a vendor, trainer or flight master's icon
  was hidden; Questie's quests now go over every icon of OpenMap's (#393).

- **No "newer OpenMap" notice from test builds**: a test build or a beta no longer tells others it's a newer
  version; only releases do.

- **The windowed quest log sits beside the map**: it covered part of the map until the window was laid out
  again; and a window resized by its corner stays on the screen (#327). By gOOvER.

- **The right wing's map in Dire Maul, Scarlet Monastery and Blackrock Spire**: the wing is worked out from
  the dungeon finder and the area you're in, or the portal you came through, and kept over a /reload; Dungeon
  Journal is told it too. By puschie286.

- **Ctrl-click left to the game is followed**: with "Ctrl-click drops a pin" off, the game's own waypoint was
  set on the map underneath (often the continent's), where the game has no route to it, so it was never
  followed; it's put on the zone under the cursor now, at the cursor, and followed (#19).

- **Coordinates clear of the border full screen**: the labels sat under Blizzard's border at the map's
  bottom edge when the map was maximized (#399).

## v0.8.11 (2026-11-20)

### Improved

- **Told when a newer OpenMap is out**: when a friend, guild member or group member has a newer release,
  a line in chat says so, once a session ("OpenMap X is out (you have Y). Update through CurseForge.").
  Your version rides only on messages OpenMap already sends them (the hello to friends who use it, your
  first shared place to your guild, a pin share to your group); older copies pass over it. Options' "Say
  when OpenMap has an update" turns it off, and then your version isn't sent either.

- **"The game's map" on a dungeon's map**: inside a dungeon, a button at the top of OpenMap's dungeon map
  switches to the game's own map there, and says how to turn OpenMap's back on (menu > Dungeons) (#371).

- **A smoother map on a Russian client**: the zones' art from further out is drawn from tiles baked
  from the ruRU client's own maps, place names and city banners in Russian, as on an English or a
  Brazilian Portuguese client (it was every zone's art drawn live). (New textures: restart the game.)
  By Danpiel.

### Fixed

- **The quest tracker keeps working in combat with OpenMap**: clicking a tracked quest, or opening the map,
  in a fight gave "Interface action failed because of an AddOn", and the objective tracker then stopped
  updating until you collapsed and opened it again. OpenMap no longer puts its own code in place of the
  game's map functions (it runs after them), and changes nothing of the game's map in a fight: the map
  opened in combat is the game's view of it, and OpenMap's comes back as the fight ends (#345, #347, #368).

- **Forever City Labels' pins show on the stitched map**: its service, profession and class trainer pins
  were drawn under OpenMap's art. By marquesm91.

- **No more green squares over the map** where the game can't find OpenMap's map tiles (not installed,
  or the game not restarted since an update): such a tile is left out, and with several missing the map
  is drawn without them. `/openmap status` says how many (#349, #353).

- **Translations of the ClassicUI Forever question read right again**: in every language they showed as
  garbled letters (Ð’ ...).

- **Quest icons show the quest's level on every map**: zoomed out, or over the next zone, OpenMap's own
  quest icons had only the quest's name on their tooltip. They now read as Blizzard's own quest icons do,
  with the level and its difficulty colour ("[39+] The Crown of Will"). By Rambomst.

- **Sharper at the middle zooms**: between a continent and a zone filling the view, the zones' art was
  drawn from tiles stretched past their pixels for a while; the zones' own art takes over sooner now.
  And unexplored land no longer flickers as the zones' art comes in while you pan. By wealdly.

- **Roogug where he is now**: in Razorfen Kraul he stands in the middle of the dungeon past the rope
  bridge (needed for the warriors' Fire Hardened Mail); his pin was at his old spot (#318).

- **With Soften on, unexplored land stays darkened up close**: from Soften's zoom until the minimap came
  in, a partly explored zone's unexplored land went nearly bright, and flickered back each time the map
  moved. By wealdly.

- **The controller map opens where you set it**: with the Gamepad UI, "When reopening the map"
  (center on you, keep the zoom, your zone, remember) was only used the first time the map opened;
  after that it opened wherever it was last left. It's used every time now.

- **Place names under the controller's cursor**: the zone (with its levels) or the area under the
  cursor is named at the top of the map, as it is under the mouse. Blizzard's own label, which named
  places on its map hidden under OpenMap's, is hidden while OpenMap's map is up.

- **Quest areas on the controller map**: pointing at a quest's icon shades its area, as Blizzard's map
  does for its own icons, and the area stays in place while zooming. The focused quest's icon is
  Blizzard's gold one, and its area stays shown when the cursor isn't on another quest. By kr0ozin.

### Also

- I've also made OpenGroup, a group finder that shows groups from every shard. It's in beta and gets more useful the more people use it. Search OpenGroup on CurseForge.

## v0.8.10 (2026-11-16)

### Fixed

- **The map loads again for everyone**: for some players since v0.8.9 the map opened blank, with an
  error about GetMapInfoAtPosition. A view worked out while the map was still 0 px across (a divide
  by zero) was put into the map, and every view after it was worked out from it, so the map stayed
  blank. A view that isn't one is never put up now, the map's last view and its saved window place
  and size are checked as they're read back, and a bad one is forgotten (#260, #261, #263). The cause, found
  by OlehPetrykUA: v0.8.9 put the map together during its very first build, before it had a size.

- **Fewer hitches zooming out**: the first zoom out of a session made the lettering of every continent
  and sea name (hundreds of font strings) in one frame; one name is made a frame now. And the tiles
  fading in as you zoom out set their opacity in 8 steps instead of on every frame, a third to a half
  fewer calls to the client for a zoom out. By k4m1.

- **No more flight paths at Eastern Plaguelands' towers**: Plaguewood, Northpass, Eastwall and Crown
  Guard Tower are in the game's flight tables, but no character can learn them and no flight master
  stands there; they're left out (#264).

- **A dungeon you've been inside counts as found** ("Only places you've found"): Blackfathom Deeps'
  entrance, under the Zoram Strand's water, never showed, done or not. Counted from your next visit (#256).

- **A quest from the quest log shows its map with "Center on player, keep zoom"**: in your own zone
  the map opened at the kept zoom on you, the quest off screen; it shows the quest's map whole now, as
  with the other choices (#255).

- **The zone highlight toggle works again**: with it off, zones could still glow under the cursor, where
  the game made its highlight after OpenMap set the map up (#262).

- **The map in combat**: opened, zoomed or panned in a fight, the map no longer comes up stretched,
  half empty and see-through until the fight ends. The game can refuse OpenMap's zoom then (the map
  holds the group members' protected icon); the map is now drawn at the zoom the game kept, and the
  one you asked for is put up as the fight ends. The window is no longer moved, sized or scaled in a
  fight either (each was an "action blocked"): that waits for the fight's end too (#294). By Vennomfang.

- **ClassicUI Forever**: its World map option lays the map window out itself every frame, so
  OpenMap's resize corners and title bar did nothing, and in a fight parts of the map went missing.
  OpenMap now asks once whether to turn that option off (a reload). Kept on, OpenMap's corners, title
  bar and saved place stand down and leave the window to it.

- **Stuck on a dungeon's map**: inside a dungeon, Esc closed the whole map, and it opened on the
  dungeon again, never the world. Esc (out of combat), a right-click and Back now go to the world map
  around the dungeon's entrance (or your last place outdoors), and another addon laying the window out
  again no longer throws the map back to the dungeon.

- **Your settings kept**: for some players every setting went back to its default at each login since
  v0.8.9. A broken number from the blank map (#261) was saved with them, which the game can't read back,
  so the whole file was lost; such a number is never saved now (#306).

- **"Share where you are" off means off**: your place could still go out once, queued just before you
  turned it off or in answer to a friend's hello at that moment. Nothing is sent now while it's off;
  friends and guild see only your zone, as the game's own lists show it (#277).

- **Learned flight paths are this character's**: a new character was shown flight masters another
  character had learned, and a learned one could show as not learned. Once you've opened a flight
  master's map on a character, what it lists is what counts (#274, #301).

- **Mount Hyjal's two flight masters** (Summit of Eternity, Tainted Foothills) are on the map (#288). And
  the wind riders shown at Eastern Plaguelands' towers, where there are none, are gone (#307, #309).

- **Learned flight masters in green**: they were your faction's icon, red for the Horde, which read as
  not learned. They're the game's flight map green now, greyed where not learned.

- **The world map reopens where you left it inside a dungeon**: with any reopen choice but Always
  remember, browsing the world map in a dungeon and opening it again went back to the whole continent
  each time. With nowhere to centre on, it reopens where you left it now.

### Improved

- **A dungeon's map never covers your quest log**: beside the quest log it always opens on your quests;
  the dungeon's panel shows only when you pick its tab. And **dungeon maps inside dungeons can be turned
  off** (Options and the menu's Dungeons): off, the map opened inside a dungeon is the game's own there; a
  dungeon's map still opens from its entrance. The first dungeon you're in says once where that switch is.
  With Dungeon Journal or NeedRoll installed, their map is left to them inside a dungeon (#302, #267).

- **Sharp map by default**: Soften and paper grain is off for everyone (turn it back on in Look > Up close).
  It softened the map a moment after it stopped moving, sharp while zooming or panning, which read as the
  map going blurry (#286, #118). Its tooltip now says so.

- **The game's own frame rate limit while the map is open**: v0.8.9's 60 fps cap held the whole game at
  60 while the map was open, below what many had set. It's off by default again (set once back to off
  for everyone who had 60); the Map frame rate cap is still there to turn on (#273).

- **Faster loading**: the stitched map is no longer built during the loading screen. It's built a few
  seconds after it, a few milliseconds a frame (not in combat), so the map is ready by the time you open
  it; opened sooner, the rest is built then. By Vennomfang.

- **A smoother map on a Brazilian Portuguese client**: the zones' art from further out is drawn from
  tiles baked from the ptBR client's own maps, place names and city banners in Portuguese, as an English
  client's has been (it was every zone's art drawn live: panning at mid zoom took about half the frame
  time). Other languages draw it live as before, until their own tiles are baked. (New textures:
  restart the game.) By cscoder69, with thanks to developer-felipe, whose #265 took this on first.

- **Less work while the map is closed**: the guild and friends lists are read at most every 30 seconds
  (a raid's roster changes came each time), exploring somewhere recolours the map's art the next time
  it opens rather than then, and another addon loading no longer looks through every global table
  again.

- **Smoother panning and zooming**: darkened unexplored land lets go of zones out of view (they were
  laid out on every frame, more the more of the world you'd seen), and of a zone's old shading when
  it's made again; the boat and zeppelin routes' finer dots are hidden, not only faded, from afar; the
  continents' names rest their outer glow while the map moves; and the close-up minimap, the cursor's
  place name and the coordinates skip work when nothing has changed. By cscoder69.

- **Smoother with the map open**: "Quests from every zone" asked the game for the quests of every zone
  and city in a single frame, half a second after each opening and again after each burst of quest log
  updates while the map was open (and once more after it closed). The zones are now read a few a frame
  and the icons put up together once all are in; nothing is read while the map is closed.
  `/openmap status` says what the last reading cost. By Merryfett.

## v0.8.9 (2026-11-14)

### New

- **Hide world markers in instances** (the menu's On the map tab, and Options; off unless turned on):
  in dungeons, raids and battlegrounds, OpenMap's friends, guild, transport and all-zone quest markers
  step aside. With Dungeon maps off and another addon's dungeon map shown over the world (NeedRoll's),
  the world under it stops answering the mouse, and a right-click brings the world map back, at the
  dungeon's outdoor entrance (#232). By HonzoNebro.

- **Pin options** (OpenMap's options, Moving about and Sharing):
  - **Follow new pins**: on by default, as before. Off, a pin you drop doesn't become the waypoint,
    so addons that route to it (Shortest Path Forever) are left alone; the pin's Follow still sets it.
  - **Send new pins to group**: a pin you drop goes to your party or raid once its card is closed.
  - **Auto-add group's pins**: pins your party or raid shares are added without asking.
    By diegodiaz1256.

- **A map of Blackmaw Hold**, drawn by Santiago Reyes: all six of its floors, from Blackmaw Grove
  and the Festering Grotto down to the Depths of Forbidden Magic (the floor list at the top of the
  dungeon's map, or its arrows). (New textures: restart the game.)

### Improved

- **City of Dalaran's map is Santiago Reyes's updated version, with the Underbelly**, where the
  dungeon starts, as a second floor (#220). Opened inside the dungeon, the map shows the floor
  you're on.

- **Shaper's Terrace's map is Santiago Reyes's final version, with the Prismatic Talus** as a
  second floor.

- **The controller view's switch in the map's menu too**: "OpenMap's map with the Gamepad UI (test)"
  is under The map in OpenMap's menu as well as in Options (it was only in Esc > Options > AddOns,
  and a player took it for gone).

- **Questie's quest icons in front**: a "!" or "?" is no longer hidden under a flight master or a
  dungeon's icon; Questie's townsfolk stay under OpenMap's icons (#92).

- **A word about MapUtils**: with MapUtils on, OpenMap says once in chat that the two both change the
  map's zoom, which made the map and Blizzard's quest areas jump while zooming (#160).

### Fixed

- **One arrow for you, not two**: where OpenMap draws your arrow itself (the map underneath can't
  place you), Blizzard's arrow now steps aside, so the two no longer show a little apart (#229).

- **Quests from the tracker open on their details**: the first click on a tracked quest opened the
  map on the quest list; it shows the quest's text now (#224).

- **The map cooler on your graphics card**: OpenMap's "Map frame rate cap" is now 60 by default (and
  set to 60 once for everyone): a still map was drawn as fast as the card could go (#233). Turn it off
  in Options if you'd rather.

- **Fade while moving fades while you steer with the mouse**: the hidden cursor's last place over the
  map held it solid, so it hardly ever faded (#69).

- **Resizing the window keeps it where it is**: it could jump to the screen's bottom left (#241).

- **Nighthaven's flight master shows for druids only**, as only druids can fly from it (#222).

- **The controller view takes the mouse too** (OpenMap's map with the Gamepad UI): the wheel zooms,
  a drag pans, and a click works as A (left) or X (right) (#234).

- **City names in your language**: Thunder Bluff's and Darnassus' name banners showed in English on
  other languages' clients; the zone map's own banner, in the client's language, is shown there now (#47).

- **Your quests' icons show in the controller view** (Options' "OpenMap's map with the Gamepad UI"):
  there were none, and no tooltips. Every quest in your log is now OpenMap's icon there, at any zoom,
  in every zone (with "Quests from every zone" off: the zone Blizzard's map is on); A tracks the quest
  and zooms to it. The "!" of quests you can start in that zone are there too, with the quest's name
  on the tooltip. The shaded quest areas aren't on it yet (#225). By k4m1.

- **Zygor's map line stays thick on the stitched map**: Zygor's route line (and its dots and waypoint
  icons) shrank to a thin grey line zoomed in and grew far too wide zoomed out, as Zygor sizes them for
  Blizzard's zoom range; they now stay the same size on screen at every zoom (#218). By rogeriocamorim.

- **Gilneas shows on every language's client**: on the Russian and Latin American Spanish clients
  Gilneas was a solid green square, as the game doesn't have its map's art in those languages (as
  with the dungeon and cave maps before v0.8.5). OpenMap now brings those tiles itself (#152).
  Found and tested by XaksFlaX. (New textures: restart the game.)

- **Dungeon level ranges**: the dungeons' levels on the map are now the ones the game's Group Finder
  gives (each Scarlet Monastery and Dire Maul wing its own); they were an old level each, five levels
  wide, and some were far off: Razorfen Kraul showed 24-29 for a dungeon of 29-38 (#201). By ConfusionOrb221.

## v0.8.8 (2026-11-13)

### Fixed

- **Party and raid markers stay steady**: one marker per member, moving smoothly. OpenMap's ring now
  follows Blizzard's own dot where the game places a member, instead of a second dot of its own that
  lagged behind it; elsewhere OpenMap's dot keeps its highlight and tooltip as it moves. The ring is
  now a thin gold edge (the wide one round a dark gap read as a target: #158, #170). By puschie286.

- **Friends on the map: your own faction only.** Your place is only shared with, and shown from,
  players of your own faction: Battle.net friends on the other faction no longer see where you are, nor
  you them (a player's report: it let Horde and Alliance find each other for PvP).

- **Friends in another realm group show on the map**: a friend on CAMWOW US1 and one on US2 (or EU4 and
  EU5) never saw each other with "Share where you are" on (#164, #167).

## v0.8.7 (2026-11-12)

### Fixed

- **Questie's icons show on the first map you open**: with Questie 12.8, a map opened on a zone showed
  none of Questie's icons (their tooltips still came up) until you'd zoomed out to the continent once:
  icons Questie placed before the map was first opened stayed under its art (#194, #193, #195).

## v0.8.6 (2026-11-12)

### Improved

- **Icons stay shown while zooming**: "Fade icons while zooming" is now off for everyone, as zooming is
  smooth enough with them shown; turn it on again in the menu's On the map tab if you prefer it.

### Fixed

- **Questie's icons show again with Questie 12.8**: Questie 12.8 brings its map icons a new way (its
  own module, with a new name), which OpenMap didn't know, so they were left off the map; and each icon
  Questie drew again sank under the map's art, so they faded away one by one. Older Questie versions
  work as before (#18). With bv101rj.
  Questie 12.8 hides its objective icons (mobs to kill, items to loot) until you turn them on: /questie,
  Icon Options, Objectives.

## v0.8.5 (2026-11-12)

### New

- **OpenMap's map with a controller** (the game's Gamepad UI; a test, off until you turn it on in
  Options: "OpenMap's map with the Gamepad UI (test)"): the seamless map with the Gamepad UI on, where
  OpenMap leaves the world map to Blizzard. OpenMap draws its map over
  Blizzard's and leaves Blizzard's map as it is, so the controller's buttons keep working and closing
  the map with B is no longer blocked. The left stick moves the cursor (at the edge it pans), the right
  stick zooms about it, A zooms into a zone or presses the icon or button under the cursor, X zooms
  out or closes what's open, and pressing the left stick puts the waypoint there. On it: dungeons,
  boats, flight masters and their routes, your pins and the waypoint, your party, Questie's icons
  (with their tooltips), townsfolk and mob paths, other addons' icons (TomTom, gatherers), dungeon
  maps with their bosses, quests and loot, and the OpenMap menu with search, Find me, map pins, the
  quill (A puts the pen down, A lifts it) and Report a problem. Questie's icons no longer slow the map
  down there either. The D-pad's right opens the quest log, as on Blizzard's map. Off (the default):
  Blizzard's map with the Gamepad UI, as before. If you play with a controller, try it and tell us
  how it goes (#57). By FlyingPenguin98.

- **WoW Forever's newest dungeons on the map**: Krol'dok Stronghold, Alcaz Prison, Blackmaw Hold and
  Shaper's Terrace have their entrance pins (#142), and they and The Drowned City list their bosses.
  By puschie286.

- **Reopen the map on your zone** (the menu's More tab, Reopen map: "Center on your zone"): the map
  opens on the whole zone you're in, in the middle, wherever you stand in it (#143).

### Fixed

- **Ragefire Chasm shows with "Only places you've found"** once you've found Orgrimmar: an entrance
  inside a city is found with the city, whose own map has nothing to explore (#113).

- **The Drowned City's map opens inside it**: opening the map in one of WoW Forever's own dungeons
  that the game's tables didn't list yet (The Drowned City, Krol'dok Stronghold, Shaper's Terrace) showed
  the world map instead of its drawn map. With puschie286.

- **"Darken unexplored areas" keeps its soft edges up close**: once the minimap's detail shows, the
  shade was hard-edged rectangles, and it changed as the minimap came in; it now has each unexplored
  area's own shape, as further out (#101, #129).

- **Cave maps whole**: Blizzard's cave maps showed only the parts their pale floors give away, cut off
  along a straight line near the page's foot (Maraudon's entrance, Wailing Caverns', Night Web's
  Hollow ...); the caves' own rooms now say where they are, as was meant (#141).

- **No white diamonds at cave mouths**: one of the game's own cave minimap pictures has a white block
  baked in over its tunnel's mouth, which showed up close at two caves in the Hinterlands (and one in
  Kalimdor); OpenMap now draws a mended copy (#114).

- **/openmap forgetflights** forgets the flight paths OpenMap remembers as learned for the character,
  for one counted wrongly (route planners read the list); the next flight master's map learns the
  real ones again (#153).

## v0.8.4 (2026-11-11)

### New

- **Bosses pinned on dungeon maps**: a numbered pin where each boss is, on its floor, numbered as
  the Bosses tab lists them, with its name on the tooltip (click: its loot in NeedRoll). Placed from
  Blizzard's own dungeon journal for 153 bosses so far; "Dungeon maps: bosses" turns them off with
  the list (#90, #93).

- **/openmap bosses places the rest yourself**: on a dungeon's map, click where the boss named in
  the bar is (right-click skips one, shift-click takes the last back). Your places show at once and
  are kept with your settings.

- **Dungeon maps from the minimap** (Options, off): a dungeon's map built from the game's own
  minimap pictures of its rooms, a picture per floor, instead of its drawn map: The Hall of Thanes
  and Ruins of Lordaeron for now.

### Improved

- **Your party and raid get a gold-bordered dot** on the stitched map, everywhere, so they can't be
  mistaken for a guild member's dot. Someone the game won't place is shown faintly in the middle of
  their zone, with "Somewhere in" on the tooltip. By KonigTX.

### Fixed

- **"Your arrow" off also hides the yellow location ping** when the world map opens or changes
  zones. Turning it on again restores the normal arrow and ping; party markers stay visible (#78). By Luquatic.

- **"Party and raid members" off means off**: Blizzard's own blips for your group are hidden too,
  not only OpenMap's dots (#77, found by Luquatic).

- **Dragging the map no longer zooms into a zone or city**: a drag that came back near where it
  started counted as a click and zoomed into what was under the cursor, Ironforge from parts of Dun
  Morogh most of all (#37, #64).

- **Guild markers clear when a guildmate joins your group**: their shared-location dot or zone
  badge entry could stay when the guild roster and the party spelled the character's name
  differently. By puschie286.

- **"Ctrl-click drops a pin" off leaves Ctrl-click to other addons**: with it off, a Ctrl-click zoomed
  the map and went no further, so Map Pin Enhanced's own Ctrl-click did nothing (#19).

- **One map marker per friend or guildmate**: different realm labels could make the same
  character count twice in a zone badge or show more than one shared-location dot (#104, #115). By
  puschie286.

- **No flight master at Powderfuse Port**: the map showed one there, but there's none in the game
  yet; the port is reached by its boat, which stays on the map (#121, #132).

- **Map size in OpenMap's menu is greyed out with Move Any**, as it is in Options: Move Any sizes
  the map then, and the menu's slider moved without changing anything (perhaps #136).

## v0.8.3 (2026-11-09)

### New

- **Turn off OpenMap's dungeon maps** (Options and the menu's On the map tab): off, clicking an
  entrance shows its card over the world map, and opening the map inside a dungeon shows the world
  map, so another dungeon map addon (NeedRoll, Dungeon Journal ...) can show its own. By ZiiMs.

- **Friends and guild each have their own switch**: keep your friends on the map and hide a big
  guild, or the other way round. A save with the old single switch off turns both off. By ZiiMs.

- **Map brightness** in the Look tab: dim the whole stitched map, including explored areas and the
  sea, while player and quest icons stay bright. 100% keeps the original look (the default). By
  forcedroidbrain.

- **A launcher for Titan Panel** and other LibDataBroker displays: it works like the minimap
  button (click: the map with its menu; right-click: the options window). By Naladdar.

### Improved

- **The settings menu can be resized**: drag its bottom-right corner to make it wider or shorter,
  double-click the corner to reset it. Long labels (German, the nearby zones settings) wrap
  instead of running into the next column, and the settings scroll when they don't fit the screen,
  instead of the whole menu shrinking. By Naladdar.

- **The map window can be resized with Move Any**: Move Any still places and scales the window,
  and OpenMap's corner grips set its width and height. By Naladdar.

- **Clicking a quest's icon on the windowed map shows it in the quest log**: the quest log beside
  the map opens if it was closed, with the quest's details, as well as tracking the quest and
  zooming in on it. (On the full-screen map a click still tracks and zooms only.)

- **A dungeon map remembers its tab**: picking Quests beside the quest log keeps it picked the next
  time a dungeon's map opens.

### Fixed

- **No more dot in the bottom-left corner of the screen** after closing the map, or inside a
  dungeon: the map art OpenMap keeps loaded while the map is closed was drawn there, hundreds of
  faint copies on one pixel. Found by ryanull24.

- **Friends on other numbered realms show on the map**: Forever's numbered realms of one pool
  (Realm4, Realm12 ...) count as one realm, so a friend there shows like a friend on yours. They
  were left out as if on another realm. By TheRayoX.

## v0.8.2 (2026-11-08)

### Improved

- **Panning no longer hitches**: the map set up to 300 textures' files in a single frame where a
  pan brought new ground into view, and each set is a load and an upload, so that frame showed as
  a hitch of about 35 ms. It sets 60 a frame now; the art still fades in, a few frames later.

### Fixed

- **The map no longer stalls a moment after it opens**: since 0.8.0 OpenMap keeps the map's art
  loaded while it's closed, then let go of it all in one frame a second into the opening, which the
  game unloaded at once (about a second's freeze). It now lets go of it a little at a time.

- **Zooming in notch by notch is smooth again**: since 0.8.1 the blur came back all at once each
  time the map stopped, one long frame the next wheel notch landed on. It now waits out a pause
  between notches and comes back a few zones a frame. Questie's mob paths are worked out once the
  map stops, not on every frame of a zoom.

## v0.8.1 (2026-11-08)

### New

- **Questie's mob paths on the stitched map**, drawn over the art for the zones near the view as
  you zoom in (Questie's own were under the art, and only on the zone's own map).

- **Darkening colour** (Options, under Darkening): the colour unexplored areas are darkened with,
  picked with the game's colour picker; **Default colour** brings back the dark one.

### Improved

- **Zooming is about four times smoother**: OpenMap no longer lays out its hidden icons and its
  blur on every frame of a zoom (the blur comes back a moment after you stop). Found and measured
  by Peendars.

- **Flight masters are easier to see on the map**: bigger, with a dark outline, and the ones you
  haven't learned are no longer half see-through (they were lost on the parchment).

- **Ctrl-click drops a pin can be turned off** (Options, and the menu's More tab): with Map Pin
  Enhanced a Ctrl-click dropped two pins, its own and OpenMap's. Off, the menu's Drop a pin still
  works.

- **The Drowned City's map is Santiago Reyes's updated version**, which names more of its places
  (the Eternal Amphitheater and the Abyssal Dais).

### Fixed

- **Dungeon and cave maps show in every language**: on the Latin American Spanish, Russian and
  Italian clients every dungeon map and Blizzard cave map was solid green squares, as the game
  doesn't have their art for those languages. OpenMap now brings that art itself. Found and
  first fixed by RADD95 (OpenMap TextureFix): with this version that addon isn't needed.
  (New textures: restart the game.)

- **Zone names in your client's language**: on every client but English, the zones' prebuilt
  art lettered their English names over the map. Other languages now draw the zones from the
  client's own art (zooming is a little slower there, as with that art turned off).

- **Questie's icons show the first time you open the map**: after a login they could be missing
  until the map was closed and opened again (Questie was still setting up when OpenMap looked).

- **Zygor's waypoint shows on the stitched map**, in the right place and over the art (Zygor uses
  its own renamed copy of HereBeDragons, which OpenMap didn't know). Traced by robnoord.

- **Your class's trainers are found on every language's client**: on a French client (and the
  other non-English ones) every class trainer showed as a profession trainer.

- **An NPC who walks about shows once on the map**: Girl with Puppies in Orgrimmar had a vendor
  icon at every point of her walk, dozens over the city. An NPC with many spawns in one zone (with
  Vendors and the other townsfolk on) now has one icon, in the middle of where it walks. Fixed by
  diegodiaz1256.

- **The map opened on Zephras Isle shows Zephras Isle**, as its airship opens it: it showed the
  stitched world with no one on it.

- **No friends dot or badge for yourself**: with Share where you are on, you could show on your
  own map as a guild member (the guild's roster can spell your realm differently).

- **The map opens at once inside a dungeon**: each opening loaded the dungeon's map art again, a
  second or two (longer in dungeons with many floors, whose Floors tab shows every floor). OpenMap
  now keeps the art of the dungeon you're in loaded, as it does the world map's.

## v0.8.0-beta (2026-11-07)

### New

- **Friends and guild on the map** (Options: Friends and guild): your guild members and friends on
  your realm who are online show on the stitched map, a badge on the zone each is in with who's there. Those who use
  OpenMap and turn on **Share where you are** show as a class-coloured dot where they stand, updated
  every few seconds while they move. The map asks once whether to share; it's off unless you say yes,
  goes only to your guild and your friends, and never from inside a dungeon, raid or battleground.
- **Maps of The Drowned City, Krol'dok Stronghold and Shaper's Terrace**, drawn by Santiago Reyes and
  used with his permission (credited on the map, as his other dungeon maps are).

### Improved

- **A new OpenMap icon, drawn by zloyeb**: a map scroll in a gold ring, in the AddOns list, on the
  minimap button, in the map's menu and its portrait (it borrowed the game's Eastern Kingdoms icon).
- **OpenMap is back on GitHub**, at github.com/openmap-world/openmap: Report a problem opens a
  report there again, and What's new and the AddOns list link to it.

### Fixed

- **"Center on player, keep zoom" opens at your zoom straight away**: having moved since the map
  closed, it opened on the zone's whole map for a moment and then jumped to the zoom kept.
- **The map opens with its art already there**: the game let go of the map's art while it was
  closed, and each opening loaded it again (blank parchment for a moment). OpenMap now keeps it
  loaded while the map is closed; `/openmap warm` turns that off.
- **The map closes in combat again**: with the map open as a fight started, neither Escape nor M
  closed it (since 0.7.0). The windowed map no longer stays open beside an NPC's window, which is
  what blocked it.
- **Flight masters you haven't learned show as not learned**: every one showed as learned, as
  WoW Forever reports them all as found. OpenMap now goes by the ones a flight master shows you've
  learned: what it remembered is forgotten once and counted again at the next flight master you talk to.
- **The map window can't go above the top of the screen**, where its title bar couldn't be
  grabbed to bring it back. `/openmap reset` puts the window back to its size and place.
- **Dun Morogh stays Dun Morogh near Ironforge**: around Kharanos, panning or zooming switched the map
  to Ironforge's and a click zoomed into the city. A city's map now takes over only in its middle,
  and its zone comes first when you click your way in.
- **The OpenMap menu fits a short screen**: on a TV at a big UI scale the Look tab ran off the
  bottom.
- **Flight masters are named in your own language**: on a client that isn't English, the map's
  flight masters kept the game's tables' English names (hovering one said "Stormwind, Elwynn" while
  the flight master in game names it in your language). They're now named as the game names them,
  and a flight's measured time is found again on a route (the times were keyed by the English names).
- **The map opened inside a dungeon shows that dungeon's map** (Ragefire Chasm, Deadmines ...): it
  showed the world map with no one on it, as WoW Forever has no map of its dungeons. Its map only
  opened from the entrance on the world map.

## v0.7.5-beta (2026-10-23)

### Fixed

- **The map's art is there at once when you open it**: since 0.7.4 the zones showed blank parchment
  for a moment each time the map opened.
- **Clicking a quest on the map keeps the map as it is**: the quest is tracked and the map zooms in on
  it, full screen or windowed. It opened the quest's details, which Blizzard shows in the windowed
  map, so a full-screen map left full screen. With the quest log open beside the map, its details
  show there too.
- **Hiding your pins hides their drawings too** (the menu's Pins, right-clicked): what you drew on a
  pin stayed on the map without it.

## v0.7.4-beta (2026-10-23)

### New

- **Chat over the full-screen map** (the menu's Look tab, and Options): the chat windows stay on show
  over the map while it's full screen, to keep talking while you look. Off unless you turn it on (a
  player's request).
- **Faster to load**: only your language's translations are read (the other nine were a quarter of
  OpenMap's code), and its look through every addon's map icons for combat waits till you're in the
  world, not the loading screen (a player's report: half a second more load time).
- **The zones' detail comes in sooner** when the map first opens up close: it took a couple of
  seconds after a login or reload.
- **`/openmap status` says what loading costs**: OpenMap's files, the login, the map's setup and
  building the map (a player found it added load time: this shows where).

## v0.7.3-beta (2026-10-22)

### New

- **Key bindings** (the game's Keybindings > OpenMap): Find me, Drop a pin, Pins, Quill,
  Quest log and the map's menu, each opening the map first if it's closed (players' requests).
- **The quill draws on dungeons' maps**: with a dungeon's map up, what you draw goes on its picture
  and is kept with that dungeon, not on the world map behind it (a player's request).
- **Only places you've found** (the menu's On the map tab, under Places): dungeon entrances, docks
  and zeppelin towers once you've explored where they are, flight masters once you've learned them.
  Off unless you turn it on (a player's request).
- **Townsfolk from another addon's NPC database**: an addon with a database in Questie's shape can
  give it to OpenMap (`OpenMapAPI.RegisterTownsfolkProvider`, docs/api.md), so townsfolk and rare
  mobs show without Questie (a player's request).

### Fixed

- **Smooth zooming at any Take colour out**: the zones' fast pre-drawn art was only used at the
  setting's default (10%); at any other, every zone was drawn from its hundreds of pieces and the
  frame rate dropped as their detail came in. It's now used at every setting.
- **Full screen stays full screen**, and the quest log you closed stays closed, the next time the
  map opens: it went back to the window and the quest log each time (a player's report).
- **Improves performance** under Fade icons while zooming no longer stays on show over the menu's
  other tabs (a player's report).
- **Riverglades and Zephras Isle show their levels** on the zone hover (35-45 and 1-12, from the
  Warcraft Wiki; a player's report).

## v0.7.2-beta (2026-10-21)

### Improved

- **Zooming is smoother with unexplored areas darkened**: greying the land you haven't found cost
  a lot of frame rate while zooming; it now costs far less.
- **Unexplored areas for one character only**: the menu's **Only for this character**, under
  Unexplored areas, gives this character its own choice (darkened, hidden or shown); every other
  character keeps the shared one (a player's request).
- **Fade icons while zooming** says **Improves performance** under it in the map's menu, so it
  isn't turned off unawares.

### Fixed

- **The map loads the zone you pan or zoom to again**: with an addon adding map icons (Questie,
  GatherLite ...), it could stay on the zone you started on, so the zone or continent you'd panned to
  showed none of their icons until you clicked it (a player's report from 0.6, and ours). Its setting,
  once Follow the view, is now **Load the zone in view** (the menu's More tab), saying what it does.
- **The map window drags and resizes with Move Any installed but turned off**: OpenMap asked whether
  Move Any was on for a character named by your first name alone (WoW Forever gives a first and last
  name), which the game took as on, and left the window to it (a player's report, with the fix).

## v0.7.1-beta (2026-10-21)

### Improved

- **Darkened unexplored areas look better** (Unexplored areas: Darken): a **Darkening** slider (the
  menu's sliders, and Options) sets how dark they are, from a light shade to the full one; unfound
  land is greyed as well as darkened, so the lighter lines Blizzard paints along zones' borders no
  longer show bright through it; neighbouring zones you haven't found blend into one another, with
  no light seams between them, and the painted land between zones (north of the Plaguelands,
  Gilneas, round Ahn'Qiraj ...) darkens with them.
- **Other addons' icons fade while you zoom** (Questie's, RestedXP's ...), out as a zoom starts and
  back in after it, instead of blinking off and on. **Fade icons while zooming**, in the map's menu
  (the Show tab), turns it off.
- **The map window can go partly off the screen**: drag it up until its title and the bar under it
  are past the top, for just the map (Options' Reset window brings it back), or past the sides and
  bottom while some of it stays on.
- **With Enhance QoL**, OpenMap says once in chat to turn off its Mover > World Map: the two both
  size the map, and its scale goes wrong (a player's finding).

### Fixed

- **Other addons' icons stay on the map** (RestedXP's, Nauticus's, Questie's ...): they could
  flicker and go, as anything that set the map's scale counted as zooming. Now only your own
  zooming does, and never for more than a moment.
- **Flight masters you've learned are in colour**, all of them: OpenMap knew only the ones it had
  seen you visit since it was installed (and, on a client not in English, none). It now asks the
  game which you've found.
- **Fishing on the zone hover** shows: OpenMap looked for your Fishing skill in a way WoW Forever no
  longer offers, and found none.
- **Zeppelin towers show for the Alliance too** when Zeppelins is on: they were the Horde's only,
  though their routes showed for everyone and the goblins' zeppelins take anyone.

## v0.7.0-beta (2026-10-20)

### New

- **Fishing on the zone hover**: if you know Fishing, hovering a zone shows the skill at which every
  cast there lands (Elwynn Forest 25, Hillsbrad Foothills 150, Stranglethorn Vale 225 ...), green if
  you have it, yellow if most casts land, red if most get away. With **Zone levels**, from the
  original game's values; WoW Forever's own zones have none yet.
- **Shortest Path Forever from anywhere on the map**: Shift-click a spot in another zone, on
  another continent or zoomed right out over the whole world, and its journey is planned there. Its
  own Shift-click only reached the map underneath (the zone or continent you were last zoomed into).
- **NeedRoll opens where you click**: a boss in a dungeon's Bosses tab opens NeedRoll on that boss's
  loot (Shift-click: where the boss is, on NeedRoll's map of the dungeon), and a quest in the Quests
  tab opens its page there; the Loot tab's button opens the dungeon's own loot. Dire Maul's, Scarlet
  Monastery's, Stratholme's and Blackrock Spire's wings open on the right one. Needs NeedRoll's
  newest version (thanks to its author, mikebvs, for the links).

### Improved

- **Choose your map**: the choice the first time the map opens is in the map window's own frame,
  with plainer words.
- **The map stays open while you talk to an NPC** (or open a vendor, the bags' windows ...): the
  windowed map is no longer put away to make room. Escape still closes it; maximized, it behaves as
  before.
- **Reopen map: Center on player, keep zoom** (the menu's Reopen map, and Options): the map opens
  on you at the zoom you closed it at.

### Fixed

- **Ironforge's map shows once you've been there**, even if you came by the Deeprun Tram and haven't
  found the land round it yet. With unexplored areas hidden, the city counted as found only once you'd
  explored the part of Dun Morogh over it; now going into a city finds it too.

## v0.6.0-beta (2026-10-18)

### New

- **Responsive ocean & border** (Options, and the map's menu): zoomed right out, the world map lies
  on a sea chart painted by Santiago Reyes (used with his permission), laid out for your window's
  shape: the sea, compass roses, sea creatures, ships and the frame's corners round it, each in its
  place whether the window is wide, square or tall. The game's own world map stays in the middle,
  fading into his sea. Zoom out past the whole world to see all of it; the map pans to its edges and
  no further. Off unless you turn it on. Its frame is the map's only border now: the parchment
  border and its setting are gone, so with this off the map has none.
- **OpenMap in your language**: German, French, Spanish (Spain and Latin America), Italian,
  Portuguese (Brazil), Russian, Korean and Chinese (Simplified and Traditional), with the game's own
  words for things (flight masters, map pins, the quest log ...). Place names were already the
  game's. What's new's notes stay in English.
- **Your quests from every zone, at any zoom**: Blizzard's map shows a zone's quests only once
  you've zoomed in on that zone; now the quests in your log show across the whole map, in the look
  of Blizzard's (in progress or ready to turn in, their objectives on hover; click one: it opens in
  the quest log). The menu's **Quests from every zone** turns them off.
- **Every cave underground**: the caves, mines, tunnels, crypts, dens and dungeon entrances Blizzard
  drew no map of (about 250 of them; it drew 39) surface as you zoom in on them too, as the game's
  own minimap draws them inside, lying as they do: Fargodeep's neighbours, Dun Algaz's tunnel, the
  troll and kobold caves, the ogre mounds, Razorfen Kraul's, Blackfathom's and Onyxia's Lair's
  entrances, and WoW Forever's own new caves and vaults.
- **Ten more gaps painted**: the blank land between zones is painted by hand by Santiago Reyes
  (used with his permission) round Tanaris and Silithus, the Plaguelands, Stonetalon and the
  Barrens, Silverpine and Hillsbrad, Thousand Needles and Feralas, Winterspring and Darkshore,
  Ashenvale and Azshara, Stranglethorn and the Blasted Lands, Thousand Needles and Dustwallow
  Marsh, and Desolace and Feralas. Their coasts are his own coastlines, fading out into the sea.
  Khaz Modan's comes back sharper, from his full-size painting.
  Options' **Filled gaps** turns them all off.
- **Map pins into chat**: Shift-click a pin (on the map or in the Pins list) to put it in chat, as
  Blizzard's map pin link where the game takes one (whoever clicks it gets the waypoint), with its
  note; else its note, zone and position as text.
- **Clearing map pins**: the Pins list's **Clear** deletes every pin (it asks first), and Alt-click
  deletes one at once, on the map or in the list.
- **Hiding your map pins**: right-click **Pins** (in the OpenMap menu, or its button on the map) and
  your pins leave the map, the button greyed while they're away; right-click again for them back.
  The Pins list still has them all, and dropping a new pin brings them back.
- **Mailboxes** in the menu's Townsfolk (from Questie's list of them, as its own map shows them).
- **Icon size** (the menu's sliders, and Options): OpenMap's icons on the map bigger or smaller.
- **Credits** (What's new's **Credits** button): who has made OpenMap, Santiago Reyes's painted
  maps, Ironship's and C-Clymer's work on the code, Blizzard's art, the libraries, and everyone who
  reports problems and ideas.

### Improved

- **Smoother zooming with Questie**: other addons' map icons (Questie's, TomTom's ...) rest while
  the map zooms and come back as soon as it stops. Each was laid out again on every frame of a zoom,
  which with Questie's hundreds cost a lot of frame rate. Options' **Other addons' icons rest while
  zooming** keeps them up.
- **In combat, fewer "action blocked" errors** from the map's own icons: the super-trackable ones
  (quests, points of interest) wait out combat to set their clicks, as the rest already did, and
  addons loaded later are covered too. Other addons' icons lifted over the map (Leatrix Maps',
  Azeroth Tripview's, Books on Map Forever's) are lifted as combat ends, not during it.
  **RareScanner's** rare icons show over the map (they were under its art). A map addon with a
  HereBeDragons OpenMap can't take over is said once in chat, not passed over. Thanks to Ironship.
- **Questie's icons across the view**: zoomed out over a zone, the quests of every zone in view show,
  not only those of the zone underneath and the next one.
- **Shortest Path Forever works on the map**: Shift-click the map to plan a journey (OpenMap's
  click-to-zoom took every click first).
- **The map opens no further in than the deepest zoom**: centred on you in a city, it opened as far
  in as the city's map fits (up to half again past the setting, and blurry past the art's own pixels).
- **The menu's buttons on the map come off with Shift-right-click** only, not a plain right-click.
- **For other addons**: `OpenMapAPI.CursorPosition()` (API version 3), the point under the cursor;
  with `MapAt`, the zone under it at any zoom, so a zone-hover tooltip (Zonewise's) can keep working
  zoomed in, where the map underneath is the zone, not the continent.
- **The Pins list** can be dragged anywhere and stays where you put it. Sharing every pin is one
  **Share all** button with a menu (as a code, to your group, to your guild), so sending them all to
  your guild is never one stray click.
- **The minimap's detail over Orgrimmar and Thunder Bluff** as over the other major cities (up to
  half strength; it was held to 15% there, which hardly showed). **Minimap detail in major cities**
  (the menu's Up close, and Options) turns it off over all six.

### Fixed

- **With a controller (the game's Gamepad UI), OpenMap leaves the world map to Blizzard.** Closing
  the map with B said "OpenMap has been blocked from an action only available to the Blizzard UI"
  (and Disable on that message could crash the game). The Gamepad UI sets the controller's buttons
  again on every map change, and on OpenMap's map those changes run as OpenMap's code, which the game
  then blocks from closing the map. Until OpenMap can work with the Gamepad UI without that, it says
  so once in chat and stays out of the map while the Gamepad UI is on; swap to mouse and keyboard and
  OpenMap's map is back.
- **The minimap's detail follows unexplored areas.** Zooming in, it drew over land you haven't
  explored as it is: on Hide, Moonglade, the land round Ironforge or Hillsbrad looked explored
  straight away; on Darken, the unexplored parts of zones you've been to came up undarkened. Up
  close, unexplored land is now blank parchment (Hide) or darkened (Darken), the minimap's detail
  with it, as from further out; on Hide a cave under it stays underground.
- **Santiago Reyes's coastline round Silithus and Ahn'Qiraj.** His painting leaves its sea clear, and
  past his coast, where the game's own map has land, the map's blank paper showed through: an orange
  band down Silithus's and Ahn'Qiraj's west coast in place of his shallows. His shallows and the ink
  line he draws off the shore show now, there and round every painted gap's coast.
- **Santiago Reyes's mountains south of Hyjal at full strength.** Between Felwood, Ashenvale and
  Azshara, his painting of the land below Mount Hyjal looked washed out, its mountains faint ghosts on
  blank paper up to a straight line under Hyjal's map. The zones' blank parchment from the sheet he
  painted on had been left over his finished painting there; it shows now as he painted it.
- **Caves come up at the usual deepest zoom.** A cave's map surfaced only once it nearly filled the
  view, which at the default deepest zoom (48x, where a mine is a speck) most never could: clicking
  a dungeon entrance glided in and stopped short of it. Over a cave the zoom now goes on past the
  deepest setting until its map fills the window, and a cave comes up as it fills a quarter of it.
- **Blizzard's cave maps show their whole cave.** Their outlines were traced from the maps' pale
  floors and lost darker rooms and passages' ends: Night Web's Hollow's great chamber, Burning Blade
  Coven's west loop, Ban'ethil Barrow Den's lower tunnel and more. They're traced now from where the
  caves' own rooms lie in the game, leaving out only the page's title ribbon and corner knots.
- **The map window resizes by its corners again.** OpenMap put the window back to its saved size
  in the middle of a drag; now the drag sizes it, the map staying where it is on screen as more or
  less of it comes into the window, and the drop lays it out at that same scale, with no jump.
- **Townsfolk without Questie**: they come from Questie's database, so without Questie the menu
  says so instead of offering switches that showed nothing, and turning one on says so once in chat.
- **Zones' edges against the sea and the painted gaps.** A zone's own map is drawn whole to its
  frame on land, so its coasts and mountains no longer fade out early into an orange band of blank
  land (Arathi's east coast) or a grey smudge of sea (Arathi's mountains above the Wetlands); where
  it paints the sea up to its frame, the sea fades in from the frame instead of stopping in a
  straight line (Eastern Plaguelands' east coast). Mountain strokes mistaken for a printed name no
  longer cut holes in a zone's map (the brown blot at Thoradin's Wall), and past its own land a zone
  gives way to Santiago Reyes's painted gaps where they reach.
- **Ironforge's map whole up close.** The Mystic Ward, the Forlorn Cavern, the Hall of Explorers and
  the Gates were faded out into the mountain: the city's map faded out in a round from its middle,
  and Ironforge's wards reach right out to its frame. It's cut to the city instead, as the
  Undercity's is, with Dun Morogh's mountain round it.
- **Ironforge's minimap detail up close.** Zooming in on Stormwind brings in the game's minimap;
  on Ironforge only the painted map showed: the game's minimap there, outside, is the mountain over
  the city, so OpenMap kept it off. Now the game's own minimap of the city inside (what your minimap
  shows walking through it) comes in over Ironforge's map as you zoom in, as the minimap does over
  Stormwind; the Undercity's too.
- **The Wetlands' Excavation Site stays hidden until you've found it.** With Unexplored areas on
  Hide, the painted mountains south of Whelgar's Excavation Site showed WoW Forever's new valley
  there (green, with paths and a lake) before you'd been anywhere near it. It's blank parchment now
  until you've explored Whelgar's Excavation Site or Angerfang Encampment, the parts of the
  Wetlands' map over it (the game itself keeps no record of exploring the valley), close up too; on
  Darken it's darkened until then.
- **Fade while moving** faded for a moment and then came back: the game's own map fade (held off
  while OpenMap's runs) kept setting the map back to full on every frame you moved. OpenMap's fade
  now stays.
- **Map size** in the map's menu ran away as you dragged it: it scales the window the menu is in, so
  the slider moved under the cursor. The size now changes when you let go.
- The continents' names lost their glow each time you zoomed and flickered back on: they keep it now
  (the seas' names still rest theirs while the map moves, which keeps zooming smooth).
- Blizzard's quest areas trailed the map as you zoomed and sprang back when you stopped: each is
  now drawn where the map is at that step.
- **Quests from every zone** follow the map's own **Quest Objectives** switch: with it off, OpenMap's
  quest icons go too, as Blizzard's do.
- The menu's **Minimap button** row has its icon (it showed none: the icon it named isn't in the
  game).

## v0.5.0-beta (2026-10-16)

### New

- **Khaz Modan's blank land painted**: the stretches between Dun Morogh, Wetlands, Loch Modan,
  Searing Gorge and the Badlands that no zone map covers, and the coast round them, painted by hand
  by Santiago Reyes in the zone maps' own style, from Blizzard's art and following the game's
  terrain (used with his permission). The first of the gaps between zones to be filled; Options'
  **Filled gaps** turns them off.
- **Maps of City of Dalaran and Excavation Site: Wetlands**, drawn by Santiago Reyes and used with
  his permission: click their entrances in Alterac Mountains and the Wetlands (they opened on a blank
  page before). "Map by Santiago Reyes" at their foot, as with his others.
- **Airships to Zephras Isle**: the flying boats at the Dalaran skydock (Alterac Mountains) and in
  Mulgore are on the map; click one and Zephras Isle's map opens in the window, as a dungeon's does,
  and Back takes you to the world where you were. (Under the Boats switch.)
- **Maps of Ruins of Lordaeron and The Hall of Thanes**, two of WoW Forever's own dungeons, which
  the game has no map of: drawn by Santiago Reyes and used with his permission. Click their
  entrances in Undercity and Ironforge; the map shows "Map by Santiago Reyes" at its foot.
- **Dungeon Journal**: with Exehn's Dungeon Journal installed, a dungeon's map has **Open in Dungeon
  Journal** on its Bosses tab, and clicking an entrance can open its page there instead of its map
  (the menu's **Entrances open Dungeon Journal**, or Options). Its map still opens where Dungeon
  Journal has no page for it.
- **Dungeon quests without Questie**: the Quests tab works with Dungeon Journal or NeedRoll too, as a
  button that opens the dungeon's quests in it. With more than one installed, Options' **Dungeon
  quests from** picks which (the first installed: Questie, then Dungeon Journal, then NeedRoll).
- **The OpenMap button off the map, if you like**: **OpenMap button on the map** (the menu's Look tab)
  hides it and the favourites. The menu is still a click away: OpenMap is in the minimap's AddOns
  list, and there's a **minimap button** if you want one (the Look tab, or Options). Click for the map
  and its menu, right-click for the options window, drag it round the minimap; /openmap works too.
- **A choice the first time the map opens** on a new install: **Classic** (unexplored areas
  hidden, no dungeon or flight master icons, no zone levels, the favourite buttons folded away) or
  **OpenMap** (as it comes). Settings you already have aren't asked about or changed;
  /openmap welcome asks again. Suggested in #24.
- **Your arrow on top, or off**: the player arrow is drawn over every other icon on the map (quest
  givers, Questie's and other addons' icons), so you can always see which way you're facing
  (suggested in #31); your party's markers come up with it. Or take it off the world map (the menu's
  Show tab, **Your arrow**) and find your way old-school by the land around you: your party still
  shows, and so does the minimap.
- **Icons from zoom**: a slider (the menu's Look tab, or Options) for the zoom the icons for places
  (dungeons, boats, zeppelins and flight masters) show from: 1x has them from the whole world, higher
  keeps the map clean further out. Auto, as before, brings each in at its own zoom. Townsfolk never
  come in further out than their own; your pins, drawings and party always show.
- OpenMap shows under a **Map** category in the game's AddOns list.

### Improved

- **Map frame rate cap** (the menu's Look tab, or Options; off unless you set it): the frame rate at
  most while the map is open. A big map draws many layers over the whole screen every frame; at 60
  the graphics card does about half the work it does at 120 (reported: a full-screen 4K map doubling
  the card's power). Your own frame rate setting comes back as the map closes.
- Up close, a layer of the paper grain that has faded out is no longer drawn.
- **Report a problem** sends you to OpenMap's comments on CurseForge for now, to post its code in
  (What's new's link goes to OpenMap's CurseForge page too).
  Its window, and the bench's and the map notes' to copy from, are in the map window's own frame.
- **Dungeons, boats and zeppelins each have their own switch** in the menu's Show tab and in
  Options, so you can keep dungeon and raid entrances and hide the boats or zeppelins. A kind that's
  off takes its routes with it when routes are shown. Your old setting carries over to all three.
- **Out of a city to its zone**: right-click out of Stormwind, Ironforge, Darnassus, Orgrimmar,
  Thunder Bluff or Undercity and the map goes out to the zone around it (Elwynn Forest, Dun Morogh
  ...), as it does from anywhere else in that zone, not the whole continent.
- **Azeroth Tripview**: its live ships and docks are kept above the map's art. For other addons,
  OpenMapAPI (version 2) can now place a point of the game's world anywhere on the stitched map,
  for frames they put on the world map themselves (docs/api.md).

### Fixed

- Zooming in quickly, the zones no longer flicker to blank parchment for a moment: the map's
  pre-drawn tiles now stay until every zone coming into view has its art in.
- Opening a dungeon's map no longer can raise a Lua error the first time (when the map window
  changed size as it opened, as in full screen).
- **With a gamepad**: the cursor stays where you put it. It jumped back to the middle of the map
  each time the map underneath changed (shortly after every zoom or pan), so the next zoom was about
  the middle. And in combat, a dungeon's or Zephras Isle's map waits until you're out of it (a line
  in chat says so): opened then, the game set the map's gamepad buttons again in a way it blocks in
  combat, which could leave them wrong until a /reload.
- **WoW Forever's boats** are on the map, with their docks and routes: Steamwheedle Port (Tanaris)
  to Powderfuse Port (Riverglades), for both factions; Stormwind to Auberdine; and Menethil Harbor
  to Southshore and Auberdine, which takes the place of the old Menethil to Auberdine boat.
- **WoW Forever's flight masters**: Farholde Keep and Powderfuse Port for the Alliance, Rog'mar and
  Powderfuse Port for the Horde, with their flights (Farholde Keep to Powderfuse Port, Lakeshire,
  Morgan's Vigil and Thelsamar; Rog'mar to Stonard, Kargath, Flame Crest and Hammerfall). The flight
  network now comes from WoW Forever's own tables, which have moved Stormwind's flight master and
  redrawn some of the classic flights.
- **The close-up minimap on towns by the sea and on islands**: Menethil Harbor, Southshore,
  Theramore, Booty Bay's shallows, Teldrassil and Darnassus, Feathermoon Stronghold. It was cut to
  the continent map's coarse outline of the land, which leaves out what that map draws as sea; it
  now takes in each zone map's own land too.
- **No retail Eversong Woods or Zul'Aman over Quel'Thalas**: the minimap is now only the tiles the
  game itself draws (those its own world map file lists), which also leaves out other versions' sea
  far west of Dun Morogh and east of Wetlands, and the Draenei isles off Kalimdor.
- Blizzard's classic maps drawn in the land between zones are placed where WoW Forever places those
  zones. They were placed by Mists of Pandaria Classic's tables, whose zones are Cataclysm's, so
  The Barrens' was drawn at Northern Barrens' size and Stonetalon Mountains', Silithus', Badlands',
  Dun Morogh's and Azshara's were off, showing copies of their mountains beside the real ones.
  Cataclysm's Hillsbrad Foothills (Alterac taken in) and a different drawing of Mulgore are no longer
  used.
- The cave maps of four places WoW Forever doesn't have are gone: Greymane Manor (Gilneas),
  Spitescale Cavern (the Echo Isles as Cataclysm remade them), and Legion's Keeper's Rest and
  Karazhan Catacombs.
- **Books on Map Forever**'s book icons show on the stitched map: they were drawn under its art.
  Which ones show is still the addon's own choice (those of the zone or continent the map is on).
- The zone you're looking at has its name over the map again when you hover it, where the game
  names no place in it (Silverpine Forest's had gone; reported in #25). With Zone levels off, zone
  names still show, without their levels.
- **Move Any** owns the map window: with it, OpenMap's title bar, resize grips and saved place
  stand down, so Move Any's own drag and resize work on the map again (reported in #23). The map
  size slider and Reset size and place are off then.
- A city's own map that went missing (Ironforge showing only Dun Morogh's painting of it, until a
  /reload: reported in #30) is shown again when you reopen the map, and the map's check of what's in
  view no longer stays stuck if it stopped part way. (A safeguard: what hid it isn't known yet.)

## v0.4.0-beta (2026-10-16)

### New

- **Dungeon maps.** Click a dungeon's entrance for its own map, drawn from the game's own art (WoW
  Forever's map never shows it), right in the map window. Zoom with the wheel, drag to pan, and step
  through its floors with the arrows, the floor list or the side panel's Floors tab, which shows each
  floor as a small picture. Where several share an entrance you pick one; Blackrock Spire, Dire Maul
  and Scarlet Monastery are listed by wing, each opening on its own floor. Right-click, Escape or
  Back takes you back to the world where you were. 25 dungeons and raids have maps; WoW Forever's
  own new dungeons open on a blank page until the game has art for them.
- **A side panel for each dungeon**, in the quest log's place and look, as a tab beside the log: its
  floors, its bosses, its quests (with Questie: their level, done or in your log, objectives on
  hover) and its loot, where we recommend NeedRoll by mikebvs (a boss's row opens it). Put the quest
  log away and the dungeon's map has the whole view; the tabs at the map's edge bring the log back.
- **Dungeon entrances** show their level range, coloured for your level (the menu's Level ranges
  hides them). WoW Forever's own dungeons are on the map: City of Dalaran, The Drowned City,
  Excavation Site: Wetlands, The Hall of Thanes and Ruins of Lordaeron so far.
- **Map pins**, as many as you like: Ctrl-click the map (or Drop a pin) for one with a note and a
  colour. Its card follows it (Blizzard's waypoint, and TomTom's), shares it with your group, guild
  or a friend (other OpenMap players are asked first), gives a code to paste anywhere, or deletes
  it. The Pins list (/openmap pins) has them all, for all your characters.
- **The quill:** draw on the map with a pen, lines, arrows, circles and raid marks, in six inks and
  three widths (the menu's Quill, or /openmap draw). Your drawings are kept, and a pin's card can
  draw on that pin.
- **Tabs at the map's edge** for the OpenMap button and your favourites, in WoW Forever's own tab art.
  Drag the OpenMap tab anywhere round the edge; the arrow by it folds your favourites away. "Buttons
  as edge tabs" (the menu's Look tab) puts them back in the corner.
- **Report a problem draws:** in two steps, draw where it's wrong (with the quill, or on a dungeon's
  page), then say what's wrong, for a code to paste into a GitHub issue.
- **When reopening the map:** center on the player (the default for new installs), always restore
  the previous view, or restore it only while you're still in view. Middle-click the map to center
  on yourself at the same zoom. Thanks, C-Clymer (#19)!
- **What's new** in the game, laid out like the quest log: each version's changes, Newer and Older,
  and where to find OpenMap on GitHub.
- **For addon authors:** `OpenMapAPI` (docs/api.md), to place things on the stitched world, hear
  when the view moves or a dungeon's map opens, and add a switch to the OpenMap menu or a section
  to a dungeon's panel.

### Improved

- One place for OpenMap's settings: /openmap (and the game's AddOns settings page) opens the map's
  own menu, now with every setting in three tabs (On the map, Look, More) in the game's own settings
  look. The Look tab's sliders sit in two columns, with Defaults and Reset size and place under them.
- Other addons' map icons placed through HereBeDragons (TomTom, gatherers, notes addons) show on
  the stitched map from every zone in view, and Leatrix Maps' icons show above its art.
- Teldrassil's coast is whole, the great tree's roots all round the island, and Thunder Bluff comes
  in sooner, cut to its plan, under Mulgore's banner for it. (Changed textures: restart the game.)
- Darkened unexplored areas reach all of a zone's land and fade softly at their edges, with no hard
  lines or boxes in zones you've been to; cities you haven't found are darkened (or hidden) too.
  (Changed textures: restart the game.)
- The minimap's detail comes in after the same turns of the wheel in any window, full screen too,
  and a tall or very wide window brings the zones in by how much of the world is in view.
- The map pin's card, the pins list, What's new and the menu's dropdowns have the game's own frames
  and dropdown look; the coordinates are steady black boxes in the bottom-right corner; Find me has
  a crosshair; tooltips say plainly what a click does.
- The quest log's Back (from a quest's details) leaves the map where you're looking. The OpenMap
  menu shows over the quest log and stays put while you drag the map window, and the window's
  bottom-right corner is easier to grab with the quest log open.
- "Reset sliders to defaults" in Options, and Defaults under the menu's sliders.
- OpenMap gives back the game settings it holds: turn off its coordinates and Blizzard's come back,
  and at logout the map fade and coordinates are the game's own again.

### Fixed

- No more "action blocked" errors opening the map (or the quest log updating it) in combat
  (reported by C-Clymer in #19).
- Clicking a quest on another continent opens it at the first click.
- Zooming in on a zone no longer flashes plain parchment between its art from afar and close in.
- The quest log's button stays over the map's parchment border when you zoom right out, and its
  arrows point the way the log goes.
- A click on the window's resize corner without dragging no longer resets the view.
- Closing the map in the middle of resizing or moving it no longer leaves the window following the
  mouse.
- The menu's tabs no longer show another tab's names behind their own, and its search results
  aren't see-through.
- Clearing or replacing a map pin removes its TomTom waypoint.
- A flight route to or from a flight master you haven't learned says so.

## v0.3.0-beta (2026-10-14)

- "Minimap detail from" (a slider in the menu, under Deepest zoom, and in Options' Up close) sets how
  far in the minimap's detail starts to mix in: lower comes in sooner, higher later (20x by default);
  at 1x it's there from the whole world. Further out than the game's own minimap tiles can be
  drawn, smaller copies of them show, crossfading to the tiles as you zoom in. (New textures:
  restart the game.)
- "Minimap opacity" (in the menu too, and Options' "Minimap detail, most opacity"): the most the
  minimap's detail ever shows, at any zoom.
- More coastal and border detail: each zone map now shows everything it paints
  round its own land (the sea off its coasts with its shallows, hatching and islets, the
  mountains and coasts beyond its border), shared out with its neighbours so each place shows
  one painting, handing over smoothly at the maps' frames. Land no map paints is plain
  parchment, which the art fades into, instead of the neighbours' edges blurred across it.
  The zone maps' sea names, their names for the neighbouring zones and their compass roses
  are left out. (Changed textures: restart the game.)
- Improved compatibility with other map addons: they work alongside OpenMap instead of fighting
  it. On the stitched map the art and the view are OpenMap's, and the rest of theirs keeps working;
  their map art shows on dungeon maps as before. At login OpenMap names only the options that
  still clash, not the whole addon.
- Gamepad: on the stitched map the right stick zooms at a steady pace all the way in and out
  (it crawled zoomed in), about the gamepad's cursor; A zooms into the zone under the cursor and
  X out a map, as clicks do, instead of changing the map underneath; the coordinates, the hover
  label, the zone highlight and the boat routes follow the gamepad's cursor. Its cursor shows
  the tooltips of OpenMap's buttons and map icons, and A presses them: the OpenMap button, the
  favourites, the menu (a slider goes to the value under the cursor), the dungeon, flight and
  other icons.
- "Fade unexplored areas" is now "Darken unexplored areas": the land you haven't explored is much
  darker and greyer, instead of faded toward the parchment, and a zone you haven't found at all is
  darkened whole from every zoom, the whole world's too, with the mountains and land round it, so a
  stretch you haven't been to is dark from one zone to the next. Only land is darkened, not the
  sea the zone maps paint round their coasts. (New textures: restart the game.)
- Panning and zooming make far less Lua garbage (OpenMap's view and zoom updates reuse their
  tables instead of making new ones every frame), so the game has less to clear up as you use the map.
- Clicking a quest in the quest log that's in another zone opens it again: the map goes to the
  quest's zone and stays there. It flickered and went back to the list, because the map was put
  back where you'd last closed it. Reopening where you left off now only applies when you open the
  map, not when Blizzard changes the map while it's open (the quest log, the zone dropdown), and
  not when the map opens on a quest's zone from the quest tracker.
- A quest's details in the quest log reach the foot of a window taller than Blizzard's, with more
  room for the quest's text, instead of stopping short with an empty strip under the buttons.
- The OpenMap button is its icon alone, right in the map's bottom-left corner.
- Zoomed in, only the tiles of each zone near the view are drawn and loaded, not every tile of
  every zone it touches, and panning works out what to show only now and then instead of every
  frame (the sea and the paper grain stay put as you pan, too). Less for the game to draw and lay
  out as you move about.
- The zones' art is baked into world tiles (made by a script from Blizzard's map art, as the map
  draws it), so from the continents' zoom in to a zone the map draws a few dozen tiles instead of
  hundreds of masked textures; closer in than the tiles' own pixels, the zones' art is drawn live
  as before. Changing the colour match, or hiding unexplored areas, uses the live art throughout.
  (New textures, 69 MB: restart the game.)
- The continents' and seas' names cost far less to pan and zoom: only those near the view are
  drawn, and their halo takes half as many font strings (each copy's shadow is the one opposite
  it), the same to look at. Panning over a continent with its names showing was a third of the
  map's frame time on a wide screen. While the map moves (zooming or panning) their halo rests
  (every letter is drawn again at its new size on each frame of a zoom, and laid out again on each
  of a pan, and the halo was eight of its nine), back as soon as the map stops.
- Questie's icons from the neighbouring zones are placed up to half the map's width round it,
  not a whole width: every icon on the map is laid out again on each frame of a pan or zoom (231
  of them cost 7 ms a frame on a wide screen). Those further off show once the map switches to
  their zone.
- Panning and zooming no longer lay out the thousands of zone textures that aren't showing (the
  live art the baked tiles stand in for, the tiles off the view): a hidden one lets go of its place
  on the map until it shows again. With vsync off on a wide screen, all of OpenMap's art cost 20 ms
  of a 41 ms panning frame, 8 of them in art nobody could see.
- Up close over Orgrimmar the minimap's detail is much fainter (15% at most, from 50%): the city's own
  plan, which comes in from further out than the other cities', leads there.
- OpenMap's icons (flight masters, dungeons, the player arrow ...) are on the map's view instead of
  its canvas: they keep their size on screen by themselves, instead of their layer being rescaled
  on every frame of a zoom (which laid every icon out again: 6.6 ms of a zooming frame).
- `/openmap bench` times the map where it's slow (still, panning and zooming, at several zooms, then
  with each part of it off in turn) and gives the results to copy into an issue.
- The OpenMap menu's close button is easier to hit, and Escape closes the menu.
- "Report a problem" isn't only about the map: circling a spot is optional (just click Next), it
  works on dungeon maps too, and the issue form says so.
- The debug overlay also shows what can pile up over a session: the UI's Lua memory and how fast it
  grows, the map's pins (every addon's, and the kind there's most of), how much zone art is loaded,
  how many regions are placed live, which parts make the most Lua garbage a second (rescaling
  every addon's pins, switching maps, OpenMap's own updates), and which addons hold the most
  memory and grow it fastest.

## v0.2.0-beta (2026-10-11)

- Map notes (Tools → Map notes, `/openmap notes`) replace the paint tool: paint an area (or
  click) and say what's there, as a "fix this", "look into this" or "idea"; a list of them all
  (click one to go there) and Export, which gives them all as text to paste where they're needed.
  `tools/map-preview/notes.py` renders them out of game. Older paint mark-up becomes notes.
- A debug overlay (Tools → Debug overlay, `/openmap debug`): the frame rate on the map, a graph of
  frame times, the worst frame, and what OpenMap's own updates cost.
- The quest log shows on the full-screen map too: the Quest log button (and the arrow button in
  the corner, as on the windowed map) puts it over the map's right side. Its background no longer
  ends in a line when the window is taller than Blizzard's.
- Blizzard's quest areas (the blue shapes) keep up with the map as it zooms, instead of a step behind.
- The OpenMap button and the favourites' row are in the map's bottom-left corner, along its
  foot (over the coordinates when they show); favourites are icon buttons in Blizzard's
  action-button frame, glowing while they're on.
- The OpenMap menu is laid out afresh in the map window's own frame: the actions as tiles with
  icons, an icon by each setting, bronze rules between the parts. Find me, Drop a pin,
  Report a problem, Options and a new Quest log button (hide or show the quest log beside the
  map, out of combat) can be starred onto the map too.
- "Minimap detail" (in the menu's Up close and in Options) turns the minimap's detail off at
  the closest zoom, so the painted map is all you see.
- The deepest zoom is a slider in the menu, and goes to 192x (it was 96x at most).
- The window resizes from its bottom-left corner as well as the bottom-right, and both grips
  are easier to catch.
- Favourite settings: the star by each setting in the OpenMap menu puts it on the map as a
  button of its own, beside the OpenMap button (lit while it's on; click to switch it,
  right-click to take it off).
- The parchment border's edges are laid as copies of their piece at its own length, every other
  one mirrored, instead of one piece stretched along the whole side; the corners are as they were.
- Orgrimmar and Undercity keep their own maps' name banners: up close that's the city's title,
  and their zone's big banner for them (Durotar's, Tirisfal's) gives way to it as you zoom in,
  instead of covering the city. (Changed textures: restart the game.)
- No more straight-edged patches over the zones zoomed out (east of the Barrens, Stranglethorn ...):
  the blank paper in the gaps between zones reaches only a little way under the zones, not to
  the edge of the square it's drawn in. (Changed textures: restart the game.)
- The ocean past the world map keeps the world sea's own colours, carried outward, instead of
  one flat grey-green. (New texture: restart the game.)
- The OpenMap button stays in the map's top-left corner (an addon's frame across the map
  could push it off the right edge).
- Going full screen and back (or resizing the window) keeps the view you were looking at,
  instead of jumping to where the map was last closed.
- Resizing the window keeps its top-left corner (and the OpenMap menu) in place with the map
  size option off 100%, so the corner stays under the cursor; the resize grip sits in the
  window's outer corner, clear of the quest log button, and is easier to catch.
- Reopening a moved or resized map shows it in its place at once (not Blizzard's first).
- The menu's pin button works wherever you click (on Blizzard's map icons too, where only
  Ctrl-click did), with the pin cursor while it's on.
- On the stitched map the waypoint is always OpenMap's pin: Shift-clicking Blizzard's there was
  blocked ("only available to the Blizzard UI"). Shift-click OpenMap's to share it in chat.
- No more square patches and straight bands in the sea off Stranglethorn and Wetlands: the
  gap fill's borrowed paintings of the land between zones stay on land, and a zone's painted
  sea fades out well inside its frame. (New textures: restart the game.)
- Zone art fades in as it loads (zooming or panning fast onto new zones), instead of popping in.
- Over the major cities' own maps the minimap shows at half strength at most, so the city plan leads.
- "Dim unexplored areas" is now "Fade unexplored areas": those areas fade 60% of the way to the
  zone's blank parchment (its unexplored look) instead of darkening.
- Faster panning and zooming: map icons off the view (townsfolk, flight masters ...) are
  hidden, and blank tiles of the filled-in land aren't drawn.
- Opening the map loads only the zone art in view (and none until zone detail shows), instead
  of the whole world's; `/openmap status` shows how long the last openings took.
- Questie's icons stay on the map when it switches to a zone: Questie's map library places
  them from world coordinates that are off on Forever's zone and continent maps, so there
  each icon is placed (or moved) from Forever's own map positions. They're also lifted above the stitched art:
  Questie fixes its icons' frame levels, which put them under the zone art up close. `/openmap status`
  shows how many Questie icons there are and who placed them.
- The parchment border frames the map only when zoomed right out, fading as you zoom in.
- Blizzard's glow on the zone under the cursor is off by default on the stitched map
  ("Zone highlight on hover" in the menu brings it back).
- The map window's portrait is OpenMap's icon while the map is stitched; the OpenMap button
  sits beside Blizzard's floor dropdown instead of under it.
- Opening the map sets its view once (straight to where you left off), or not at all if
  it's still there, instead of Blizzard's reset to the whole world and back; the
  close-up softening no longer recolours the whole map when it first builds a zone.
- Zone art coming into view loads over a few frames instead of stalling one; `/openmap status`
  names the slowest steps of the close-up update, and how much of opening the map is OpenMap's.
- Undercity: Tirisfal's "Undercity" banner sits over the city until close in, as Orgrimmar's
  does. You can zoom 1.5x further in cities, and the minimap mixes in over the cities in the
  open. Undercity's and Ironforge's own maps are drawn over the minimap, which shows the
  surface there, wherever they are in the view.
- Blackrock Mountain's inside (its main floor) surfaces from further out as you zoom in on it.
- Cave and dungeon-entrance maps stay while they're on screen (they no longer fade as you pan
  away from them); only the dimming of the surface follows the one you're centred on.
- Undercity's map is cut to the city's plan (its quarters, the Ruins, the Sewers), so Tirisfal's
  painting shows round it instead of the city map's own parchment.
- "Fade while moving" (0-90%, in Options; on / off in the map's menu) replaces "Don't fade while
  moving": the map fades smoothly while you move, never while the mouse is over it.

## v0.1.0-beta (2026-10-09)

First public beta. One seamless world map for WoW Forever: every zone stitched
together, Blizzard's own art, with dungeon entrances and caves, flight paths,
boat and zeppelin routes, townsfolk and rares (with Questie), search, map pins,
group members, a movable and resizable window, and a "Report a problem" button.
The continent and sea names are lettered live; land Forever has no zone map for is
drawn from Blizzard's classic and pre-Cataclysm maps of it, or left as blank parchment.
