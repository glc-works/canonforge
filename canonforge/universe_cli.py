#!/usr/bin/env python3
"""
OKF STUDIO: UNIVERSE CLI & AUTHOR EXPERIENCE RUNNER (ax)
--------------------------------------------------------------------------------
Seamless backward-compatible proxy delegating 100% to CanonForge Unified CLI (cf).
Ensures zero feature drift between 'cf' and './ax'.
"""
import sys
from canonforge.cli.main import main
from canonforge.engines.verifier import verify_universe
from canonforge.core.manifest import find_universe_root

if __name__ == "__main__":
    main()
