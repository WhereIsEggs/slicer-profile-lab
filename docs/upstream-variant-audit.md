# Upstream variant compatibility audit

Development reference: `f520e9221f220657f752d269ead37dd61e9cb0c3` (main, checked 2026-09-17).
Stable reference: 2.4.2, `8500fcdccaa10b5099ac20d252af3a7c560046f1`.

## Source-confirmed behavior (not GUI verification)

- `src/slic3r/GUI/PresetComboBoxes.cpp`: system printer display groups are keyed by
  `printer_model`. Bundle and user presets have separate branches; do not assume
  they get the same short-name grouping.
- `src/libslic3r/Preset.cpp`, `diameters_of_selected_printer`: gathers
  `printer_variant` strings from presets with the same `printer_model`.
- `src/slic3r/GUI/Plater.cpp`: the separate unified nozzle selector is shown for
  the single-extruder layout without flow variants. The dual layout hides it and
  uses its own extruder controls. Two nozzle values alone are not proof of the UI
  mode: the code also inspects extruder variant metadata.
- `scripts/orca_profile_tool.py` now combines system profile maintenance and ID
  checking. System-profile ID policy must not be applied indiscriminately to
  ordinary user profiles.

## Isolation

Clean checkout: `C:/Users/justw/OrcaClean/OrcaSlicer-upstream-test`.
No patches from the old source tree are included. Stock installation and normal
Roaming/OrcaSlicer profiles are not test destinations. Old source deletion is
authorized but deferred until a replacement build succeeds and no dependencies
still refer to the old tree.

## Build result

Clean upstream checkout and Release app/validator built successfully with VS2022
Build Tools (MSVC 19.44.35222), CMake 4.3, `ORCA_TOOLS=ON`, `BUILD_TESTS=ON`.
Startup log confirms **2.5.0-dev build f520e922**. This is a development snapshot,
not a released 2.5.0 and not an upgrade to Profile Lab's production library.
The upstream working tree is clean. Existing compiled dependency libraries were
copied to the new isolated prefix; missing/changed dependencies were built there
(including Python 3.12.13, wxWidgets 3.3.2, wxInspector, Assimp, FFmpeg, OpenSSL).
No old application patches were reused. The new main CMake cache has no paths
into the old checkout. The old checkout has not been deleted.

App: `C:/Users/justw/OrcaClean/OrcaSlicer-upstream-test/build/src/Release/orca-slicer.exe`

SHA256: `090F8D5C329A7A4643C3711D4A0126EACEA942C1864F32ADDD0783AE6DB52369`

Matching validator is `OrcaSlicer_profile_validator.exe` in that same folder.
Use **Start Orca 2.5 Test.cmd** in the Profile Lab folder. It always supplies an
isolated `--datadir` under `artifacts/variant-comparison/development-sender`.
Close other Orca sessions first to avoid confusing the two versions. The fixture
printers are fictional and must not be used to print. Normal profiles are not
copied into this test environment.

## 2026-09-17 stock GUI comparison

Executable: `C:/Program Files/OrcaSlicer/orca-slicer.exe`; startup log confirms
`2.4.2 build 8500fcdc`. Test-only data: `artifacts/stock-export-test/sender`.

- Imported `artifacts/variant-comparison/30dbdbe7/Lab-family.zip`: GUI reports
  eight configs. All five printers appear as ordinary User presets.
- Standard 0.4 and 0.8 are separate user entries. The nozzle control lists both;
  choosing 0.8 switches printer and selects Lab Process 0.8 (layer height 0.4).
  **This feature exists in the installed stock 2.4.2, not just development.**
- Lab PLA is selectable. Automatic printer switching chose Generic PLA instead;
  stored default references are correct. Do not promise automatic filament choice.
- Dual fixture shows two material slots and hides the single nozzle selector.
  Orca displayed an empty changed-settings prompt on first selection; accepted
  Save in the isolated test. This is not a dual hardware validation.
- Exported all five as `.orca_printer`: GUI reports success, no initialize-fail.
  Each archive contains its printer, Lab PLA and the assigned Lab Process.
- Fresh recipient test uses only the unrelated public Workshop baseline to avoid
  the first-run wizard (its embedded browser rejects automated clicks).
  `artifacts/variant-comparison/recipient-baseline` contains none of the Lab
  profiles before import. Importing the five exports reports 15 configs.
- **Recipient compatibility FAIL:** selecting bundled Lab Standard 0.8 shows only
  Default Setting in processes. Stored compatible_printers still contains plain
  Lab Standard 0.8 / Lab XL 0.8 names although presets are now under `_local/UUID`.
  File import count alone is not a successful sharing test. Keep Profile Lab ZIP.
- Imported the Profile Lab ZIP into the recipient: eight configs, ordinary User
  entries, matching process and selectable Lab PLA. Selected Standard 0.8 / Lab
  PLA / Lab Process 0.8 survived closing and reopening stock Orca.

## 2026-09-17 development GUI comparison

Sender: `artifacts/variant-comparison/development-sender` (only test fixtures).
Recipient: `artifacts/variant-comparison/recipient-af61e668` (unrelated public
Prusa fixture initially; no Lab profiles). `tests/prepare_variant_recipient.py`
can create another fresh isolated recipient without touching normal Orca data.

- Standard 0.4 → 0.8 nozzle selection switches the printer and Lab Process 0.8.
  Lab PLA remains selectable, although switching chose Generic PLA in the sender.
- Enabled public Prusa MK3S system variants in the isolated recipient. The system
  selector displays the short **Prusa MK3S** name; choosing nozzle 0.8 retains that
  short name and selects `0.30mm Detail @MK3S 0.8`. User fixtures still display
  their full preset names. System grouping is not a reason to disguise user
  presets as system presets.
- Legacy-style dual fixture loads and shows two material slots, but the new GUI
  leaves a blank single-nozzle control visible. Source logic uses
  `extruder_variant_list` to recognize the new dual layout. Two nozzle values
  alone are insufficient. Do not claim full new dual/flow-variant UI support or
  copy Bambu-specific metadata into arbitrary printers to hide this difference.
- Exported Standard 0.8 as `.orca_printer` successfully. Recipient imported three
  configs but selected **Default Filament / Default Setting**. Plain compatibility
  names remain stored under a `_local/UUID` bundle: the stock failure reproduces.
- Imported Profile Lab's same eight-profile ZIP into that recipient. Selecting
  the ordinary User Standard 0.8 immediately shows **Lab PLA / Lab Process 0.8**.
  All three selections survive a full application restart.

| Check | Stock 2.4.2 | Pinned 2.5.0-dev |
| --- | --- | --- |
| User 0.4/0.8 nozzle switching + matching process | Pass | Pass |
| Profile Lab ZIP recipient selection + restart | Pass | Pass |
| Orca `.orca_printer` export creates archive | Pass (five printers) | Pass (Standard 0.8) |
| Orca `.orca_printer` recipient compatibility | Fail | Fail |
| Short system model + nozzle switch | Source-audited, not GUI-tested here | Pass (Prusa MK3S) |
| Legacy dual fixture UI | Two slots; nozzle selector hidden | Two slots; blank selector caveat |

These are bounded fixture checks, not every vendor/nozzle/dual configuration or
print-safety certification. No jobs were sliced or sent to a printer. No upstream
application fixes were made. Future upstream changes must be re-tested rather
than assuming this snapshot predicts the final 2.5.0 release.

## Profile Lab refinements

Add-from-library now filters explicit inherited printer_model / printer_variant,
shows actual base-to-selected ancestry, and keeps generic instantiated filaments
selectable. Source revision/path/ancestry are saved as project metadata outside
Orca JSON. Unresolvable library entries cannot be selected; they do not hide valid
entries. No system/user ID rules or stable library pin were silently changed.
Duplicating a set member keeps its frozen source metadata. The actual installed
user profiles remain self-contained with empty `inherits`; ancestry is retained
in the project rather than leaving recipients dependent on hidden system parents.

Read-only visual QA: `tests/render_library_picker.py` renders the real re3D
library choices; model/nozzle controls, source chain and actions fit correctly.

## Regression results and future updates

- Profile Lab: **159 tests passed**, with native/public-library/upstream-ID
  opt-ins enabled against the newly built validator; six native fixture checks.
- Upstream Python setting-ID tests: **55 passed**.
- Upstream native `[Preset]` tests: **104 passed / 1,821 assertions**.
- `tests/test_upstream_identity.py` requires the exact development Git revision
  before comparing UUID/base62 system IDs. Update that pin only after review.
- The production library stays pinned to 2.4.2 / `8500fcdc…`. Development source,
  validator and data folders are separate; the installed production validator
  has not been silently replaced.

Regression command (PowerShell, local checkout paths):

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$env:PROFILELAB_NATIVE_TESTS = '1'
$env:PROFILELAB_PUBLIC_LIBRARY_TESTS = '1'
$env:PROFILELAB_UPSTREAM_SOURCE = 'C:/Users/justw/OrcaClean/OrcaSlicer-upstream-test'
$env:PROFILELAB_NATIVE_VALIDATOR = "$env:PROFILELAB_UPSTREAM_SOURCE/build/src/Release/OrcaSlicer_profile_validator.exe"
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Continue sharing the Profile Lab ZIP. Do not change hierarchy, IDs or packaging
based on display names alone. Before promoting a newer library/engine, repeat
the recipient GUI and restart checks, including explicitly supported dual
metadata. Archive/import success and native loading are necessary but not enough.
