# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
PyPE compatibility plugin.  PyPE depends on global variables for some
of its configuration, so insert what it expects into the global
namespace.

By adding this plugin, I can use PyPE code without modification, so I
can just drop in new replacements as Josiah adds new features to his
code.
"""
import os

from peppy import *
from peppy.trac.core import *
from peppy.configprefs import *

from peppy.about import AddCredit
AddCredit("Josiah Carlson for PyPE and for licensing PyPE under the GPL so I could borrow some of his code to create a few of the plugins")

class PyPECompat(object):
    # runpath is needed for loading icons and pype config settings.
    # It should point to the peppy module directory.  This file is in
    # the plugins directory, so that directory is one level up.
    runpath=os.path.dirname(os.path.dirname(os.path.normpath(os.path.abspath(__file__))))


class PyPEConfExtender(Component):
    implements(IConfigurationExtender)

    def loadConf(self,app):
        if isinstance(__builtins__, dict):
            __builtins__['_pype'] = PyPECompat()
        else:
            __builtins__._pype = PyPECompat()
    
    def saveConf(self,app):
        pass
