# Superseded: fictional sandbox guide

For the requested real-product presentation, use **Real Workflow Guide.md** and
**Start Profile Lab.cmd** instead. The instructions below describe only the
optional fictional sandbox, which does not support installation.

## Start here

Double-click **Start Demo.cmd** in this project folder.

The app opens maximized with a blue **DEMO** banner and a fictional dual-extruder
printer already selected. No download, internet connection, or running OrcaSlicer
is needed. This mode cannot install profiles into OrcaSlicer. Its generated
packages are marked as fictional; Profile Lab also refuses to install them in normal mode.

If double-clicking does not open the app, run this in the project's VS Code terminal:

```powershell
.\.venv\Scripts\python.exe -m profilelab.desktop --demo
```

Each launch has a separate workspace under
`%LOCALAPPDATA%\SlicerProfileLab\demo`. Drafts and packages remain there after the
window closes. The **Open saved package folder** button finds the current package.

## The story to tell

“Orca profiles are connected to other profiles. A file can look valid by itself
but fail when someone else imports it because its dependencies are missing.
Profile Lab is designed to make those relationships manageable without asking
people to edit JSON.”

## 1. Start from an existing profile — about 45 seconds

The **System library** tab is open with **Demo Dual Printer 0.4 nozzle** selected.
The banner and note explicitly identify these as fictional examples; do not
present them as manufacturer-approved profiles.

- Point out the human-readable settings and their inherited origins.
- Click **Create draft from selected profile…**.
- Name it **Workshop Printer** and confirm.

“The original stays unchanged. We work on a saved draft.”

## 2. Customize the draft — about one minute

The app switches to **My drafts** automatically.

- In **Find a setting…**, type **retraction length**.
- Click the value, not the setting name.
- Change **E0 / Left** to **1.2** and **E1 / Right** to **1.0**. Click **Save**.
- Point out the bold changed value and the **Draft saved** message.
- Clear the search. Optionally click **Default filament profile** to show the
  constrained dropdowns for each extruder, then **Cancel**.

“Users edit values, not JSON or dependency keys. Changes are saved to the draft.”

These values illustrate the interface only; they are not printing recommendations.

## 3. Prepare a complete package — about one minute

- Click **Prepare sharing package…**.
- The preview shows **1 printer, 2 filaments, and 1 process**.
- Expand **Supporting parents** to show the six profiles that preserve ancestry.
- Explain that these are supporting profiles, not six extra target printers.
- Click **Create package**.
- Point out **Workshop Printer.orca_bundle** and the automatic-save message.
- Optionally click **Open saved package folder** to show the generated file.

“The package builder includes the connected profiles and keeps their parent
chains. It names and saves the file for us.”

Do not import this fictional package into a production Orca setup during the demo.
The demo does not claim the package has passed every Orca check.

## 4. Show the original problem being caught — about 45 seconds

- Open **Check profiles**.
- Click **Try a valid profile set**; the built-in checks pass.
- Click **Find a missing parent**; the actual validator reports the missing parent.

“This catches a broken relationship before someone tries to use the profile.”

## Close honestly

“The library-to-draft editor, dependency-aware packaging, and built-in checks
are working. We are still completing full upstream validation and testing the
installation/import round trip across supported Orca versions.”

## What is and isn't demonstrated

Working in this presentation: real draft creation and persistence, per-extruder
editing, read-only setting names, constrained profile choices, actual package
generation, and real built-in validation of fictional files.

Not demonstrated: print quality, all Orca settings, manufacturer certification,
complete nightly-vendor validation, or a production-ready import/export guarantee.
The installed validator still needs a matching source JSON library for full checks.

## Backup if screen sharing or launching fails

The rendered rehearsal screenshots are in **artifacts/demo**:

1. `01-library.png`
2. `02-extruder-editor.png`
3. `03-saved-draft.png`
4. `04-package-preview.png`
5. `05-package-created.png`
6. `06-missing-parent-check.png`

These show the actual app widgets used during the automated click-through,
not design mockups. They are generated locally and excluded from Git.

## Recovery during the presentation

- Cancelling an editor or package preview leaves the existing data alone.
- If **Workshop Printer** already exists in this launch, use **Workshop Printer 2**.
- Creating another package never overwrites the previous one; the filename gains a number.
- Closing and restarting the demo opens a fresh workspace. Your earlier files remain
  in the previous timestamped folder.
- Normal mode remains available with `profilelab-desktop` (without `--demo`).
