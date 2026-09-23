# SPDX-License-Identifier: AGPL-3.0-only
"""Extract static setting order from the pinned Orca UI source."""
import pathlib
import re
import pprint
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
source = (root / 'src/slic3r/GUI/Tab.cpp').read_text(encoding='utf-8')
# Remove comments while preserving string literals (including URLs).
source = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                lambda m: m[0] if m[0].startswith('"') else '', source)

def body(name):
    start = source.index('void ' + name + '(')
    end = source.find('\nvoid ', start + 5)
    return source[start:end if end >= 0 else len(source)]

layouts = {}
for kind, function in [('filament', 'TabFilament::build'), ('process', 'TabPrint::build'), ('machine', 'TabPrinter::build_fff')]:
    text = body(function)
    if kind == 'filament':
        text = text.replace('add_filament_overrides_page();', body('TabFilament::add_filament_overrides_page'))
    text = re.sub(r'for \(const std::string opt_key : \{([^}]+)\}\)',
                  lambda m: '\n'.join('get_option("' + key + '");' for key in re.findall(r'"([^"]+)"', m[1])), text)
    page, group = '', ''
    entries = []
    seen = set()
    pattern = r'add_options_page\(L\("([^"]+)"\)|new_optgroup\(L\("([^"]+)"\)|(?:append_single_option_line|get_option)\("([^"]+)"|create_line_with_widget\(optgroup.get\(\), "([^"]+)"'
    for match in re.finditer(pattern, text):
        p, g, key, widget_key = match.groups()
        if p:
            page, group = p, ''
        elif g:
            group = g
        else:
            key = key or widget_key
            if page and key not in seen:
                entries.append((key, page, group))
                seen.add(key)
    layouts[kind] = entries
revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
target = pathlib.Path(__file__).resolve().parents[1] / 'src/profilelab/orca_setting_layout.py'
target.write_text('# SPDX-License-Identifier: AGPL-3.0-only\n# Generated from Orca Tab.cpp; see NOTICE.md.\n'
                  f'SOURCE_REVISION = {revision!r}\nLAYOUT = ' + pprint.pformat(layouts, width=120) + '\n', encoding='utf-8')
print({k: len(v) for k, v in layouts.items()})
