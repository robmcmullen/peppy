# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Wrapper and utility functions around SPE.

This module provides a wrapper around SPE.  Currently, it provides the
SPECompat object that can be used in place of the parentPanel to
provide the icon list.
"""

import os, os.path

import info

from peppy.debug import *
from peppy.lib.iconstorage import *

from peppy.about import AddCredit

SPECompat = None

class _SPECompat(object):
    def __init__(self):
        icons = getIconStorage()
        self.iconsListIndex = {}
        
        spedir = os.path.dirname(__file__)
        dprint(spedir)
        for filename in os.listdir(spedir):
            dprint("name=%s type=%s" % (filename, filename.__class__))
            if filename.endswith(".png"):
                self.iconsListIndex[filename] = icons.get(filename, spedir)


if SPECompat is None:
    SPECompat = _SPECompat()

    AddCredit("Stani Michiels", "for SPE (GPL Licensed, Copyright (c) 2003-2005 www.stani.be), and the pyxides mailing list.")

__all__ = ['SPECompat', 'info']
