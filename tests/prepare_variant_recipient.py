"""Create a fresh, isolated GUI recipient; never read normal Orca user data."""
from hashlib import md5
import json
from pathlib import Path
import shutil
from uuid import uuid4


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1] / 'artifacts'
    sender = root / 'stock-export-test' / 'sender'
    destination = root / 'variant-comparison' / ('recipient-' + uuid4().hex[:8])
    destination.mkdir(parents=True)
    # Only the unrelated public-Prusa fixture; none of the Lab family members.
    for source in (sender / 'user' / 'default').rglob('*'):
        if source.is_file() and 'Workshop Export Check MK3S' in source.name:
            target = destination / source.relative_to(sender)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    text = (sender / 'OrcaSlicer.conf').read_text(encoding='utf-8')
    config = json.JSONDecoder().raw_decode(text)[0]
    config['presets'] = {'machine': 'Workshop Export Check MK3S'}
    config['orca_presets'] = [p for p in config.get('orca_presets', [])
                              if p.get('machine') == 'Workshop Export Check MK3S']
    config['models'] = [{'vendor': 'Prusa', 'model': 'Prusa MK3S',
                         'nozzle_diameter': '0.4;0.8'}]
    payload = json.dumps(config, indent='\t') + '\n'
    checksum = md5(payload.encode('utf-8')).hexdigest().upper()
    (destination / 'OrcaSlicer.conf').write_bytes(
        (payload + '# MD5 checksum ' + checksum + '\n').encode('utf-8'))
    print(destination)
