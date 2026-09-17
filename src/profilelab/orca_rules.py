# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
# Orca-derived rules/vectors adapted for Profile Lab; modified 2026-09-17.
"""Pinned Orca identity primitives; system IDs are NOT user/cloud IDs.

Reference: OrcaSlicer scripts/orca_id_tool.py and test_preset_setting_id.cpp
at RULES_REVISION. Standard-library implementation; no downloaded code execution.
"""

from uuid import UUID, uuid5

RULES_REVISION = "5c635d5e504c5f88d45ff7f0d66b63a83382d0bc"
NAMESPACE = UUID("c1f4d9e2-7a3b-5c8d-9e0f-1a2b3c4d5e6f")
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _tail(value, length):
    digits = []
    for _ in range(length):
        value, remainder = divmod(value, 62)
        digits.append(ALPHABET[remainder])
    return "".join(reversed(digits))


def system_setting_id(vendor, kind, name):
    """Compute a vendor-system ID, not an ID for a local user draft."""
    if not vendor or not kind or not name:
        return ""
    return _tail(uuid5(NAMESPACE, f"{vendor}/{kind}/{name}").int, 16)


def system_filament_id(vendor, material, product_name):
    """Accept the upstream normalized product triple (no printer suffix)."""
    if not all(isinstance(v, str) and v.strip() for v in (vendor, material, product_name)):
        raise ValueError("A filament product needs a vendor, material and product name.")
    namespace = uuid5(NAMESPACE, "filament_id")
    return "OF" + _tail(uuid5(namespace, f"filament_product/{vendor}/{material}/{product_name}").int, 6)


def check_system_setting_id(vendor, profile):
    """Check only the system setting-ID rule; not whole-tree validation."""
    if "settings_id" in profile:
        raise ValueError("Use setting_id, not settings_id.")
    value = profile.get("setting_id", "")
    if profile.get("instantiation") != "true":
        if value:
            raise ValueError("System base profiles must not carry setting_id.")
    elif not isinstance(value, str) or not value:
        raise ValueError("Instantiated system profiles require setting_id.")
    elif vendor != "BBL" and value != system_setting_id(vendor, profile["type"], profile["name"]):
        raise ValueError("System setting_id does not match vendor, type and name.")
