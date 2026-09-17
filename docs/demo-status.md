# Real-product presentation — September 15, 2026

The user corrected the scope: demonstrate the normal public library → draft →
package → installation workflow, not a fictional demo. Use `Start Profile Lab.cmd`
and `Real Workflow Guide.md`. The earlier fictional work below is historical.

Current verified result: **121 tests passed**, including optional public-library
desktop workflow and native Orca loading checks. The real Prusa MK3S package
uncovered and fixed empty-string compatibility serialization in upstream parents.
Package copies normalize those empty lists; source records are unchanged.

The normal installation button reuses the just-created package without a file
picker. Installation confirmation groups the contents, and success names the
printer to select in Orca. After confirming Orca closed, the real public-derived
`Profile Lab Workshop MK3S` package was installed additively into
`user/default/_local/profilelab_39e1ff3b971c4f5a80b1c6f57de5c997`:
one printer, one filament, one process, seven supporting parents (10 files).
Existing profiles were not replaced. A final real GUI dropdown check remains necessary.

Continue improving the REAL workflow, keeping all installations additive and
guarded by the Orca process check. Do not upgrade upstream versions during the
presentation. Freeze changes when the user starts presenting.

## Historical fictional-sandbox work

Final verified result: **118 tests passed**, with both optional native Orca tests
enabled. The whitespace check passed. Demo CLI startup was exercised in an
isolated offscreen process and exited cleanly.

## Completed scope

1. Inspected the existing worktree and verified the baseline: 107 tests passed.
2. Implemented a safe offline presentation mode, consistent desktop styling,
   searchable draft settings, grouped package preview, constrained default-profile
   selectors, per-extruder labels, and narrow numeric-input guards.
3. Rehearsed the actual Qt controls: create a draft, edit both extruders, save,
   preview, create a package, and reopen/check the generated archive. Native Orca
   loading tests verify every expected profile is loaded, including the ten-profile
   demonstration package. Screenshots were rendered from the actual widgets and
   visually reviewed; this was not a manual Windows GUI import rehearsal.
4. Added `Start Demo.cmd`, the project-root `Demo Guide.md`, and six fallback
   screenshots in the ignored `artifacts/demo` directory.

## Safeguards

- No production Orca user profile was installed, replaced, migrated, or deleted.
- Demo mode cannot run installation or engine downloads, even through direct
  handler calls. Its packages are marked as fictional and rejected by the normal
  Profile Lab installer.
- Each launch gets an isolated, persistent, timestamped demo workspace.
- Source profiles remain unchanged. Cancel does not create a package; repeated
  saves reserve a new filename rather than overwriting.
- Demo checks are labeled built-in checks; full upstream validation is not claimed.
- Full native source-library validation still needs source JSON paired with the
  validator runtime. That is intentionally not a presentation prerequisite.
- All work is uncommitted. Existing unfinished changes were preserved.

## Recheck

```powershell
$env:PROFILELAB_NATIVE_TESTS = '1'
$env:PROFILELAB_DEMO_SCREENSHOTS = Join-Path (Get-Location) 'artifacts\demo'
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Without the native-test flag, the optional native tests are skipped. Desktop
tests need the existing desktop dependencies. No new package was installed for
this demo work.

## Follow-up boundaries

The following boundaries applied to the superseded fictional sandbox. Only make small, tested improvements to
demo usability, recovery, and documentation before the presentation. Do not
attempt risky upstream upgrades, broad refactors, or real profile installations.
When the user begins presenting, freeze changes to the demonstration.
