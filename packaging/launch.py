# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Frozen desktop entry point; smoke mode never opens real user data."""
import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from profilelab.packaged_smoke import run_smoke
        raise SystemExit(run_smoke(sys.argv[2]))
    from profilelab.desktop import main
    raise SystemExit(main())
