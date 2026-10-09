# Contributing to OpenMap

Thanks for helping. A few things make changes easy to review.

## Ground rules

- **Only contribute what you may license under MIT.** Don't copy code, data or
  art from addons that aren't openly licensed (for example Leatrix Maps or
  HiddenMaps, which are "all rights reserved"). Game facts (positions, level
  ranges) are fine; prefer generating them from the game's own tables
  (`tools/map-data`).
- **Generated files are generated.** Everything under `OpenMap/Data` except
  `Levels.lua` and `Labels.lua`, and everything in `OpenMap/Media/Textures`, comes from scripts in
  `tools/`. Change the script and regenerate; don't hand-edit the output.
  `Levels.lua` is entered by hand from the source named at its top: a correction
  needs a source too. `Labels.lua` is measured from the map art (see its top).
  Hand edits of Blizzard's art go in `art-edits/` (see its README).
- **Show blending changes with pictures.** `tools/map-preview/render.py` renders
  the stitched map out of game. Attach before / after renders to pull requests
  that touch how the map looks.

## Before a pull request

```bash
pip install lupa pillow numpy scipy
python tools/offline-test/run.py plain
python tools/offline-test/run.py secret
python tools/offline-test/lint.py
```

All three must pass (they also run on every pull request). They load the addon
in a stubbed client: they catch load errors, bad options and broken slash
commands, but not how the map looks or behaves. Check that in game.

## Triaging reports from players

Players report from the map itself (**Report a problem**): their issue carries a code
(`OM1|...`). Render exactly what they saw, circles and all:

```bash
python -P tools/map-preview/report.py <db2 dir> <texture cache> report.png "OM1|..."
```

## Reporting blending problems

Players: the "Report a problem" button on the map (circle it, add a note, paste the
code into an issue). Contributors: `/openmap paint` opens a paint-and-notes tool: brush over the problem (hide or
show a layer, blend a seam, tint) and leave a note. It's saved in
`WTF/Account/<account>/SavedVariables/OpenMap.lua` after a `/reload`; attach
that file (or the `paint` section of it) and a screenshot to the issue.

## Code style

Tabs, short comments that say why, names that read like the surrounding code.
WoW runs Lua 5.1: watch for `a and f()` truncating `f`'s multiple returns, and
read values the client may keep secret through `ns.Safe`.
