# Releasing

Releases are built by the [BigWigsMods packager](https://github.com/BigWigsMods/packager)
when a version tag is pushed: `.github/workflows/release.yml` runs the offline tests, zips the
`OpenMap` folder (`.pkgmeta`), puts the version in the toc (`@project-version@`), makes a
GitHub release with the zip, and uploads it to CurseForge.

## Once

1. **CurseForge project**: create it, then add its project ID to `OpenMap/OpenMap.toc`:
   `## X-Curse-Project-ID: 123456`. Without it the packager skips the CurseForge upload
   (the GitHub release still happens).
2. **API token**: CurseForge → My API Tokens → generate one, then on GitHub: the repo's
   Settings → Secrets and variables → Actions → New secret `CF_API_KEY`.
3. **Game version**: WoW Forever's interface number (16001) is new; if the packager can't
   tell which CurseForge game version it is, the upload fails with a message saying so. Then
   set the game version by hand on the CurseForge file, or pass it to the packager in
   `release.yml` (`with: args: -g <version>`).
4. **Check the zip once**: run the workflow on a test tag (`v0.0.1-test`), download the zip
   from the GitHub release, and check it has a single `OpenMap/` folder with the toc inside.

## Each release

1. Run the in-game check: [testing.md](testing.md).
2. Move the "Unreleased" notes in `CHANGELOG.md` under the new version, written as what the
   release does (not each step of getting there) and grouped under `### New`, `### Improved`
   and `### Fixed`, the most important first (a change's lead-in in `**bold**`), then run
   `python -P tools/changelog/build.py`: the in-game "What's new" (`Data/Changelog.lua`) is made
   from it, and lint fails while the two disagree.
3. Tag and push: `git tag v0.2.0` then `git push origin v0.2.0`.

Tags with `-beta` or `-alpha` in them are uploaded to CurseForge as beta / alpha files.

## By hand

To upload without the workflow, do steps 1 and 2, commit, then

    python -P tools/package/build.py v0.5.0-beta --client=forever

It runs lint and the offline tests, then writes `dist/OpenMap-v0.5.0-beta-forever.zip`: the
`OpenMap/` folder as committed with the version in its toc, with only that client's toc, data and
textures (`--client=retail` for retail's; each client's zip is a file of its own on CurseForge,
named `v0.5.0-beta-forever` / `v0.5.0-beta-retail` and tagged with that client's game version and
flavour). The workflow's packager doesn't split clients yet: it zips every folder. It also writes
`dist/OpenMap-v0.5.0-beta-changelog.md`, that version's notes. On CurseForge, open the project's
Files → Upload File, choose the zip, paste the notes as the changelog (Markdown), set the release
type (Beta for a `-beta` version) and the game version, and upload. Tag the commit when you can
push again, so the next release's notes start from the right place.
