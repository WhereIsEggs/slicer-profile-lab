"""Share ordinary root user presets without Orca's bundle namespace."""

from copy import deepcopy
import json
from pathlib import Path
import zipfile

from profilelab.profile_install import _safe_name, IDENTITIES, MANIFEST_FIELDS
from profilelab.user_install import exportable_profiles
from profilelab.bundle_contract import strict_json


def write_user_zip(profiles, destination):
    """No bundle_structure.json: Orca imports these into the user collection."""
    destination = Path(destination)
    if destination.suffix.lower() != ".zip":
        raise ValueError("Use a .zip filename for user profiles.")
    profiles = deepcopy(profiles)
    names = {(p['type'], p['name']) for p in profiles}
    if len(names) != len(profiles) or not profiles:
        raise ValueError("Empty or duplicate profile set.")
    for profile in profiles:
        _safe_name(profile['name'])
        if profile.get('inherits'):
            raise ValueError("Sharing requires self-contained profiles without parents.")
        for field, kind in [('compatible_printers', 'machine'), ('default_filament_profile', 'filament'), ('default_print_profile', 'process')]:
            refs = profile.get(field, [])
            if isinstance(refs, str):
                refs = [refs] if refs else []
            if not isinstance(refs, list) or any((kind, ref) not in names for ref in refs):
                raise ValueError(f"Unresolved {field} in {profile['name']}.")
    # Unique basenames also accommodate Orca's temporary flat extraction folder.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for number, profile in enumerate(sorted(profiles, key=lambda p: p['type'] != 'machine')):
            archive.writestr(f"profile_{number:04d}.json", json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False))
    return destination


def share_prepared_package(package):
    package = Path(package)
    destination = package.with_suffix('.zip')
    number = 2
    while destination.exists():
        destination = package.with_name(f'{package.stem} ({number}).zip')
        number += 1
    return write_user_zip(exportable_profiles(package), destination)


def repair_stock_export(source, destination):
    """Read a stock export without extracting files or changing the original."""
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(e.file_size for e in entries) > 64 * 1024 * 1024:
            raise ValueError('Archive is too large.')
        if len({e.filename for e in entries}) != len(entries):
            raise ValueError('Duplicate archive entries.')
        manifest = strict_json(archive.read('bundle_structure.json'))
        profiles = []
        for field, kind in MANIFEST_FIELDS.items():
            for entry in manifest[field]:
                profile = strict_json(archive.read(entry))
                profile['type'] = kind
                identity = IDENTITIES[kind]
                expected = [profile['name']] if kind == 'filament' else profile['name']
                if profile.get(identity) != expected:
                    raise ValueError('Profile identity mismatch.')
                profiles.append(profile)
    return write_user_zip(profiles, destination)
