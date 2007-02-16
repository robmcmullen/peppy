# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""
Function list minor mode.  Any major mode that supplies information in
its getFunctionList method will be able to work with this minor mode.
"""

import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *

from peppy.pype.codetree import hierCodeTreePanel

class FuncList(MinorMode):
    keyword="funclist"

    default_settings = {
        'best_width':150,
        'best_height':500,
        'min_width':100,
        'min_height':100,
        }
    
    def createWindows(self, parent):
        self.funclist=hierCodeTreePanel(self.major,parent,False)
        self.fl=self.major.getFunctionList()
        self.funclist.new_hierarchy(self.fl[0])

        paneinfo=self.getDefaultPaneInfo("Function List")
        paneinfo.Right()
        if not self.fl[0]:
            paneinfo.Hide()
        self.major.addPane(self.funclist,paneinfo)
        

class FuncListProvider(Component):
    implements(IMinorModeProvider)

    def getMinorModes(self):
        yield FuncList
