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
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption("Function List").Right()
        self.fl=self.major.getFunctionList()
        self.funclist.new_hierarchy(self.fl[0])
        if not self.fl[0]:
            paneinfo.Hide()
        self.major.addPane(self.funclist,paneinfo)
##        self.funclist=wx.TextCtrl(parent, -1, "Stuff" , style=wx.TE_MULTILINE)
##        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption("Function List").Right()
##        self.major.addPane(self.funclist,paneinfo)
        

class FuncListProvider(Component):
    implements(IMinorModeProvider)

    def getMinorModes(self):
        yield FuncList
