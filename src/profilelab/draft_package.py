"""Prepare saved draft values and their named dependencies for export."""

from copy import deepcopy
import re
from pathlib import Path

from profilelab.orca_bundle import FIELDS, export_orca_bundle
from profilelab.resolver import ProfileResolver
from profilelab.sharing import REFERENCES, DEPENDENCIES, collect_profiles


def normalize_empty_compatibility(values):
    """Public Orca templates also serialize an empty string-vector as ''."""
    for field in ("compatible_printers", "compatible_prints"):
        if values.get(field) == "":
            values[field] = []


def save_named_package(profiles, selected, folder: Path, *, demo=False) -> Path:
    """Save under the displayed name, reserving a new file on every export."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", selected[1]).strip().rstrip(". ")[:100]
    name = name or "Profile Lab"
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "_" + name
    folder.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        suffix = "" if number == 1 else f" ({number})"
        destination = folder / f"{name}{suffix}.orca_bundle"
        try:
            export_orca_bundle(profiles, [selected], destination, demo=demo)
            return destination
        except FileExistsError:
            number += 1


def prepare_draft_profiles(selected_id, drafts, snapshot=None):
    selected = [d for d in drafts if d["id"] == selected_id]
    if len(selected) != 1:
        raise ValueError("Refresh and select a saved draft.")
    draft_index, library_index = {}, {}
    for draft in drafts:
        draft_index.setdefault((draft["type"], draft["name"]), []).append(draft)
    library = snapshot["profiles"] if snapshot else []
    for profile in library:
        if profile["type"] in FIELDS:
            library_index.setdefault((profile["type"], profile["name"]), []).append(profile)
    resolver = ProfileResolver(library)
    result = {}
    target_printer = selected[0]["name"] if selected[0]["type"] == "machine" else None
    ancestors = {}

    def add_chain(chain, version):
        """Copy actual ancestors, keeping vendor-qualified lookup and material IDs."""
        parent_name = ""
        for record in reversed(chain):
            source = (record["vendor"], record["type"], record["name"])
            name = f"{record['name']} - {record['vendor']} base"
            identity = (record["type"], name)
            values = deepcopy(record["settings"])
            normalize_empty_compatibility(values)
            for _, _, field in FIELDS.values():
                values.pop(field, None)
            for field in ("setting_id", "settings_id", "alias", "renamed_from"):
                values.pop(field, None)
            # Startup choices on a template are not additional package selections.
            for field in DEPENDENCIES:
                values.pop(field, None)
            values.update(name=name, type=record["type"], version=version,
                          inherits=parent_name, instantiation="false", **{"from": "User"})
            values[FIELDS[record["type"]][2]] = [name] if record["type"] == "filament" else name
            if identity in ancestors and ancestors[identity] != (source, values):
                raise ValueError(f"Conflicting saved parent snapshots for '{name}'.")
            ancestors[identity] = (source, values)
            parent_name = name
        return parent_name

    def saved_chain(draft):
        if "base_chain" in draft:
            chain = draft["base_chain"]
            if not isinstance(chain, list) or not chain:
                raise ValueError("The saved parent chain is incomplete. Recreate this draft.")
            # Resolve the frozen snapshot itself to detect missing parents/cycles.
            return ProfileResolver(chain).chain(chain[0])
        if not draft.get("base"):
            return []  # A deliberately standalone, from-scratch draft.
        if not snapshot or draft["library"] != {k: snapshot["metadata"].get(k) for k in draft["library"]}:
            raise ValueError("This older draft needs its original library revision to recover its parents. Recreate it from the library.")
        base = draft["base"]
        matches = [p for p in library if p["vendor"] == base["vendor"] and p["type"] == draft["type"] and p["name"] == base["name"] and p["path"] == base["path"]]
        if len(matches) != 1 or matches[0]["settings"] != draft.get("base_profile"):
            raise ValueError("The original draft parent cannot be verified. Recreate this draft.")
        return resolver.chain(matches[0])

    def visit(key, vendor=None):
        if key in result:
            return
        matches = draft_index.get(key, [])
        if len(matches) > 1:
            raise ValueError(f"Multiple drafts are named '{key[1]}'. Rename one before sharing.")
        if matches:
            draft = matches[0]
            values = deepcopy(draft["base_values"])
            values.update(deepcopy(draft.get("overrides", {})))
            version = draft["library"]["version"]
            chain = saved_chain(draft)
            vendor = draft.get("base", {}).get("vendor", vendor)
            if key[0] == "filament" and any(k in draft.get("overrides", {}) for k in ("filament_vendor", "filament_type")):
                raise ValueError("Changing the material vendor or type needs a new product identity. Keep the original material identity for this package.")
        else:
            matches = library_index.get(key, [])
            if vendor:
                local_matches = [p for p in matches if p["vendor"] == vendor]
                if not local_matches and key[0] == "filament":
                    local_matches = [p for p in matches if p["vendor"] == "OrcaFilamentLibrary"]
                matches = local_matches
            if len(matches) != 1:
                raise ValueError(f"Dependency '{key[1]}' is missing or ambiguous. Create a uniquely named draft for it first.")
            pin = selected[0]["library"]
            if any(snapshot["metadata"].get(k) != v for k, v in pin.items()):
                raise ValueError("The dependency library changed since this draft was created. Use its original library revision or recreate the draft.")
            values = {k: deepcopy(v.value) for k, v in resolver.resolve(matches[0]).items()}
            version = snapshot["metadata"]["version"]
            chain = resolver.chain(matches[0])
            vendor = matches[0]["vendor"]
        normalize_empty_compatibility(values)
        for _, _, identity in FIELDS.values():
            values.pop(identity, None)
        # Do not turn every customized profile into an unrelated root.
        for field in ("setting_id", "settings_id", "inherits", "from", "instantiation"):
            values.pop(field, None)
        parent = add_chain(chain, version)
        if key[0] == "filament":
            material_id = next((p["settings"]["filament_id"] for p in chain if p["settings"].get("filament_id")), values.get("filament_id"))
            if material_id:
                values["filament_id"] = material_id
        values.update(name=key[1], type=key[0], version=version, inherits=parent, **{"from": "User"})
        values[FIELDS[key[0]][2]] = [key[1]] if key[0] == "filament" else key[1]
        if target_printer and key[0] in {"filament", "process"}:
            # Compatibility is an allowed-printer list, not a request to export
            # every printer on it. Scope only these package copies to the target.
            # Keep expressions intact; Orca gives the explicit list precedence.
            values["compatible_printers"] = [target_printer]
        result[key] = values
        for field, kind in DEPENDENCIES.items():
            refs = values.get(field, [])
            if isinstance(refs, str):
                refs = [refs] if refs else []
            if not isinstance(refs, list) or any(not isinstance(n, str) or not n for n in refs):
                raise ValueError(f"Invalid {field} in '{key[1]}'.")
            for name in refs:
                visit((kind, name), vendor)

    key = (selected[0]["type"], selected[0]["name"])
    visit(key)
    if set(result) & set(ancestors):
        raise ValueError("A selected profile name conflicts with a packaged parent.")
    if target_printer:
        # Package-specific identities avoid shadowing the original system presets.
        names = {identity: f"{identity[1]} - {target_printer}"
                 for identity in result if identity[0] in {"process", "filament"}}
        for identity, profile in result.items():
            if identity in names:
                profile["name"] = names[identity]
                profile[FIELDS[identity[0]][2]] = ([profile["name"]] if identity[0] == "filament" else profile["name"])
            for field, kind in REFERENCES.items():
                if field not in profile:
                    continue
                value = profile[field]
                if isinstance(value, list):
                    profile[field] = [names.get((kind, name), name) for name in value]
                elif isinstance(value, str):
                    profile[field] = names.get((kind, value), value)
    return collect_profiles(list(result.values()) + [v for _, v in ancestors.values()], [key]), key


def export_draft_package(selected_id, drafts, snapshot, destination):
    profiles, selected = prepare_draft_profiles(selected_id, drafts, snapshot)
    export_orca_bundle(profiles, [selected], destination)
    return profiles
