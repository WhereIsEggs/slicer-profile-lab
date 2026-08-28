# Validation Rules

## MVP(minimum viable product): Missing Parent Profiles

The first version of Slicer Profile Lab will inspect a folder of exported OrcaSlicer profiles.

It must:

- Read profile files from a selected folder.
- Identify each profile's name and declared parent profile.
- Report an error when a profile references a parent that does no exist in the provided profile set.
- Show the affected profile name and the missing parent name.

## Not part of the MVP

These will come later:

- Comparing profile revisions
- Validating nozzle, filament fiameter, temperatures, or volumetric flow
- A web interface
- A database
- Editing or repairing profiles automatically
- Create a new profile (printer/filament/processes. should be based on existing data stored in database)

