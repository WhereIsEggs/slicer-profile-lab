"""Conservative profile-reference choices from the draft's pinned library."""

from collections import Counter
from profilelab.resolver import ProfileResolver, ResolutionError


def compatible_filaments(draft, snapshot):
    if not snapshot or snapshot["metadata"].get("revision") != draft["library"].get("revision"):
        return []
    if draft["type"] != "machine":
        return []
    profiles = snapshot["profiles"]
    resolver = ProfileResolver(profiles)
    counts = Counter(p["name"] for p in profiles if p["type"] == "filament" and not p.get("template", True))
    result = []
    for profile in profiles:
        if profile["type"] != "filament" or profile.get("template", True) or counts[profile["name"]] != 1:
            continue
        # Shared-library exclusions are defined outside individual profiles.
        # Until that metadata is supported, do not promise compatibility.
        if profile["vendor"] == "OrcaFilamentLibrary":
            continue
        try:
            values = {k: v.value for k, v in resolver.resolve(profile).items()}
        except ResolutionError:
            continue
        printers = values.get("compatible_printers", [])
        condition = values.get("compatible_printers_condition", "")
        # Fail closed for expressions: never evaluate upstream text as Python.
        if condition or not isinstance(printers, list):
            continue
        if draft["base"]["name"] in printers:
            result.append(profile["name"])
    return sorted(result, key=str.casefold)
