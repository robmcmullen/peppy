# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Includable file that is used to provide a Goto Line function for a
major mode.
"""

import os

import wx
import wx.stc

from peppy.actions.minibuffer import *
from peppy.actions.base import *
from peppy.debug import *


class GotoLine(MinibufferAction):
    """Goto a line number.
    
    Use minibuffer to request a line number, then go to that line in
    the stc.
    """
    alias = "goto-line"
    name = "Goto Line..."
    tooltip = "Goto a line in the text."
    default_menu = ("View", -250)
    key_bindings = {'default': 'C-G', 'emacs': 'M-G'}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Line:"

    def processMinibuffer(self, minibuffer, mode, line):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        mode.GotoLine(line - 1)
