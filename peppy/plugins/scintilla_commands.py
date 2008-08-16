# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Wrappers around the Scintilla built-in keyboard commands

This plugin is contains actions that wrap the default scintilla editing
commands so that they can be overridden in peppy.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *

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
    
class NextCharacter(ScintillaCmdKeyExecute):
    alias = "next-character"
    name = "Cursor to next character"
    tooltip = "Move the cursor right"
    key_bindings = {'emacs': 'C-F',}
    cmd = wx.stc.STC_CMD_CHARRIGHT

class PreviousCharacter(ScintillaCmdKeyExecute):
    alias = "previous-character"
    name = "Cursor to previous character"
    tooltip = "Move the cursor left"
    key_bindings = {'emacs': 'C-B',}
    cmd = wx.stc.STC_CMD_CHARLEFT
    
class NextWord(ScintillaCmdKeyExecute):
    alias = "next-word"
    name = "Cursor to next word"
    tooltip = "Move the cursor right to the next word break"
    key_bindings = {'emacs': 'M-F',}
    cmd = wx.stc.STC_CMD_WORDRIGHT

class PreviousWord(ScintillaCmdKeyExecute):
    alias = "previous-word"
    name = "Cursor to previous word"
    tooltip = "Move the cursor left to the previous word break"
    key_bindings = {'emacs': 'M-B',}
    cmd = wx.stc.STC_CMD_WORDLEFT


class ScintillaCommandsPlugin(IPeppyPlugin):
    def getActions(self):
        return [BeginningOfLine, BeginningTextOfLine, EndOfLine,
                PreviousLine, NextLine,
                NextCharacter, PreviousCharacter,
                NextWord, PreviousWord,
            ]
