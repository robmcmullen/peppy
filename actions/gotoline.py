import os

import wx
import wx.stc as stc

from actions.minibuffer import *
from views import *
from plugin import *
from debug import *


class GotoMinibuffer(IntMinibuffer):
    def minibuffer(self, viewer):
        #super(GotoMinibuffer,self).minibuffer(viewer,label="Goto Line:")
        IntMinibuffer.minibuffer(self,viewer,label="Goto Line:")

    def OnInt(self,line):
        # stc counts lines from zero, but displayed starting at 1.
        self.viewer.stc.GotoLine(line-1)
        


class GotoLine(MinibufferAction):
    name = "Goto Line..."
    tooltip = "Goto a line in the text."
    keyboard = 'M-G'
    minibuffer = GotoMinibuffer





if __name__ == "__main__":
    # tests go here
    pass
