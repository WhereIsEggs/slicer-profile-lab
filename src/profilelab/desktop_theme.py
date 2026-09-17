"""Consistent native-widget styling for the desktop presentation."""

import os
from pathlib import Path
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette


def apply_theme(app):
    app.setStyle("Fusion")
    # Qt's offscreen Windows plugin does not enumerate system fonts. Register
    # existing Windows fonts for screenshot/rehearsal runs; no fonts are shipped.
    if not QFontDatabase.families():
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf"):
            path = fonts / name
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))
    app.setFont(QFont("Segoe UI", 10))
    palette = app.palette()
    for role, color in ((QPalette.ColorRole.WindowText, "#edf2f7"),
                        (QPalette.ColorRole.Window, "#232a33"),
                        (QPalette.ColorRole.Highlight, "#79b7ff"),
                        (QPalette.ColorRole.Mid, "#344254")):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet("""
        QWidget { background: #232a33; color: #edf2f7; }
        QMainWindow, QDialog { background: #232a33; }
        QLabel { background: transparent; }
        QPushButton { background: #344254; border: 1px solid #53647a;
                      border-radius: 5px; padding: 7px 12px; min-height: 20px; }
        QPushButton:hover { background: #415775; border-color: #79b7ff; }
        QPushButton:pressed { background: #245783; }
        QPushButton:disabled { color: #8995a5; background: #2a323d; border-color: #3b4655; }
        QLineEdit, QComboBox { background: #19212a; border: 1px solid #53647a;
                             border-radius: 4px; padding: 6px; min-height: 22px; }
        QLineEdit:focus, QComboBox:focus { border-color: #79b7ff; }
        QTableWidget, QListWidget, QTreeWidget, QTextEdit, QPlainTextEdit {
            background: #19212a; alternate-background-color: #222e3c;
            border: 1px solid #46566b; gridline-color: #364455;
            selection-background-color: #245c91; selection-color: #ffffff;
        }
        QHeaderView::section { background: #303e50; padding: 6px; border: 0;
                               border-right: 1px solid #46566b; }
        QTabWidget::pane { border: 1px solid #46566b; }
        QTabBar::tab { padding: 10px 20px; background: #2b3543; }
        QTabBar::tab:selected { background: #245c91; color: white; }
        QToolTip { color: #edf2f7; background: #303e50; border: 1px solid #79b7ff; }
    """)
