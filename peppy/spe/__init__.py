# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Wrapper and utility functions around SPE.

This module provides a wrapper around SPE.  Currently, it provides the
SPECompat object that can be used in place of the parentPanel to
provide the icon list.
"""

import os, os.path

import info
import sm

from peppy.debug import *
from peppy.lib.iconstorage import *

from peppy.about import AddCredit, AddCopyright

SPECompat = None

class _SPECompat(object):
    def __init__(self):
        icons = getIconStorage()
        self.iconsListIndex = {}
        
        spedir = os.path.dirname(__file__)
        for filename in os.listdir(spedir):
            if filename.endswith(".png"):
                self.iconsListIndex[filename] = icons.get(filename, spedir)


if SPECompat is None:
    SPECompat = _SPECompat()

    AddCredit("Stani Michiels", "for the pyxides mailing list")
    AddCopyright("SPE", "http://www.stani.be", "Stani Michiels", "2003-2005")

def isUtf8(text):
    try:
        if text.startswith('\xef\xbb\xbf'):
            return True
        else:
            return False
    except:
        return False

__all__ = ['SPECompat', 'isUtf8', 'info', 'sm']
