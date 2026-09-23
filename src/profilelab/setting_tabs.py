# SPDX-License-Identifier: AGPL-3.0-only
"""Presentation-only tabs; row indices continue to identify original JSON keys."""
from PySide6.QtWidgets import QTabBar
from profilelab.orca_setting_layout import LAYOUT


def ordered_keys(kind, keys):
    rank = {key: i for i, (key, _, _) in enumerate(LAYOUT.get(kind, []))}
    return sorted(keys, key=lambda k: (rank.get(k, len(rank)), k))


class SettingTabs(QTabBar):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.keys = []
        self.mapping = {}
        self.kind = ''
        self.pages_by_kind = {}
        self.query = ''
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.currentChanged.connect(self.apply)

    def configure(self, kind, keys):
        if self.kind and self.currentIndex() >= 0:
            self.pages_by_kind[self.kind] = self.tabText(self.currentIndex())
        self.kind = kind
        previous = self.pages_by_kind.get(kind, '')
        self.blockSignals(True)
        while self.count():
            self.removeTab(0)
        self.keys = list(keys)
        self.mapping = {key: (page, group) for key, page, group in LAYOUT.get(kind, [])}
        pages = list(dict.fromkeys(page for _, page, _ in LAYOUT.get(kind, [])))
        if any(k not in self.mapping for k in keys):
            pages.append('Other settings')
        for page in pages:
            self.addTab(page)
        if previous in pages:
            self.setCurrentIndex(pages.index(previous))
        self.blockSignals(False)
        self.setVisible(bool(keys))
        self.apply()

    def apply(self, *_ , query=None):
        page = self.tabText(self.currentIndex())
        if query is not None:
            self.query = query.casefold().strip()
        query = self.query
        for row, key in enumerate(self.keys):
            item = self.table.item(row, 0)
            label = item.text() if item else key
            # Search spans all tabs so a matching setting is never silently hidden.
            visible = query in (key + ' ' + label).casefold() if query else self.mapping.get(key, ('Other settings', ''))[0] == page
            self.table.setRowHidden(row, not visible)
            if item:
                group = self.mapping.get(key, ('Other settings', ''))[1]
                if group and not item.toolTip().startswith(group + '\n'):
                    item.setToolTip(group + '\n' + item.toolTip())
