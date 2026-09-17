# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Private application drafts, not OrcaSlicer export files."""

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from profilelab.library import library_home


def drafts_home():
    return library_home().parent / "drafts"


def delete_draft(root, original):
    """Move exactly one unchanged draft to a recoverable private trash folder."""
    root = Path(root).resolve()
    identity = str(UUID(original['id']))
    source = root / f'{identity}.json'
    if source.resolve().parent != root or source.is_symlink():
        raise ValueError('Linked draft files cannot be deleted.')
    if json.loads(source.read_text(encoding='utf-8')) != original:
        raise ValueError('This draft changed. Refresh drafts before deleting it.')
    trash = root / 'deleted'
    if trash.resolve() != trash:
        raise ValueError('Linked deleted-drafts folder is not supported.')
    trash.mkdir(exist_ok=True)
    destination = trash / f'{identity}-{uuid4().hex}.json'
    source.rename(destination)
    return destination


def load_drafts(root):
    drafts, errors = [], []
    if not root.exists():
        return drafts, errors
    for path in sorted(root.glob("*.json")):
        try:
            draft = json.loads(path.read_text(encoding="utf-8"))
            if (draft.get("format_version") != 1 or not isinstance(draft.get("name"), str)
                    or not isinstance(draft.get("base_values"), dict)
                    or not isinstance(draft.get("base"), dict)
                    or not isinstance(draft.get("library"), dict)
                    or draft.get("type") not in {"machine", "filament", "process"}):
                raise ValueError("Unsupported draft format")
            drafts.append(draft)
        except (OSError, ValueError, AttributeError) as error:
            errors.append(f"{path.name}: {error}")
    return drafts, errors


def create_draft(root, name, profile, metadata, resolver):
    name = name.strip()
    if not name or any(ord(char) < 32 for char in name):
        raise ValueError("Enter a name containing visible text and no control characters.")
    if profile["type"] not in {"machine", "filament", "process"}:
        raise ValueError("Choose a printer variant, filament, or process to create a draft.")
    if name.casefold() == profile["name"].casefold():
        raise ValueError("Choose a different name from the system profile.")
    existing, errors = load_drafts(root)
    if any(item["name"].casefold() == name.casefold() and item["type"] == profile["type"] for item in existing):
        raise ValueError("A draft of this type already uses that name.")
    resolved = resolver.resolve(profile)
    draft = {
        "format_version": 1, "id": str(uuid4()), "name": name, "type": profile["type"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "library": {key: metadata[key] for key in ("version", "revision")},
        "base": {key: profile[key] for key in ("name", "vendor", "path")},
        "base_profile": deepcopy(profile["settings"]),
        "base_chain": deepcopy(resolver.chain(profile)),
        "base_values": {key: deepcopy(value.value) for key, value in resolved.items()},
        "base_sources": {key: {"name": value.source_name, "vendor": value.source_vendor,
                                "path": value.source_path} for key, value in resolved.items()},
        "overrides": {},
    }
    root.mkdir(parents=True, exist_ok=True)
    # A random internal filename makes user-entered names safe on every platform.
    destination = root / f"{draft['id']}.json"
    descriptor, temporary = tempfile.mkstemp(prefix="draft-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(draft, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return draft


def save_override(root, original, key, value, reset=False):
    """Save one draft change atomically, refusing stale or mismatched files."""
    identity = str(UUID(original["id"]))
    destination = root / f"{identity}.json"
    current = json.loads(destination.read_text(encoding="utf-8"))
    if current != original:
        raise ValueError("This draft changed since it was opened. Refresh drafts before editing.")
    if key not in current["base_values"]:
        raise ValueError("Unknown setting.")
    base = current["base_values"][key]
    if not reset:
        if type(value) is not type(base):
            raise ValueError("The value must keep the setting's original type.")
        if isinstance(base, list) and (len(value) != len(base) or any(type(a) is not type(b) for a, b in zip(value, base))):
            raise ValueError("Keep the same number and types of values.")
    updated = deepcopy(current)
    if reset or value == base:
        updated["overrides"].pop(key, None)
    else:
        updated["overrides"][key] = deepcopy(value)
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    descriptor, temporary = tempfile.mkstemp(prefix="edit-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(updated, output, indent=2, ensure_ascii=False, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return updated
