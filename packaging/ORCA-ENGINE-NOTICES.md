# Bundled Orca profile validation engine

OrcaSlicer 2.5.0-dev, revision f520e9221f220657f752d269ead37dd61e9cb0c3.
This is a fixed development snapshot, not a released Orca 2.5.0.
Copyright remains with the OrcaSlicer contributors and its dependency authors.
The engine is unmodified upstream source, built with Visual Studio 2022 x64,
Release, SLIC3R_STATIC=ON, SLIC3R_GUI=ON and ORCA_TOOLS=ON.

OrcaSlicer is licensed under AGPL v3; see the adjacent LICENSE.txt.
No warranty is provided. Profile Lab does not imply upstream endorsement.

The matching Profile Lab release source ZIP includes the exact Orca source
archive and dependency sources, preserving upstream notices, patches and build
recipes. Follow Orca's doc/build instructions in that archive and build the
OrcaSlicer_profile_validator target. The Profile Lab Windows build guide explains
how the reviewed runtime is staged. No signing key is required for modifications.

Only the validator's runtime DLL closure and matching resources/profiles and
resources/info are bundled. No Orca GUI, private data_dir or user's profiles are
included. Engine updates are reviewed as part of Profile Lab releases. The
editor's separately downloaded library can have a different supported version;
it is never silently substituted for this engine's validation resources.
