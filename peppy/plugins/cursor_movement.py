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


class GotoLine(MinibufferAction):
    """Goto a line number.
    
    Use minibuffer to request a line number, then go to that line in
    the stc.
    """
    alias = "goto-line"
    name = "Goto Line..."
    tooltip = "Goto a line in the text."
    default_menu = ("Tools", -250)
    key_bindings = {'default': 'C-g', 'emacs': 'M-g'}
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
        mode.showLine(line - 1)


class MarkerAction(SelectAction):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'MarkerAdd')

class SetBookmark(MarkerAction):
    """Set a bookmark on the current line in the buffer."""
    alias = "set-bookmark"
    name = "Set Bookmark"
    default_menu = (("Tools/Bookmarks", 251), 100)
    key_bindings = {'emacs': 'C-c C-b C-s'}

    def action(self, index=-1, multiplier=1):
        line = self.mode.GetCurrentLine()
        self.mode.MarkerAdd(line, self.mode.bookmark_marker_number)

class ToggleBookmark(MarkerAction):
    """Toggle a bookmark on the current line in the buffer."""
    alias = "toggle-bookmark"
    name = "Toggle Bookmark"
    default_menu = (("Tools/Bookmarks", 251), 110)
    key_bindings = {'default': 'M-b', 'emacs': 'C-c C-b C-b'}

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
    key_bindings = {'emacs': 'C-c C-b C-d'}

    def action(self, index=-1, multiplier=1):
        line = self.mode.GetCurrentLine()
        self.mode.MarkerDelete(line, self.mode.bookmark_marker_number)

class NextBookmark(MarkerAction):
    """Scroll to view the next bookmark."""
    alias = "next-bookmark"
    name = "Next Bookmark"
    default_menu = ("Tools/Bookmarks", -200)
    key_bindings = {'default': 'M-n', 'emacs': 'C-c C-b C-n'}

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
    key_bindings = {'default': 'M-p', 'emacs': 'C-c C-b C-p'}

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
        return [GotoLine,
                
                SetBookmark, ToggleBookmark, DelBookmark,
                NextBookmark, PrevBookmark,
            ]
