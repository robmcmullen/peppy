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

class _autoload_img_dict(object):
    def __init__(self):
        self.icons = getIconStorage()

    def __getitem__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        icon = self.icons.get("icons/spe/" + name)
        self.__dict__[name] = icon
        return icon
    

class _SPECompat(object):
    def __init__(self):
        self.iconsListIndex = _autoload_img_dict()


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
