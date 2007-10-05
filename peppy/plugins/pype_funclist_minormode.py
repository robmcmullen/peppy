# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""
Function list minor mode.  Any major mode that supplies information in
its getFunctionList method will be able to work with this minor mode.
"""

import os

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.stcinterface import STCProxy
from peppy.menu import *

import peppy.pype
from peppy.pype.codetree import hierCodeTreePanel

class PyPEFuncList(MinorMode, hierCodeTreePanel):
    keyword="pype_funclist"

    default_classprefs = (
        IntParam('best_width', 150),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        )

    @classmethod
    def worksWithMajorMode(self, mode):
        if hasattr(mode, 'getFunctionList'):
            return True
        return False
    
    def __init__(self, major, parent):
        hierCodeTreePanel.__init__(self, self, parent, False)

        self.major = major
        self.fl=self.major.getFunctionList()
        self.new_hierarchy(self.fl[0])

    def paneInfoHook(self, paneinfo):
        paneinfo.Caption("PyPE Function List")
        if not self.fl[0]:
            paneinfo.Hide()

    def getNumWin(self, evt=None):
        """PyPE compat"""
        s = STCProxy(self.major.stc)
        s.format = self.major.stc.getLinesep()
        return 1,s
        

class PyPEFuncListPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield PyPEFuncList
