"""
Includable file that is used to provide a Goto Line function for a
major mode.
"""

import os

import wx
import wx.stc as stc

from actions.minibuffer import *
from major import *
from plugin import *
from debug import *


class GotoMinibuffer(IntMinibuffer):
    """
    Use minibuffer to request a line number, then go to that line in
    the stc.
    """
    
    def create(self, mode):
        """
        Create the minibuffer with the Goto Line label.

        @param mode: the current major mode
        """
        IntMinibuffer.create(self, mode, label="Goto Line:")

    def OnInt(self, line):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        self.mode.stc.GotoLine(line-1)
        


class GotoLine(MinibufferAction):
    name = "Goto Line..."
    tooltip = "Goto a line in the text."
    keyboard = 'M-G'
    minibuffer = GotoMinibuffer

