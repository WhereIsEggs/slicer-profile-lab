# Slicer Profile Lab

A native desktop workspace for creating, mixing, checking, installing and sharing
**OrcaSlicer printer, filament and process profiles** without hand-editing JSON.
The goal is a clean, beginner-friendly interface that handles dependencies behind
the scenes. A command-line validator is also included.

**Status: active development / experimental.** The real library → draft or set →
package → install → recipient import workflow is implemented. This is not yet a
complete replacement for Orca's settings editor. Passing checks does not certify
print safety.

## Get started

Windows is the currently tested desktop/install platform. Use Python 3.12 or newer
(the project declares `>3.11`). From the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m profilelab.desktop
```

After setup, double-click **Start Profile Lab.cmd**. With the virtual environment
activated, `profilelab-desktop` works too. No browser or web server is required.
The desktop extra installs PySide6 and psutil; Orca's optional engine is a separate
download.

See the [Workflow guide](Real%20Workflow%20Guide.md) for step-by-step instructions.
The fictional offline sandbox remains an internal regression-test fixture; the
normal launcher opens the real application.

## Available now

### System library and inheritance

- Download the official **2.4.2** library pinned to
  `8500fcdccaa10b5099ac20d252af3a7c560046f1`; browse offline after download.
- Search/filter profiles; inspect original JSON and resolved settings, including
  inherited/overridden values and their source profiles.
- Resize the profile list and settings panel using the visible draggable divider.
- **Check for updates** reports newer official stable GitHub releases. It does
  **not** upgrade the library, engine or saved work.
- In profile sets, **Add from library** filters category, vendor and search, plus
  explicit printer model/nozzle variant. It shows ancestry and blocks unresolved sources.
- Non-instantiated templates are excluded from creation choices but remain
  inspectable. Generic selectable profiles are not hidden based on names alone.

Downloads are staged; the cache records source/revision/integrity information.
It is separate from Orca's installed compiled `.opc` files. Public profiles
belong to OrcaSlicer and its contributors; upstream source/license attribution
(AGPL-3.0) is recorded in the cache's `source.json`. Resolved values include
explicitly saved ancestor settings, not all Orca internal defaults.

### Drafts and friendly editing

- Create independent named drafts from system profiles, leaving originals unchanged.
- Freeze source revision/starting values; save overrides automatically and reopen
  offline. Reset individual settings to baseline; changed values appear in bold.
- Click values to edit; setting names remain read-only. Lists display without JSON
  brackets, known booleans use On/Off, and G-code has a multiline editor.
- Supported draft reference fields offer constrained library choices. Extruder-aware
  fields use E0/E1, with Left/Right labels for two slots.
- **Delete draft…** confirms removal and preserves a recoverable `deleted-drafts`
  copy. Packages and installed profiles are not deleted.

Numeric validation, reference choices and specialized editors cover a limited
subset—not every Orca setting, enum or compatibility expression.

### Multi-printer sets and scratch creation

- A saved wizard: **Printers → Filaments → Processes → Assignments and review**.
- Mix library profiles and drafts, or create starter profiles from scratch.
- Include multiple printers, materials and processes in one set; duplicate members
  as nozzle-size or printer-size variants.
- Assign materials/processes per printer, including shared materials,
  nozzle-specific processes and default filament for each extruder.
- Save incomplete work automatically. Missing defaults, stale references and
  unassigned members block packaging. Supported diameter/layer-height checks warn
  about inconsistencies.
- Preserve source ancestry/revision as project metadata, including on duplicated
  variants, without adding non-Orca fields to exported profile JSON.

Scratch forms cover rectangular, front-left-origin FFF printers with one or two
extruders, basic filament settings and basic process settings. Machine G-code and
dual-extruder offsets must be supplied. These are starter forms, not a complete
generator for every printer architecture.

### Packaging, installation and sharing

- Review members, then save automatically using the draft/set name—no routine
  Save As dialog. Keep an internal prepared `.orca_bundle` and a sharing **ZIP**.
- Resolve saved parent values into self-contained ordinary user presets; establish
  explicit printer/material/process links without requiring hidden system parents
  on the recipient's computer.
- Install to Windows `OrcaSlicer/user/default` as **User** presets, not system or
  bundle presets. Recheck that Orca is closed; unknown process status blocks writing.
- Refuse existing-name collisions instead of overwriting; stage installation and
  clean up newly created files if installation fails.
- Import the sharing ZIP in Orca with **File → Import → Import Configs**.

**Share Profile Lab's ZIP, not an Orca re-exported `.orca_printer` bundle.** In our
stock 2.4.2 and pinned 2.5.0-dev tests, Orca exported all files but bundle import
lost compatibility links. Profile Lab ZIP imports and selected profiles survived
restart. See the [compatibility audit](docs/upstream-variant-audit.md).

### Validation

- Built-in checks: missing/invalid folders, empty profile folders, malformed or
  non-object JSON, invalid names, duplicate names, missing parents and cycles.
- Additional ID/reference checks for recognized complete system trees. System
  identity rules are not imposed indiscriminately on ordinary user profiles.
- **Check my OrcaSlicer profiles** provides an installed-user-profile check path;
  system sources are used privately where available.
- **Install Orca engine** downloads official nightly assets, verifies published
  checksums and installs into Profile Lab's private cache.
- Background checks distinguish built-in results from unavailable, failed or
  incomplete engine validation. Read-only checks can run while Orca is open.

Full engine checks require matching source JSON/resources; compiled `.opc`
files alone are insufficient. User-profile engine checks cover loading/inheritance,
not slicing. Complete source-tree checks can exercise upstream slicing/subtype
checks. Packaging does not automatically certify full-engine validation.

## Versions and verification

The production library remains **2.4.2**. Separate development testing used clean
**2.5.0-dev**, commit `f520e9221f220657f752d269ead37dd61e9cb0c3`—not a final 2.5.0 release.

As of September 17, 2026:

- 159 Profile Lab tests passed with native/public-library/upstream-ID opt-ins.
- 55 upstream Python ID tests and 104 upstream native profile tests passed.
- GUI checks covered 0.4/0.8 switching, matching processes, ZIP recipient import
  and restart in stock 2.4.2 and the pinned development build.
- Development system-model grouping worked. User presets retain their own display
  behavior. A legacy dual fixture showed two slots but a blank nozzle selector;
  complete newer dual/flow-variant UI support is not certified.

The local build and **Start Orca 2.5 Test.cmd** are maintainer test conveniences,
not a bundled Orca dependency or installer for GitHub users. The launcher expects
a specific local checkout and uses isolated test data.

## Planned—not implemented yet

Roadmap items below are not current capabilities or promises of release dates.

- Full Orca-style categorized settings pages: comprehensive labels, units, help,
  enums, limits, structured-value editors and version-aware schema validation.
- Broader scratch creation, guided printer-family/variant editing and complete
  newer dual-extruder/flow-variant metadata support.
- Existing user profiles as direct editable starting points, broader compatibility
  expression handling and user-profile reference choices.
- Reviewed library/engine upgrades, version selection, change review and rollback.
  The current update button only checks for newer stable releases.
- Easier matched engine/source setup and clearer actionable validation throughout
  creation, packaging and installation.
- Configurable portable, cloud-account and custom installation destinations.
  The current install button targets the normal `user/default` folder.
- Broader package/set cleanup and installed-profile management. Draft deletion
  and removing a set member exist; a general uninstall/package manager does not.
- Distributable desktop packaging without Python setup, and wider recipient,
  platform and version regression coverage.

Review temperatures, dimensions, motion limits, filament diameter, extruder
mapping and G-code before printing. Assignment establishes links, not physical
suitability. Printer switching can select Generic PLA rather than the assigned
default; explicitly check filament and process selectors.

## Data locations (Windows)

| Data | Default location |
| --- | --- |
| Library | `%LOCALAPPDATA%\SlicerProfileLab\libraries` |
| Drafts, sets, packages | `%LOCALAPPDATA%\SlicerProfileLab\drafts`, `sets`, `sharing` |
| Private engine | `%LOCALAPPDATA%\SlicerProfileLab\engine` |
| Installation target | `%APPDATA%\OrcaSlicer\user\default` (`machine`, `filament`, `process`) |

## Command line and tests

With the virtual environment activated:

```powershell
profilelab <profile-folder>
profilelab tests/fixtures/valid_parent
python -m unittest discover -s tests
```

The CLI recursively checks JSON profiles using built-in validation, not the
optional engine. Exit code `0` means no built-in problems found; `1` means
problems/incomplete validation. In PowerShell, inspect `$LASTEXITCODE`.
A standalone folder check expects parents within that tree and stops at the first
malformed/invalid profile. Use the desktop user-profile path for installed profiles.

Native, cached-library and pinned-upstream tests are opt-in and may be skipped by
the ordinary command. See the [audit](docs/upstream-variant-audit.md) for exact
setup/results. Use fictional or public fixtures; do not commit private profile
exports, caches or build artifacts.
