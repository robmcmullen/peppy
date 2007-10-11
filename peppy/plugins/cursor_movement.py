# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.menu import *
from peppy.actions.base import *
from peppy.debug import *


class BeginningOfLine(ScintillaCmdKeyExecute):
    alias = _("beginning-of-line")
    name = _("Cursor to Start of Line")
    tooltip = _("Move the cursor to the start of the current line")
    cmd = wx.stc.STC_CMD_HOMEDISPLAY
        
class BeginningTextOfLine(ScintillaCmdKeyExecute):
    alias = _("beginning-text-of-line")
    name = _("Cursor to first non-blank character in the line")
    tooltip = _("Move the cursor to the start of the current line")
    key_bindings = {'emacs': 'C-A',}
    cmd = wx.stc.STC_CMD_VCHOME
        
class EndOfLine(ScintillaCmdKeyExecute):
    alias = _("end-of-line")
    name = _("Cursor to End of Line")
    tooltip = _("Move the cursor to the end of the current line")
    key_bindings = {'emacs': 'C-E',}
    cmd = wx.stc.STC_CMD_LINEEND

class PreviousLine(ScintillaCmdKeyExecute):
    alias = _("previous-line")
    name = _("Cursor to previous line")
    tooltip = _("Move the cursor up a line")
    key_bindings = {'emacs': 'C-P',}
    cmd = wx.stc.STC_CMD_LINEUP

class NextLine(ScintillaCmdKeyExecute):
    alias = _("next-line")
    name = _("Cursor to next line")
    tooltip = _("Move the cursor down a line")
    key_bindings = {'emacs': 'C-N',}
    cmd = wx.stc.STC_CMD_LINEDOWN

class BeginningOfBuffer(SelectAction):
    alias = _("beginning-of-buffer")
    name = _("Cursor to first character in the buffer")
    tooltip = _("Move the cursor to the start of the buffer")
        
    def action(self, index=-1, multiplier=1):
        self.mode.stc.DocumentStart()

class EndOfBuffer(SelectAction):
    alias = _("end-of-buffer")
    name = _("Cursor to end of the buffer")
    tooltip = _("Move the cursor to the end of the buffer")
        
    def action(self, index=-1, multiplier=1):
        self.mode.stc.DocumentEnd()



class CursorMovementPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    default_keys=((None, BeginningOfLine),
                  (None, BeginningTextOfLine),
                  (None, EndOfLine),
                  (None, PreviousLine),
                  (None, NextLine),
                  (None, BeginningOfBuffer),
                  (None, EndOfBuffer),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)
