"""Manual GUI test input; fictional data only, no installation or app launch."""
from pathlib import Path
from uuid import uuid4
from test_scratch_profiles import scratch_fixture
from profilelab.scratch_profiles import scratch_values
from profilelab.profile_sets import new_set, add_copy, prepare_set
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_sharing import share_prepared_package

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1] / 'artifacts' / 'scratch-import-check'
    root.mkdir(parents=True, exist_ok=True)
    data = new_set('Scratch GUI check')
    for kind, values in scratch_fixture().items():
        add_copy(data, kind, 'Scratch GUI ' + kind, scratch_values(kind, values), '2.4.2')
    data['defaults'] = dict(filaments=['Scratch GUI filament'] * 2, process='Scratch GUI process')
    profiles = prepare_set(data)
    package = root / (uuid4().hex + '.orca_bundle')
    export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
    print(share_prepared_package(package))
