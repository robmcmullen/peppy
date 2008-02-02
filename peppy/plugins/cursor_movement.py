# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.actions import *
from peppy.actions.base import *
from peppy.debug import *


class BeginningOfLine(ScintillaCmdKeyExecute):
    alias = "beginning-of-line"
    name = "Cursor to Start of Line"
    tooltip = "Move the cursor to the start of the current line"
    key_bindings = {'emacs': 'M-C-A',}
    cmd = wx.stc.STC_CMD_HOMEDISPLAY
        
class BeginningTextOfLine(ScintillaCmdKeyExecute):
    alias = "beginning-text-of-line"
    name = "Cursor to first non-blank character in the line"
    tooltip = "Move the cursor to the start of the current line"
    key_bindings = {'default': 'HOME', 'emacs': 'C-A',}
    cmd = wx.stc.STC_CMD_VCHOME
        
class EndOfLine(ScintillaCmdKeyExecute):
    alias = "end-of-line"
    name = "Cursor to End of Line"
    tooltip = "Move the cursor to the end of the current line"
    key_bindings = {'default': 'END', 'emacs': 'C-E',}
    cmd = wx.stc.STC_CMD_LINEEND

class PreviousLine(ScintillaCmdKeyExecute):
    alias = "previous-line"
    name = "Cursor to previous line"
    tooltip = "Move the cursor up a line"
    key_bindings = {'emacs': 'C-P',}
    cmd = wx.stc.STC_CMD_LINEUP

class NextLine(ScintillaCmdKeyExecute):
    alias = "next-line"
    name = "Cursor to next line"
    tooltip = "Move the cursor down a line"
    key_bindings = {'emacs': 'C-N',}
    cmd = wx.stc.STC_CMD_LINEDOWN

class BeginningOfBuffer(SelectAction):
    alias = "beginning-of-buffer"
    name = "Cursor to first character in the buffer"
    tooltip = "Move the cursor to the start of the buffer"
    key_bindings = {'default': 'C-HOME'}

    def action(self, index=-1, multiplier=1):
        self.mode.DocumentStart()

class EndOfBuffer(SelectAction):
    alias = "end-of-buffer"
    name = "Cursor to end of the buffer"
    tooltip = "Move the cursor to the end of the buffer"
    key_bindings = {'default': 'C-END'}

    def action(self, index=-1, multiplier=1):
        self.mode.DocumentEnd()


class CursorMovementPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getActions(self):
        return [BeginningOfLine, BeginningTextOfLine, EndOfLine, PreviousLine,
            NextLine, BeginningOfBuffer, EndOfBuffer
            ]
