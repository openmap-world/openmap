# Translating OpenMap

OpenMap's text is written in English in the code and looked up through `ns.L["English"]`; a
language's translation is used where there is one, else the English. Each language's translations
are in `tools/locale/<locale>.json`, `{ "English": "translation" }`, and
`python -P tools/locale/translate.py build` turns them into `OpenMap/Locales/<locale>.lua` (and the
addon list's description, the `@toc-notes` entry, into the toc).

- `python -P tools/locale/translate.py export` writes `strings.json`: every text, and the files and
  lines it's used on (open them to see what it is: a menu row, a tooltip, a chat message ...).
- `python -P tools/locale/translate.py check <locale>` checks one language: what's missing, and what
  would break in game.

Languages: deDE, esES, esMX (Latin American Spanish), frFR, itIT, koKR, ptBR, ruRU, zhCN, zhTW.

## How it should read

- **The game's own words.** Use the term the game itself uses in that language, as its UI, quest
  log and world map write it: World Map, Minimap, Quest Log, Flight Master, Innkeeper, Banker,
  Auctioneer, Stable Master, Class Trainer, Profession Trainer, Spirit Healer, Vendor, Repair,
  Mailbox, Rare, Rare Elite, Dungeon, Raid, Zone, Continent, Waypoint, Map Pin, Zeppelin, Boat,
  Horde, Alliance, Show, Hide ... Players know these words from the game; a different word for the
  same thing reads as a mistake.
- **One word for one thing**, all the way through.
- **Natural, short, plain.** As a player would write it, not word for word from the English. Menu
  rows and buttons are narrow: keep them as short as the English or close to it. Tooltips and
  descriptions can be as long as the language needs. Address the player as the game's own interface
  text does in that language (its settings, tooltips and system messages), in the same register.
- **Numbers.** A text with a count (`%d stops`, `%d versions`) is shown for any number: write it so
  it reads right for all of them (Russian, for one, has several plural forms: a form like
  "пересадок: %d" works for every number).

## What must come through as it is

- Placeholders: `%s`, `%d`, `%.1f` ..., as many as the English has, of the same kinds. Their order
  can change where the language needs it, with positions: `%2$s ... %1$s` (WoW's format takes them).
  `%%` is a percent sign.
- Colour codes `|cffxxxxxx` ... `|r`, textures `|T...|t`, line breaks (`\n` in the JSON).
- Slash commands (`/openmap pins`, `/reload` ...), addon names (OpenMap, Questie, TomTom, Leatrix
  Maps, Dungeon Journal, NeedRoll, Shortest Path Forever ...), people's names (Santiago Reyes),
  key names as the game writes them in that language (Shift, Ctrl, Alt: as the game's own key
  bindings show them).
- `%d %s %s` is a date: day, month's name (the game's own), year. Reorder it for the language with
  positions, e.g. `%3$s年%2$s%1$d日`.
- The game's place names (zones, dungeons) come from the game in the player's language; they aren't
  in these texts.
