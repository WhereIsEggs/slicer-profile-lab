# Building the Windows alpha

The installer targets Windows 10/11 x64, installs per user without elevation,
and bundles Python/Qt plus a fixed Orca validator with matching source resources.
Publisher: WhereIsEggs. It does not bundle the Orca GUI or user data. It preserves workspace/Orca data
on uninstall. Version comes from `profilelab.__version__`; keep pyproject in sync.

## Build

Install the official Inno Setup 6 compiler and verify its published signature.
Use a separate 64-bit Python build environment, then from the repository:

```powershell
python -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install -r packaging/requirements-build.txt
.\.build-venv\Scripts\python.exe packaging/build_windows.py --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" --orca-source C:\Build\OrcaSlicer --orca-runtime C:\Build\OrcaSlicer\build\src\Release --orca-dependency-cache C:\Build\OrcaSlicer\deps\DL_CACHE
```

The compiler path may differ for a per-user installation. Dependency versions
are pinned. The script fetches upstream Qt license texts and checksum-verified
matching Qt/PySide source archives, bundles only app code
and explicitly selected docs/notices, records source revision/dirty status and
dependency versions, runs the packaged offline smoke check, and compiles Setup.
Artifacts are in a new `artifacts/releases/0.1.0a2-TIMESTAMP` folder per build.
The source snapshot is included inside the installed `_internal` folder.

Outputs: setup EXE, matching SlicerProfileLab-VERSION-source.zip, LICENSE.txt,
NOTICE.md, SHA256SUMS.txt, build-info.json, START-HERE.md and the app folder.
Send testers the setup EXE, source ZIP, checksum and guide—not the development venv.
The source ZIP contains tests, fixtures, build scripts, dependency sources and a
source-file hash manifest. Profile Lab itself can be rebuilt without git history;
the engine review gate requires a clean pinned Orca checkout and a reviewed binary.
The complete source archive includes `orca-sources/`, including upstream build
recipes/patches and matching dependency downloads. Extract the dependency ZIP
into Orca's `deps/DL_CACHE` to reuse those sources. Use upstream's Windows build
instructions with VS2022 x64, Release, ORCA_TOOLS=ON, SLIC3R_STATIC=ON and
SLIC3R_GUI=ON; build the `OrcaSlicer_profile_validator` target. The tested prefix
is `deps/build/OrcaSlicer_dep/usr/local`, supplied as CMAKE_PREFIX_PATH to the main build.

The bundled engine pin and binary hash are in `packaging/bundle_engine.py`.
To ship an intentionally modified/rebuilt engine, review its behavior, update
those pins and attribution, and provide its corresponding source. No signing
key is required. Cache paths can be repeated to collect verified dependency
archives from more than one local build. The staging step refuses missing or
unmatched source archives, a dirty upstream checkout, and an unreviewed binary.
The resources come from the same revision, not the editor's 2.4.2 library.
The app folder is an unpacked test payload, not a replacement for the installer.

On a Windows account with no existing Profile Lab Alpha installation, run
`packaging/test_installer.py PATH-TO-SETUP.exe` with the build Python to test
install, launch, reinstall and uninstall in a unique workspace artifact directory.
This temporarily registers the alpha installer for that account, then removes it.

## Release gates

- Run the unit tests and relevant native opt-in checks before building.
- Test the packaged smoke mode and real UI. Test a clean per-user installation,
  launch, reinstall/upgrade with the app closed and uninstall; preserve user data.
- Repeat in a clean Windows VM without Python before calling the alpha generally
  supported. A smoke test on the build machine is not that certification.
- Profile Lab is AGPL-3.0-only. Publish matching source next to every installer
  and preserve notices; see [licensing.md](licensing.md). Recheck third-party
  obligations when dependencies change.
- Unsigned alpha may be blocked by SmartScreen or organizational policy. Do not
  tell testers to disable protections. Arrange reviewed distribution/signing.
- Use a GitHub **pre-release** when approved; do not mark this stable/latest.
  Publishing/uploading is a separate explicit step, not performed by this script.

The build script neither creates a release nor commits/pushes changes. It never
embeds normal Orca or Profile Lab profile data. Manual test fixtures are fictional.
