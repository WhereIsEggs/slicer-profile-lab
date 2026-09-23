"""Generate presentation metadata from a pinned Orca PrintConfig.cpp checkout.

Usage: python scripts/generate_setting_labels.py CHECKOUT
Only literal assignments are extracted; no C++ code is executed.
"""
import ast
import pathlib
import pprint
import re
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
source = (root / 'src/libslic3r/PrintConfig.cpp').read_text(encoding='utf-8')
blocks = list(re.finditer(r'def\s*=\s*this->add\("([^"]+)"', source))
metadata = {}
for i, match in enumerate(blocks):
    block = source[match.end():blocks[i + 1].start() if i + 1 < len(blocks) else len(source)]
    fields = {}
    for field in ('label', 'full_label', 'tooltip', 'sidetext', 'category'):
        assignment = re.search(r'def->' + field + r'\s*=\s*(?:L\()?\s*((?:"(?:\\.|[^"\\])*"\s*)+)\)?\s*;', block)
        if assignment:
            fields[field] = ''.join(ast.literal_eval(s) for s in re.findall(r'"(?:\\.|[^"\\])*"', assignment[1]))
    if fields.get('label') or fields.get('full_label'):
        metadata[match[1]] = fields
target = pathlib.Path(__file__).resolve().parents[1] / 'src/profilelab/orca_setting_labels.py'
target.write_text('# SPDX-License-Identifier: AGPL-3.0-only\n'
                  '# Generated from OrcaSlicer src/libslic3r/PrintConfig.cpp; see NOTICE.md.\n'
                  f'SOURCE_REVISION = {revision!r}\n'
                  'SETTINGS = ' + pprint.pformat(metadata, width=110, sort_dicts=True) + '\n', encoding='utf-8')
print(f'Generated {len(metadata)} setting labels from {revision}')
