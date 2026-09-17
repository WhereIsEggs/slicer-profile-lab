# Slicer Profile Lab — copyright and licensing

Copyright (C) 2026 WhereIsEggs, for original Profile Lab contributions.

Slicer Profile Lab is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License, version 3, as
published by the Free Software Foundation (SPDX: AGPL-3.0-only).

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See LICENSE.txt for the full terms.

Project and contact: https://github.com/WhereIsEggs/slicer-profile-lab

## OrcaSlicer attribution and modifications

Profile Lab incorporates adaptations of OrcaSlicer's profile-validation and
identity rules, and test vectors. Upstream work remains copyright its original
OrcaSlicer contributors; this notice does not claim ownership of their work.
OrcaSlicer is distributed under AGPL v3:
https://github.com/OrcaSlicer/OrcaSlicer/blob/main/LICENSE.txt

Relevant upstream references include `scripts/orca_id_tool.py`,
`tests/libslic3r/test_preset_setting_id.cpp`, and
`src/dev-utils/OrcaSlicer_profile_validator.cpp`. The identity reference is
commit `5c635d5e504c5f88d45ff7f0d66b63a83382d0bc`:
https://github.com/OrcaSlicer/OrcaSlicer/tree/5c635d5e504c5f88d45ff7f0d66b63a83382d0bc

The newer locally audited snapshot `f520e9221f220657f752d269ead37dd61e9cb0c3`
names the Python tool `scripts/orca_profile_tool.py`; its C++ identity test
contains the same vectors used by Profile Lab. The earlier filename above is
retained as the historical reference recorded in Profile Lab's implementation.

Profile Lab adaptations, documented September 17, 2026:

- `src/profilelab/orca_rules.py` and `system_checks.py`: Python implementations
  of deterministic IDs and selected system-profile checks, integrated with
  Profile Lab's error reporting rather than upstream's command-line workflow.
- `tests/test_orca_rules.py`: selected upstream identity vectors used as
  compatibility regression tests.
- Starting with Alpha 2, the fixed native Orca validator and matching resources
  are bundled and invoked on temporary copies. See packaging/ORCA-ENGINE-NOTICES.md.

The optional profile library is drawn from OrcaSlicer 2.4.2, commit
`8500fcdccaa10b5099ac20d252af3a7c560046f1`. Vendor/profile names and third-party
materials retain their original ownership and applicable notices. Profile Lab
is not an official OrcaSlicer product and implies no endorsement.

## Scope and corresponding source

The project license covers original code, tests, build scripts and documentation,
except where a file states otherwise. Dependencies retain their own licenses;
see packaging/THIRD-PARTY-NOTICES.md (installed as THIRD-PARTY-NOTICES.md).
Merely using Profile Lab does not automatically license your independently
created profiles under AGPL; copied upstream material keeps its applicable terms.

Each release includes a matching source ZIP, build instructions, and dependency
sources. Installed copies also contain `_internal/profilelab-source.zip` and
`_internal/dependency-sources`. See docs/licensing.md for redistribution steps.
No additional noncommercial, no-redistribution or no-modification restrictions
are imposed. The alpha label describes maturity, not a limitation on license rights.
