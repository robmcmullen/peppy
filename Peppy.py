#!/usr/bin/env python
"""
Main driver program for the peppy editor.
"""

import os,sys

# Set default translation as a no-op for the moment (the actual translation is
# performed on-demand during the GUI creation, not at application start time).
import __builtin__
__builtin__._ = unicode

try:
    import peppy.main
except AttributeError:
    raise RuntimeError("Peppy needs wxPython version 2.8.7.1 or later to function.  Minimum recommended version is 2.8.8.0")

peppy.main.main()
