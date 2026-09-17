# Third-party software in the Windows alpha

Publisher of Profile Lab: WhereIsEggs. Profile Lab is not an official OrcaSlicer
or Qt product. Alpha 2 bundles a fixed Orca profile validator and matching validation
resources, not the Orca GUI. See orca-engine/ORCA-ENGINE-NOTICES.md and its LICENSE.txt.
The complete release source ZIP includes the matching Orca and dependency sources.

Profile Lab is AGPL-3.0-only; Copyright (C) 2026 WhereIsEggs for original
contributions. Orca-derived rules and test vectors are attributed in NOTICE.md.
The project license does not replace any dependency's license.

The installed `licenses` folder includes dependency license files and metadata.
The installed `dependency-sources` folder contains matching unmodified Qt Base,
SVG, image-format, PySide/Shiboken and psutil sources, including their third-party notices
and upstream build instructions. Preserve these with redistributed copies.
The unused Qt Virtual Keyboard and PDF image plugins are excluded from this build.

| Component | Version | Upstream / source | License |
| --- | --- | --- | --- |
| CPython | See build-info.json | https://www.python.org/downloads/source/ | PSF and bundled component notices |
| PySide6 / Shiboken6 | 6.11.2 | https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/ | LGPLv3 / GPL alternatives; see upstream notices |
| Qt Core/Gui/Widgets and bundled plugins | 6.11.2 | https://download.qt.io/archive/qt/6.11/6.11.2/submodules/ | LGPLv3 and third-party notices |
| psutil | 7.2.2 | https://github.com/giampaolo/psutil/tree/release-7.2.2 | BSD-3-Clause |
| PyInstaller bootloader | 6.22.0 | https://github.com/pyinstaller/pyinstaller/tree/v6.22.0 | GPL with distribution exception |

Qt/PySide/Shiboken are unmodified, dynamically loaded components. The installed
one-folder layout leaves their DLLs available for replacement with compatible
modified versions. No restriction is imposed on reverse engineering for debugging
modifications to those LGPL components. License texts and copyright notices must
be preserved when redistributing the application. The build includes source/rebuild
instructions for Profile Lab, licensed under AGPL v3 as described in LICENSE.txt.

Inno Setup creates the installer: https://jrsoftware.org/ . Its copyright notices
remain in Setup/Uninstall. Dependency copyrights remain with their authors.

Preserve the matching source archives and these notices when redistributing.
Review third-party source/notice obligations again when dependencies change.
