# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Compatibility entry point: engine installation is now owned by the app installer."""
from profilelab.engine_validator import validator_path, validation_engine_resources, is_complete_profile_tree


def install_engine(progress=lambda message: None):
    executable = validator_path()
    if not executable.is_file() or not is_complete_profile_tree(validation_engine_resources() / 'profiles'):
        raise ValueError('Reinstall Profile Lab to restore its included validation engine. '
                         'No nightly download is needed. Source developers must configure a matching engine/resources pair.')
    progress('The included Orca validation engine is ready.')
    return executable
