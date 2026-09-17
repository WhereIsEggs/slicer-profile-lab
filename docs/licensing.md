# Licensing and sharing releases

Profile Lab is licensed under **AGPL-3.0-only**. Copyright (C) 2026 WhereIsEggs
for original contributions. Upstream material retains its original copyrights.
Read [LICENSE.txt](../LICENSE.txt), [NOTICE.md](../NOTICE.md), and the
[third-party notices](../packaging/THIRD-PARTY-NOTICES.md).

## What to distribute

For every Windows release, provide the installer and its matching
`SlicerProfileLab-VERSION-source.zip` together at the same download location,
with `SHA256SUMS.txt` and the testing guide. Source access must not cost extra.
Do not substitute the moving main branch for the matching release snapshot.
Keep the corresponding source available with the binary release. If you send
the installer directly to someone, send the matching source ZIP too.

The source ZIP includes the actual app source, tests and fixtures, build scripts,
license/notices, dependency source archives, and build information. The installed
app additionally contains its project source ZIP and dependency-source directory.
No git checkout, private cache, profile export, token or local virtual environment
is included. Builds from the source ZIP do not require git history.

Follow [windows-release.md](windows-release.md) to rebuild. Install a compatible
64-bit Python (the tested build version is recorded in build-info.json), the
pinned build dependencies, and Inno Setup. Internet is required for package/tool
installation; the build can reuse the included dependency sources. No proprietary
signing key is needed to build or run modified versions. Unsigned modified builds
are supported, subject to the operating system's security policies.

## When modifying or redistributing

- Preserve the license, copyright notices, attribution and warranty disclaimer.
- Identify your modifications and their dates. Distribute covered modified work
  under AGPL v3 and supply its matching corresponding source, not the original
  release's source. Recipients retain their rights to modify and redistribute.
- Keep dependency notices and sources with their binaries. For any new dependency,
  review compatibility and source obligations before adding it to a release.
- If you offer a modified version for remote network interaction, implement the
  source-access requirement of AGPL section 13. This desktop app is not currently
  offered as a hosted service.
- Do not imply that an independent modified release is endorsed by OrcaSlicer or
  WhereIsEggs. Attribution is not an endorsement.

These instructions support the license; they do not replace its terms or create
extra restrictions. Commercial use and charging for distribution are permitted.
For unusual distribution arrangements, obtain appropriate legal advice.

## Optional Orca downloads and generated profiles

The standard installer does not bundle Orca's engine or profile library. If you
redistribute those separately or change the installer to bundle them, preserve
their own notices and provide the matching source as required; this project's
source ZIP is not a substitute for the native Orca engine's source.

Profile Lab's license does not automatically apply to independently authored
profile data simply because the tool generated a JSON or ZIP file. Profiles
derived from library content may carry upstream obligations; keep their provenance
and review the applicable terms when sharing them.
