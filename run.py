#!/usr/bin/env python
"""
Main driver program for the peppy editor.
"""

import os,sys

# Set default translation as a no-op for the moment (the actual translation is
# performed on-demand during the GUI creation, not at application start time).
import __builtin__
__builtin__._ = unicode

import peppy.main

peppy.main.main()
