# Local Orca export-label fix

The native `ExportConfigsDialog` displays canonical bundle identities directly
in its printer bundle / printer preset checklist. For local bundles that means
`_local/<bundle-id>/<profile-name>` appears instead of the friendly name.

The local checkout at `C:/Users/justw/OrcaClean/OrcaSlicer` was patched in
`src/slic3r/GUI/CreatePresetsDialog.cpp`, in `select_curr_radiobox`:

- Printer bundle label: `get_preset_bare_name(preset_name)`.
- Printer preset label: `get_preset_bare_name(preset.first)`.

Both calls still pass the original `preset.second` pointer to `create_checkbox`.
That helper stores the pointer for export selection separately from the text.
No profile names, package IDs, file paths, references, or export lookup keys change.
Ordinary names remain unchanged. Two bundles with the same friendly name can
still have identical visible labels; their selected profile pointers stay distinct.

Scope: the native printer export checklist only. This does not patch the separate
web-based export dialog or recipient installations. No installed profile needs
renaming or reinstalling for this display-only fix.

The local source already contained other changes; those were preserved. Do not
distribute this build as a clean upstream build or include local profile resources
in a public package. No source commit or release was made.

Build command:

```powershell
cmake --build build --config Release --target OrcaSlicer_app_gui -- /m:2 /verbosity:minimal
```

This existing build has zero CTest tests configured. Compilation and a manual
check of both printer export lists are required before calling the fix verified.

## Build result — September 15, 2026

Release build completed with exit code 0. Both `OrcaSlicer.dll` and
`orca-slicer.exe` were rebuilt in `build/src/Release`. The rebuilt launcher
returned exit code 0 with `--help` (no captured console output). This is only a
startup smoke check, not a visual export test. Existing compiler/linker warnings
remain, including LNK4098. No installed executable was replaced.

Close the current Orca window before launching
`C:/Users/justw/OrcaClean/OrcaSlicer/build/src/Release/orca-slicer.exe`.
Check File → Export's printer bundle and printer preset lists. The same installed
bundle should now display only its friendly profile name. No reinstall needed.

## Follow-up: archive initialization and local-bundle export

The user subsequently hit `initialize fail`. The old exporter appended the
canonical identity to the output folder as a filename, so its slashes became
nonexistent subdirectories. Printer temporary filenames had the same defect.

- Added `ExportFilename.hpp`: strips recognized bundle prefixes, sanitizes
  Windows filename characters, removes trailing dots/spaces and handles reserved
  device names. Eight standalone C++ test cases passed.
- Temporary printer copies now use unique filenames in Orca's Temp folder.
- A local-bundle printer export preserves its bundle ID and readable metadata,
  collects same-bundle material/process presets and startup defaults, recursively
  includes parents, detects cycles/missing/external parents, and emits parents
  before children using unique ZIP entry filenames.
- Export serialization uses copies and removes printer connection credentials.
  Existing destination files get a numbered suffix for this local-bundle path.
- Cross-bundle or subscribed dependencies are refused, not silently relabeled.
  The legacy non-bundle path only receives the filename sanitization fix.

The updated Release GUI build completed successfully. Test command from the
Profile Lab workspace (create `artifacts/orca-export-check` first):
`tests/run_orca_export_filename_smoke.cmd`.

**Not yet verified:** actual GUI export/import/restart on a recipient installation.
In particular, this Orca importer's save routine places imported presets in flat
type folders; ancestor loading after restart remains a separate risk that a
successful ZIP creation does not resolve. Do not claim round-trip compatibility
until that test has passed. No real/internal profile export was used in testing.
