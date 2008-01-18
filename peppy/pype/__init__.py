# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""PyPE compatibility module.

PyPE depends on global variables for some of its configuration, so
insert what it expects into the global namespace.

By adding this code here, I can use PyPE code without modification, so
I can just drop in new replacements as Josiah adds new features to his
code.
"""
import os

from peppy.configprefs import *
from peppy.about import AddCopyright

PyPECompat = None

class _PyPECompat(object):
    # runpath is needed for loading icons and pype config settings.
    # It should point to the peppy module directory.  This file is in
    # the plugins directory, so that directory is one level up.
    runpath=os.path.dirname(os.path.dirname(os.path.normpath(os.path.abspath(__file__))))

if PyPECompat is None:
    PyPECompat = _PyPECompat

    if isinstance(__builtins__, dict):
        __builtins__['_pype'] = PyPECompat()
    else:
        __builtins__._pype = PyPECompat()

    AddCopyright("PyPE", "http://pype.sourceforge.net/", "Josiah Carlson", "2003-2007",
    "Search bar, file browsing sidebar, and other code from")

__all__ = ['PyPECompat']
