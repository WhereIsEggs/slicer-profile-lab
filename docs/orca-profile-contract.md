# Orca profile contract and verification boundary

Rules reviewed against OrcaSlicer commit
`5c635d5e504c5f88d45ff7f0d66b63a83382d0bc` (2026-09-14).
The editor's existing 2.4.2 library remains separately pinned; it is not silently upgraded.

## Implemented

- Drafts created now freeze the full selected-to-root chain, including metadata.
  Older drafts can recover ancestry only from their matching library revision and
  unchanged source profile. Otherwise preparation stops with an explanation.
- Parent lookup uses the vendor and profile type; filament lookup may fall back
  to OrcaFilamentLibrary. Missing/ambiguous parents and cycles block preparation.
- `inherits` is a settings dependency. `compatible_printers` and
  `compatible_prints` are allowed-name lists, not package ownership or a request
  to export every printer/process in those lists. Startup defaults select the
  accompanying profiles. Expressions are preserved, not interpreted by Python.
- Prepared copies retain their hierarchy and inherited material identity.
  System `setting_id` values are not copied into user identities. Changing a
  material's vendor/type currently blocks export rather than reusing the old ID.
- Package `id` is distinct from its human-readable `name` and legacy `bundle_id`.
  References within a bundle use `_local/<id>/<name>`, matching Orca's constants.
- Direct installation uses `user/<account>/_local/<id>/`, not loose profiles.
  Each bundle has `bundle_metadata.json` and machine/process/filament folders.
  Ancestors use nested `base` folders: Orca reads these before child files.
  File stems retain the actual profile names. The desktop still targets the
  existing default account; automatic signed-in account selection is not done.
- Installation stages files outside `_local`, checks Orca's running state, and
  publishes the complete directory. It refuses replacements and performs no
  migration/deletion of existing profiles. Reinstalling identical contents is a
  no-op. Old packages must be prepared again.
- Archive reading rejects duplicate JSON keys, nonfinite numbers, traversal,
  duplicate/unlisted entries, mismatched kinds and identities, and oversize input.
- ID primitives use only Python's standard library. System setting-ID outputs
  match all six upstream C++ golden vectors; filament-ID outputs match sampled
  upstream snapshot entries. These primitives do not mint user/cloud IDs.

## What is NOT claimed

This is not yet full parity with Orca's vendor-submission workflow. In particular:

- Whole-tree filament product/snapshot validation, collision checks, the Bambu
  catalog mapping, and all optional source checks are not implemented in Python.
  `check_system_setting_id` checks that one rule only, not an entire library.
- The installed nightly runtime has compiled `.opc` system profiles. The native
  validator ignores caches in validation mode and requires source JSON. The UI
  now reports that missing prerequisite instead of claiming full validation.
  A source snapshot must be paired with the validator build before full-library
  native checking can be trusted. Do not swap in the editor's older library.
- Native regression uses an empty fictional system manifest, not a production
  vendor library. It proves that five fictional bundle presets load, including
  a two-level parent chain. It does not prove slicing, compatibility expressions,
  all multi-extruder settings, or the Orca GUI ZIP-import round trip.
- Orca's own GUI importer saves bundle files differently from Profile Lab's
  parent-first direct installer. Sharing a ZIP and importing through Orca must
  still be tested across supported versions before declaring it production-safe.
- Supporting parents can appear as additional presets depending on Orca's UI.
  They are not additional target printers selected for the package.

## Tests

Run ordinary tests with the project's virtual-environment Python:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Opt into the installed-engine regression (fictional temporary files only):

```powershell
$env:PROFILELAB_NATIVE_TESTS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The native test asserts individual successful-load messages, not just exit code
zero. An empty/skipped package must never count as a successful test.

## Official references

- [ID generator and checks](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/scripts/orca_id_tool.py)
- [C++ setting-ID vectors](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/tests/libslic3r/test_preset_setting_id.cpp)
- [Filament snapshot](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/scripts/filament_id_snapshot.json)
- [Bundle loading, metadata and import](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/src/libslic3r/PresetBundle.cpp)
- [User loading and parent-first base directories](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/src/libslic3r/Preset.cpp)
- [Literal bundle directory constants](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/src/libslic3r/Preset.hpp)
- [Vendor CI workflow](https://github.com/OrcaSlicer/OrcaSlicer/blob/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc/.github/workflows/check_profiles.yml)
