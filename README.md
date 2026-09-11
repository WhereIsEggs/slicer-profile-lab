# Slicer Profile Lab

A Python command-line tool for checking OrcaSlicer profile folders.

## Usage

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

The tool does not yet check inheritance cycles or printing settings.