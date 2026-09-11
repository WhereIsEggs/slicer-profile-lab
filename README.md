# Slicer Profile Lab

A Python command-line tool for checking OrcaSlicer profile folders.

## Desktop preview

Install the optional desktop interface in the activated virtual environment:

    python -m pip install -e ".[desktop]"

Launch the native window:

    profilelab-desktop

Alternatively, run `python -m profilelab.desktop`.
Choose a folder and click **Check profiles**. Validation runs in the background.
On Windows, the folder picker starts at `%APPDATA%\OrcaSlicer\user\default`
when it exists, falling back to `%APPDATA%\OrcaSlicer`, then your home folder.
Once a folder is selected,
the picker starts there. Custom or portable locations can be selected manually.
Opening the picker does not scan profiles. Choose a profile folder rather than
the entire configuration directory, which can contain unrelated JSON files.
This first desktop version reads profiles only; it does not yet create, edit,
export, or install profiles. It reports OrcaSlicer process status, but read-only
checks remain available while OrcaSlicer is open.

Future installation actions must recheck that OrcaSlicer is closed immediately
before writing. Unknown process status blocks installation. Process detection
is a snapshot, not a lock preventing OrcaSlicer from starting afterward.
The planned profile builder targets OrcaSlicer 2.4.2 and will follow its settings
organization; this preview does not yet certify 2.4.2 import compatibility.

The planned builder will offer separate **System profile** and **User profile**
starting points, with source-specific folder selection. System locations must
be detected from the installation; user profiles default to the location above,
with manual selection for cloud account or custom locations. Building from a
profile will create a new draft without modifying the source. This builder
workflow is not implemented in the current validation preview.

## System library preview

The desktop **System library** tab downloads and searches the official OrcaSlicer
2.4.2 profiles pinned to revision `8500fcdccaa10b5099ac20d252af3a7c560046f1`.
The initial download is a full upstream source ZIP; only profile JSON is indexed.
The temporary source archive is removed after indexing. The catalog is stored
under `%LOCALAPPDATA%\SlicerProfileLab\libraries` and works offline afterward.
The source URL, revision, download date, and integrity hashes are recorded beside it.
Downloads are staged before publication; an incomplete download is never activated.

Search by name, vendor, or parent and filter by profile type. The preview displays
stored source settings and a read-only **Resolved settings** table. The table
combines explicitly stored values along the parent chain and identifies inherited,
overridden, locally defined, and same-as-parent values with their source profile.
It does not include OrcaSlicer's internal application defaults or normalize values.
Parent lookup uses vendor and profile type, with shared OrcaFilamentLibrary fallback
for filaments. Missing or ambiguous parents and cycles prevent displaying a partial
result. Source JSON remains available in a separate tab. Vendor manifests are excluded
from the profile list, and base templates remain available for inspection. This
library is separate from OrcaSlicer's installed `.opc` files and may differ from
installed profile updates. It does not yet certify import
compatibility, generate profiles, check for newer releases, or offer rollback controls.
Public upstream profiles are attributed to OrcaSlicer (AGPL-3.0); see the source
and license link recorded in `source.json`.

## Command-line usage

With the project's virtual environment activated, run:

    profilelab <profile-folder>

The tool searches the selected folder and its subfolders for JSON files.

Example using fictional test profiles:

    profilelab tests/fixtures/valid_parent

## Current checks

- Missing parent profiles referenced by `inherits`
- Duplicate profile names
- Malformed JSON
- JSON content that is not an object
- Missing, empty, whitespace-only, or non-string profile names
- Folder paths that do not exist or are not directories
- Folders containing no JSON files
- Inheritance cycle detection

Errors include the affected file paths where applicable.

## Exit codes

- `0`: validation completed without finding problems
- `1`: validation found a problem or could not complete

In PowerShell, run `$LASTEXITCODE` immediately after the command
to see its exit code.

## Tests

Run the automated tests with:

    python -m unittest discover -s tests

Fixtures use fictional profiles. Do not add internal profile exports
unless they have been explicitly sanitized for this project.

## Current limitations

Parents must exist within the selected folder tree. The tool does
not look for parents in OrcaSlicer's built-in profiles.

Malformed JSON or an invalid profile structure stops validation
at the first such file.
