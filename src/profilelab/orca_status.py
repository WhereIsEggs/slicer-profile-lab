# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Read-only process checks; never terminate OrcaSlicer."""

from enum import Enum

import psutil


class OrcaStatus(Enum):
    CLOSED = "closed"
    RUNNING = "running"
    UNKNOWN = "unknown"


def get_orca_status() -> OrcaStatus:
    uncertain = False
    try:
        for process in psutil.process_iter():
            try:
                name = process.name().lower()
                if name in {"orcaslicer", "orcaslicer.exe", "orca-slicer", "orca-slicer.exe"}:
                    return OrcaStatus.RUNNING
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                uncertain = True
    except psutil.Error:
        return OrcaStatus.UNKNOWN
    return OrcaStatus.UNKNOWN if uncertain else OrcaStatus.CLOSED


def require_orca_closed() -> None:
    """Future install actions must call this immediately before writing."""
    status = get_orca_status()
    if status is OrcaStatus.RUNNING:
        raise RuntimeError("Close OrcaSlicer before installing profiles, then check again.")
    if status is OrcaStatus.UNKNOWN:
        raise RuntimeError("Could not confirm OrcaSlicer is closed. Installation is blocked.")
