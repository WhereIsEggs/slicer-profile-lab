"""Local bundle names and strict JSON shared by the writer and installer."""

from copy import deepcopy
import json
import re

from profilelab.sharing import REFERENCES


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"Invalid JSON number: {value}")

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=invalid)


def bundle_prefix(identity):
    if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity):
        raise ValueError("Invalid bundle ID.")
    return f"_local/{identity}/"


def scope_profiles(profiles, identity, *, unqualify=False):
    """Qualify only in-bundle references; never rewrite compatibility expressions."""
    prefix = bundle_prefix(identity)
    index = {(p["type"], p["name"]) for p in profiles}
    result = deepcopy(profiles)
    for profile in result:
        fields = {**REFERENCES, "inherits": profile["type"]}
        for field, kind in fields.items():
            if field not in profile:
                continue

            def convert(name):
                if not isinstance(name, str):
                    raise ValueError(f"Invalid {field}.")
                if unqualify:
                    return name[len(prefix):] if name.startswith(prefix) else name
                return prefix + name if (kind, name) in index else name

            value = profile[field]
            profile[field] = [convert(n) for n in value] if isinstance(value, list) else convert(value)
    return result
