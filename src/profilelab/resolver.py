"""Resolve explicitly stored profile values, excluding application defaults."""

from copy import deepcopy
from dataclasses import dataclass

# Identity and catalog fields describe a profile, not inherited print settings.
METADATA = {
    "name", "type", "inherits", "from", "instantiation", "setting_id",
    "filament_id", "version", "renamed_from", "description", "alias",
}


class ResolutionError(ValueError):
    pass


@dataclass
class ResolvedSetting:
    value: object
    status: str
    source_name: str
    source_vendor: str
    source_path: str


class ProfileResolver:
    def __init__(self, profiles):
        self.index = {}
        for profile in profiles:
            key = (profile["vendor"], profile["type"], profile["name"])
            self.index.setdefault(key, []).append(profile)

    def parent_of(self, profile):
        parent = profile["settings"].get("inherits", "")
        if parent == "":
            return None
        if not isinstance(parent, str):
            raise ResolutionError(f"Invalid parent reference in {profile['name']}.")
        matches = self.index.get((profile["vendor"], profile["type"], parent), [])
        if not matches and profile["type"] == "filament":
            matches = self.index.get(("OrcaFilamentLibrary", "filament", parent), [])
        if not matches:
            raise ResolutionError(f"Parent '{parent}' was not found for {profile['name']} ({profile['vendor']}).")
        if len(matches) != 1:
            raise ResolutionError(f"Parent '{parent}' is ambiguous within {matches[0]['vendor']}.")
        return matches[0]

    def resolve(self, selected):
        chain = []
        visited = set()
        current = selected
        while current is not None:
            key = (current["vendor"], current["type"], current["path"])
            if key in visited:
                raise ResolutionError(f"Inheritance cycle detected at {current['name']}.")
            visited.add(key)
            chain.append(current)
            current = self.parent_of(current)

        settings = {}
        for profile in reversed(chain):
            for key, value in profile["settings"].items():
                if key in METADATA:
                    continue
                status = "Inherited"
                if profile is selected:
                    if key not in settings:
                        status = "Defined here"
                    elif settings[key].value == value:
                        status = "Same as parent"
                    else:
                        status = "Overridden here"
                settings[key] = ResolvedSetting(
                    deepcopy(value), status, profile["name"], profile["vendor"], profile["path"]
                )
        return settings
