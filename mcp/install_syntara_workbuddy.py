#!/usr/bin/env python3
"""Compatibility wrapper for the Syntara WorkBuddy installer."""

from __future__ import annotations

import sys

from syntara import main


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--uninstall" in args:
        args = [arg for arg in args if arg != "--uninstall"]
        raise SystemExit(main(["uninstall", "workbuddy", *args]))
    raise SystemExit(main(["install", "workbuddy", *args]))
