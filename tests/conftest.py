"""Headless Qt defaults for CI and automated widget tests."""
import os
import sys

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
