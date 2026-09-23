# Slicer Profile Lab workflow guide

Profile Lab is AGPL-3.0-only, Copyright (C) 2026 WhereIsEggs for original
contributions, without warranty. See [licensing and source access](docs/licensing.md).

This describes the real application. See the
[README](README.md) for setup and the feature overview. Items marked **planned**
are not available yet.

## 1. Open the app and get the library

After installing the desktop dependencies, double-click **Start Profile Lab.cmd**
or run `profilelab-desktop` in the activated environment.

Open **System library** and download the pinned **OrcaSlicer 2.4.2** library.
It works offline afterward. **Check for updates** reports newer stable GitHub
releases; it does not replace your library, engine, drafts or sets.

Search/filter profiles and inspect **Resolved settings** and **Source JSON**.
The source column identifies which ancestor supplies a setting. Drag the divider
to resize the list/settings sections. Resolved values include saved ancestor
settings, not every internal Orca default.

Generic names do not prove that a record is a hidden template. Creation choices
exclude non-instantiated templates but retain generic selectable profiles.
Missing or ambiguous ancestors block resolution rather than silently returning
incomplete settings.

## 2. Choose your starting workflow

### A. Customize one library profile as a draft

1. Select a usable printer, filament or process in **System library**.
2. Click **Create draft from selected profile…** and give it a unique name.
3. In **My drafts**, click a value to edit it; setting names stay read-only.
4. Changes save automatically as overrides and appear in bold. Use **Reset selected
   setting to starting value** to undo an individual override.
5. Click **Prepare sharing package…** when ready, and review the included members.

Known boolean fields use On/Off; lists display without JSON syntax. Supported
draft reference fields use constrained choices; extruder-aware fields use E0/E1
(and Left/Right for two slots). Numeric checks cover selected settings, not every
Orca rule. Structured values and some compatibility expressions still need
specialized editors.

Drafts freeze their starting values/revision; library changes do not alter them.
**Delete draft…** moves the draft to a recoverable `deleted-drafts` folder after
confirmation. Saved packages and installed Orca profiles remain intact.

For explicit control over every printer, material and process in a package,
use a profile set rather than relying on a single draft's dependencies.

### B. Build a complete mix-and-match set

Open **My profile sets**, click **New set**, and name it. The wizard saves incomplete
work automatically. Back/Next let you revisit each stage.

1. **Printers:** choose **Add from library**, **Add from drafts**, or **Create from
   scratch…**. Filter library choices by vendor, model and nozzle variant.
   Selecting a record shows its actual ancestry. Name each independent copy.
2. Add more printers as needed. **Duplicate as variant…** copies a member, then
   lets you edit its settings. Renaming it “0.8” does not change the nozzle!
   Review printer model, printer variant, nozzle values, dimensions and extruder
   settings explicitly. Grouping uses metadata, not name parsing.
3. **Filaments:** add/copy/create materials, including ones originally associated
   with another printer. Review physical suitability before assigning them.
4. **Processes:** add/copy/create processes with settings appropriate to each
   nozzle and printer variant.
5. **Assignments and review:** open **Assign profiles and defaults…**. Each printer
   has its own page. Check its allowed filaments/processes, choose a default
   filament per extruder, and choose a default process.
6. Click **Prepare and install…**, review warnings and package contents, then
   create the package. Accept or decline the subsequent installation prompt.

Example: Standard 0.4, Standard 0.8, XL 0.4 and XL 0.8 can share one PLA profile.
Assign the 0.4 process only to the 0.4 printers and the 0.8 process only to the 0.8
printers. Assigned non-default profiles are included too.

Missing defaults, stale references and unassigned members block packaging.
Supported review warnings cover diameter/layer-height inconsistencies.
**Remove selected** removes a copy from the set, not its source or installed
files; repair affected assignments before packaging again. Library-derived
copies and duplicated variants retain source metadata in the project.

### C. Start from scratch

**Create from scratch…** currently offers basic forms for:

- Rectangular, front-left-origin FFF printers with one or two extruders.
- Filament material, diameter, flow and supported nozzle/bed temperatures.
- Process layer heights, walls, infill and basic speeds.

Supply machine-specific start/end G-code and right-extruder offsets for dual
printers. Other build plates, motion limits, hardware capabilities and omitted
settings need review in Orca. These are starter forms—not every Orca setting or
printer architecture. Do not print using fictional test fixtures.

## 3. Prepare, install and verify

Packages save automatically under `%LOCALAPPDATA%\SlicerProfileLab\sharing`,
using the draft/set name with a unique suffix when needed. Routine creation does
not ask for a save location.

| File | Purpose |
| --- | --- |
| Prepared `.orca_bundle` | Profile Lab's installation input; may retain supporting parents internally |
| Sharing `.zip` | Send to recipients; self-contained ordinary user profiles |

1. Close Orca before accepting installation. Profile Lab rechecks before writing;
   unknown process status blocks installation.
2. Confirm the preview. The current button writes to
   `%APPDATA%\OrcaSlicer\user\default\machine`, `filament` and `process`.
3. Name collisions are refused rather than overwritten. Use a new copy name;
   this is not an installed-profile update/uninstall manager.
4. Open Orca and select the new **User** printer. Confirm the intended filament
   and process are available and selected; check both slots on dual printers.
5. Switch nozzle variants if applicable and check the process again. Orca can
   choose Generic PLA instead of the assigned default—check the filament explicitly.
6. Review hardware settings and G-code before printing. Installation success does
   not certify print safety.

If installation was declined, use **Install prepared package into OrcaSlicer…**
in **My drafts**. It uses the latest prepared package in the current app session;
after restarting Profile Lab, select the saved `.orca_bundle` when prompted.

Installation resolves saved ancestor values into independent user profiles with
empty `inherits`. Source history stays in Profile Lab; recipients do not need
hidden ancestors installed. Originals stay unchanged. Unsaved Orca internal
defaults are not frozen into the package.

**Portable/custom Orca:** configurable installation targets are planned. The
current install button always targets the normal default user folder. Instead,
import the sharing ZIP through the intended isolated Orca instance.

## 4. Share with another person

1. Find the generated `.zip` in the sharing folder. The draft workflow also
   offers **Open saved package folder**.
2. Send that ZIP.
3. The recipient uses **File → Import → Import Configs** in Orca—not model import.
4. Select the imported User printer, check filament/process choices, and close
   and reopen Orca to verify persistence.

**Do not substitute Orca's `.orca_printer` re-export.** In stock 2.4.2 and the
pinned 2.5.0-dev tests, the bundle files imported but their compatibility links
were lost. “Imported three configs” alone does not prove the profiles work
together. Profile Lab's ZIP passed recipient selection and restart checks.

## 5. Check profiles and read the result

In **Check profiles**:

- **Check my OrcaSlicer profiles** targets the normal installed user location.
- **Choose folder… / Check selected folder** checks a separate profile tree.
  Standalone checks may report parents that exist outside that tree as missing.
- Windows Alpha 2 includes the validator and matching resources, without replacing
  your Orca installation. No engine download is needed. **Validation engine information**
  shows its status; future engine updates are delivered with Profile Lab releases.

Built-in checks cover JSON structure, names, duplicates, parents and cycles;
recognized complete system trees receive additional ID/reference checks.
Read-only validation does not edit profiles and may run while Orca is open.

Read the engine status as well as the built-in summary. Missing engine, startup
failure or missing matching source resources means full validation did not run.
Compiled `.opc` files alone cannot replace source JSON. User-profile engine
checks cover loading/inheritance, not slicing. A missing system parent can mean
the validation library does not match the source: do not remove inheritance
merely to silence that message.

Package checks, native loading and print safety are distinct. Review temperatures,
motion limits, dimensions, filament diameter, extruder mapping and G-code yourself.

## 6. Stable and development testing

The production library remains **2.4.2**. Separate tests used clean **2.5.0-dev**
at `f520e9221f220657f752d269ead37dd61e9cb0c3`, not a final 2.5.0 release.

The maintainer's **Start Orca 2.5 Test.cmd** expects a specific local build path
and supplies an isolated `--datadir`. The build is not included in this repository.
For a separately built Orca, an empty `data_dir` beside `orca-slicer.exe` also
starts a separate configuration when launching that executable directly.
An explicit `--datadir` overrides it; subsequent launches reuse the saved data.

Both tested versions support single-extruder nozzle switching. System models can
show short grouped names; user presets need not use the same display behavior.
The development legacy-dual fixture has a blank nozzle-control limitation;
complete new dual/flow-variant UI support is not certified.

As of September 17, 2026, 159 Profile Lab tests passed with optional integrations
enabled, alongside 55 upstream Python ID tests and 104 native profile tests.
Profile Lab ZIP recipient selection and restart passed in both tested versions.
See the [audit](docs/upstream-variant-audit.md) for exact setup, fixture results
and limitations. This is not coverage of every vendor/hardware configuration.

## Planned next steps—not available yet

- Full settings pages organized like Orca, with comprehensive enums, units,
  help, limits, structured editors and version-aware schema checks.
- Broader scratch/family tools and newer dual/flow-variant support.
- Existing user profiles as direct starting points and broader reference choices.
- Reviewed library/engine upgrades, version selection, change review and rollback.
- Easier matched engine/source setup and actionable validation explanations.
- Portable/cloud-account/custom installation destinations.
- Package/set cleanup, broader installed-profile management and signed public
  desktop releases. A private Windows alpha installer now bundles Python;
  see the [alpha testing guide](docs/alpha-testing.md).

In **Add from library**, use **All filament brands** to filter by the material
manufacturer (for example, Polymaker). Brand values include inherited settings,
so searching `Polymaker` also finds products named PolyLite or PolyTerra.
**All profile sources** is a separate filter for the library bundle, such as BBL,
Qidi, or OrcaFilamentLibrary. Neither filter changes compatibility or inheritance.
For filaments, **All library locations** can be narrowed to **Shared filament
library** (OrcaFilamentLibrary) or **Printer-vendor libraries**. This describes
file location only: shared-library entries may still target specific printers.
Exact profiles show whether their resolved settings contain printer links,
conditional restrictions, or no explicit printer restriction. None of these
labels certify print suitability. Checked selections remain selected across filters.

To delete an entire saved set, choose it in **My profile sets**, click
**Delete set…** beside the saved-set selector, and confirm. This moves its saved
file to `%LOCALAPPDATA%\SlicerProfileLab\sets\deleted\<backup-id>\`.
To restore it, close Profile Lab and move that JSON file back into `sets` without
overwriting an existing file. Original drafts and library profiles are unchanged.

Draft deletion, set deletion, and removing a set member do not delete
exported packages or uninstall profiles. There is no general package cleanup or
uninstall button yet. See the [README](README.md) for the roadmap and current
limits. No release dates are promised.
# Updating Profile Lab itself

Open Help → Check for updates and click Check now. No application update checks
run automatically. If offered, click Download update; Profile Lab verifies the
download against the release checksum. Open the downloaded installer folder,
close Profile Lab, and run setup. This is separate from the system-library update
check. Alpha/beta builds see newer previews; stable builds see stable releases.

## Selecting several profiles and reviewing recommendations

In a set's Filaments or Processes step, use Add from library (or Add from drafts)
and check several profiles. Checked choices survive searches and vendor filters;
switching category clears them. Printers remain single-selection per addition.
Batch additions show a scrollable name review and create independent copies only
after confirmation. No defaults are chosen automatically.

Recommended choices appear first; Recommended only narrows the list. Reasons use
explicit printer/process links, original defaults, or matching filament diameters.
Printer diameter may be inferred from an unambiguous original default filament;
nozzle size is never used as filament diameter. Missing metadata yields no
recommendation, not a claim of incompatibility. Orca condition expressions are not
evaluated by these suggestions. Review temperatures, nozzle suitability and G-code.

Assignments decide which profiles are available to each printer. Defaults select
the initial filament per extruder and process; they do not remove other choices.
Package review shows these links and initial selections alongside package contents.

### Filament families

The set picker groups filaments by their source vendor and explicit filament ID.
Expand a material family to inspect its exact profiles, including legacy base-named
entries. No files are removed and grouping never changes inheritance or JSON names.
The family checkbox selects visible variants with explicit links to your set's
printers, preferring narrower printer lists over broad legacy lists. Diameter-only
recommendations are not automatically selected. Without explicit links, expand the
family and check variants manually. Turn off Group filament families for the flat
list. These are selection suggestions, not a guarantee of Orca's runtime switching
or hardware suitability; review the package assignments before installing.

### Before packaging a multi-nozzle set

The wizard shows how many assignment/default items remain. Prepare and install
opens a complete, scrollable checklist if the set is incomplete, with a shortcut
to Assign profiles and defaults. Incomplete sets remain saved for later.

Review also warns when a numeric printer variant disagrees with its nozzle
diameters; it does not silently rewrite either value. Automated tests cover a
same-model 0.4/0.8 dual-extruder set through save/reopen, packaging, sharing ZIP,
and isolated file installation. Actual nozzle switching and import behavior in
Orca still require testing in the target Orca version.
