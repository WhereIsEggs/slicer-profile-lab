# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Keep a frozen app's bundled DLL search path out of external Orca processes."""
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import sys
from threading import RLock

_launch_lock = RLock()


@contextmanager
def external_dll_search():
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        yield
        return
    with _launch_lock:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetDllDirectoryW.argtypes = (ctypes.c_uint32, ctypes.c_wchar_p)
        kernel.GetDllDirectoryW.restype = ctypes.c_uint32
        kernel.SetDllDirectoryW.argtypes = (ctypes.c_wchar_p,)
        kernel.SetDllDirectoryW.restype = ctypes.c_int
        size = kernel.GetDllDirectoryW(0, None)
        buffer = ctypes.create_unicode_buffer(size + 1)
        kernel.GetDllDirectoryW(len(buffer), buffer)
        previous = buffer.value or None
        if not kernel.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            if not kernel.SetDllDirectoryW(previous):
                raise ctypes.WinError(ctypes.get_last_error())


def external_environment(executable):
    environment = os.environ.copy()
    paths = environment.get('PATH', '').split(os.pathsep)
    if getattr(sys, 'frozen', False):
        bundle = Path(sys._MEIPASS).resolve()
        paths = [p for p in paths if p and not Path(p).resolve().is_relative_to(bundle)]
        for key in ('QT_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
            environment.pop(key, None)
    environment['PATH'] = str(executable.parent) + os.pathsep + os.pathsep.join(paths)
    return environment
