import os

from menu import *
from debug import *
from trac.core import *
from minor import *

from pype.codetree import hierCodeTreePanel

class FuncList(MinorMode):
    keyword="funclist"

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
