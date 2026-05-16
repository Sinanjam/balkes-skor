#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balkes TFF Factory v3.5 — targeted safe chain wrapper.

v3.5 keeps the v3.3 targeted senior/professional extraction rules and adds
safe-chain/finalisation around the generated data.  The heavy extraction logic
lives in tff_factory_v33_targeted_professional.py; importing it patches the base
factory, then we only stamp the version before running.
"""
from __future__ import annotations

import tff_factory_v33_targeted_professional  # noqa: F401
import tff_factory as base

base.FACTORY_VERSION = "v3.5-targeted-safe-chain"

if __name__ == "__main__":
    raise SystemExit(base.main())
