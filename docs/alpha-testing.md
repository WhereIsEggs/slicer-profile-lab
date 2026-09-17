# Alpha 1 testing guide

Version: **0.1.0 Alpha 1** · Publisher: **WhereIsEggs** · Windows x64

Licensed under **AGPL-3.0-only**, without warranty. Copyright (C) 2026 WhereIsEggs
for original contributions; upstream attribution is in NOTICE.md. The installer
and matching source ZIP should be shared together. **Help → License and source
code** provides offline access to the license and installed source location.

This is the real app, packaged with Python and Qt. You do not need Python, a
development checkout or a locally built Orca to use it. The installer does not
include Orca, the system profile library, or its optional validator engine.

## Before testing

1. Back up your Orca profile/configuration directory. Use clearly unique test
   profile names; do not replace working production profiles.
2. Run the setup executable. It installs for your account without requesting
   administrator privileges, and adds a Start menu entry. Desktop shortcut is optional.
3. The build is unsigned. If Windows or your organization blocks installation,
   do not disable protection; ask the publisher/IT for a reviewed distribution route.
4. Existing Profile Lab drafts/sets/cache are reused. To test a fresh computer
   experience, use a separate Windows test account or VM.

## Suggested test pass

- Open every tab and resize the window. Note clipped controls or confusing wording.
- Download the system library; search/filter by vendor, model and nozzle variant.
  Check the displayed inheritance chain against a profile you know.
- Create a draft, edit a boolean/number/G-code value, reset a setting, restart,
  and confirm saved changes. Delete only the test draft; its backup is retained.
- Create a set containing two printer variants, shared filament and separate
  processes. Try library copies, duplication and scratch forms.
- Assign profiles/defaults per printer. Try an incomplete set and confirm it
  explains what prevents packaging. Review all safety warnings.
- Prepare the package. Verify automatic naming and the generated sharing ZIP.
- Close Orca, install test profiles, reopen Orca and inspect printer, filament and
  process choices. Review actual values; do not print merely because validation passed.
- Import the Profile Lab ZIP on another test computer. Select each printer/nozzle,
  confirm the intended materials/processes, and repeat after restarting Orca.
- Exercise read-only validation. Note built-in results separately from engine status.
  The optional engine/source setup may report incomplete validation.

For portable Orca, import the ZIP through that instance. The install button
currently targets the normal `%APPDATA%\OrcaSlicer\user\default` folder.

## Known limits

- Share the Profile Lab ZIP, not an Orca re-exported `.orca_printer` bundle:
  compatibility links failed in tested stock 2.4.2 and pinned 2.5.0-dev imports.
- Production library is pinned to 2.4.2. Update checking does not upgrade it.
- Full Orca settings pages, all enums/ranges and every printer architecture are
  not implemented. New dual/flow-variant UI support remains incomplete.
- Printer switching can choose Generic PLA instead of the default you assigned.
- Built-in validation passing does not mean full engine validation ran. User
  engine checks cover loading/inheritance, not slicing or hardware safety.
- No automatic update, overwrite, migration or general profile uninstall manager.

## Report findings

Use https://github.com/WhereIsEggs/slicer-profile-lab/issues or send findings to
the publisher. Include:

- Profile Lab version, Windows version, Orca version and normal/portable setup.
- Exact steps, expected result, actual result, and a screenshot/error text.
- Whether the problem persists after restart.
- A minimal **sanitized** public/fictional profile or ZIP if necessary.

Do not post proprietary profiles, API keys, personal paths or machine network
addresses. No automatic issue submission or telemetry is included.

## Uninstall / recovery

Close Profile Lab, then use Windows Installed apps → Slicer Profile Lab Alpha →
Uninstall. Application files and shortcuts are removed. Your Profile Lab workspace
under `%LOCALAPPDATA%\SlicerProfileLab` and all Orca profiles remain untouched.
The installer does not back up Orca for you; preserve your backup separately.

The source and [workflow guide](../Real%20Workflow%20Guide.md) describe the real
workflow. This is an early-testing build, not a production-ready or print-certified release.
