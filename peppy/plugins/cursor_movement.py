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


class GotoLine(MinibufferAction):
    """Goto a line number.
    
    Use minibuffer to request a line number, then go to that line in
    the stc.
    """
    alias = "goto-line"
    name = "Goto Line..."
    tooltip = "Goto a line in the text."
    default_menu = ("Tools", -250)
    key_bindings = {'default': 'C-G', 'emacs': 'M-G'}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Line:"

    def getInitialValueHook(self):
        line = self.mode.GetCurrentLine()
        return str(line + 1)

    def processMinibuffer(self, minibuffer, mode, line):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        mode.EnsureVisible(line - 1)
        mode.GotoLine(line - 1)


class MarkerAction(SelectAction):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'MarkerAdd')

class SetBookmark(MarkerAction):
    """Set a bookmark on the current line in the buffer."""
    alias = "set-bookmark"
    name = "Set Bookmark"
    default_menu = (("Tools/Bookmarks", 251), 100)
    key_bindings = {'emacs': 'C-C C-B C-S'}

    def action(self, index=-1, multiplier=1):
        line = self.mode.GetCurrentLine()
        self.mode.MarkerAdd(line, self.mode.bookmark_marker_number)

class ToggleBookmark(MarkerAction):
    """Toggle a bookmark on the current line in the buffer."""
    alias = "toggle-bookmark"
    name = "Toggle Bookmark"
    default_menu = (("Tools/Bookmarks", 251), 110)
    key_bindings = {'default': 'M-B', 'emacs': 'C-C C-B C-B'}

    def action(self, index=-1, multiplier=1):
        line = self.mode.GetCurrentLine()
        marker = self.mode.MarkerGet(line)
        mask = 1 << self.mode.bookmark_marker_number
        if marker & mask:
            self.mode.MarkerDelete(line, self.mode.bookmark_marker_number)
        else:
            self.mode.MarkerAdd(line, self.mode.bookmark_marker_number)

class DelBookmark(MarkerAction):
    """Remove a bookmark on the current line in the buffer."""
    alias = "del-bookmark"
    name = "Delete Bookmark"
    default_menu = (("Tools/Bookmarks", 251), 120)
    key_bindings = {'emacs': 'C-C C-B C-D'}

    def action(self, index=-1, multiplier=1):
        line = self.mode.GetCurrentLine()
        self.mode.MarkerDelete(line, self.mode.bookmark_marker_number)

class NextBookmark(MarkerAction):
    """Scroll to view the next bookmark."""
    alias = "next-bookmark"
    name = "Next Bookmark"
    default_menu = ("Tools/Bookmarks", -200)
    key_bindings = {'default': 'M-N', 'emacs': 'C-C C-B C-N'}

    def action(self, index=-1, multiplier=1):
        mask = 1 << self.mode.bookmark_marker_number
        line = self.mode.GetCurrentLine() + 1
        line = self.mode.MarkerNext(line, mask)
        self.dprint("found marker at line %d" % line)
        if line < 0:
            line = self.mode.MarkerNext(0, mask)
        if line > -1:
            self.mode.EnsureVisible(line)
            self.mode.GotoLine(line)

class PrevBookmark(MarkerAction):
    """Scroll to view the previous bookmark."""
    alias = "prev-bookmark"
    name = "Prev Bookmark"
    default_menu = ("Tools/Bookmarks", 210)
    key_bindings = {'default': 'M-P', 'emacs': 'C-C C-B C-P'}

    def action(self, index=-1, multiplier=1):
        mask = 1 << self.mode.bookmark_marker_number
        line = self.mode.GetCurrentLine() - 1
        line = self.mode.MarkerPrevious(line, mask)
        self.dprint("found marker at line %d" % line)
        if line < 0:
            line = self.mode.MarkerPrevious(self.mode.GetLineCount(), mask)
        if line > -1:
            self.mode.EnsureVisible(line)
            self.mode.GotoLine(line)


class CursorMovementPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getActions(self):
        return [BeginningOfLine, BeginningTextOfLine, EndOfLine,
                PreviousLine, NextLine,
                NextCharacter, PreviousCharacter,
                NextWord, PreviousWord,
                BeginningOfBuffer, EndOfBuffer,
                GotoLine,
                
                SetBookmark, ToggleBookmark, DelBookmark,
                NextBookmark, PrevBookmark,
            ]
