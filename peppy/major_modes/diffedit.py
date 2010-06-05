# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Diff editing support.

Major mode for editing diffs.
"""

import os, re
import keyword
from cStringIO import StringIO

import wx
import wx.stc

from peppy.actions import *
from peppy.major import *
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import *


class NextDiff(SelectAction):
    """Scroll to view the next diff."""
    name = "Next Diff"
    default_menu = ("Tools", 252)
    key_bindings = {'default': 'S-M-n'}

    def action(self, index=-1, multiplier=1):
        stc = self.mode
        start = stc.GetCurrentPos()
        end = stc.GetTextLength()
        while True:
            pos = stc.FindText(start, end, "--- ", 0)
            self.dprint("start=%d end=%d pos=%d" % (start, end, pos))
            if pos < 0:
                self.dprint("not found")
                break
            if stc.GetColumn(pos) == 0 and pos != start:
                line = stc.LineFromPosition(pos)
                stc.showLine(line)
                break
            start = pos + 1

class PrevDiff(SelectAction):
    """Scroll to view the previous diff."""
    name = "Prev Diff"
    default_menu = ("Tools", 253)
    key_bindings = {'default': 'S-M-p'}

    def action(self, index=-1, multiplier=1):
        stc = self.mode
        start = stc.GetCurrentPos()
        end = 0
        while True:
            pos = stc.FindText(start, end, "--- ", 0)
            if pos < 0:
                self.dprint("not found")
                break
            if stc.GetColumn(pos) == 0 and pos != start:
                line = stc.LineFromPosition(pos)
                stc.showLine(line)
                break
            start = pos - 1

class DiffEditMode(SimpleFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing Diffs.
    
    """
    # keyword is required: it's a one-word name that must be unique
    # compared to all other major modes
    keyword = 'DiffEdit'
    editra_synonym = 'Diff File'
    stc_lexer_id = wx.stc.STC_LEX_DIFF
    start_line_comment = '--- '
    end_line_comment = ''
    
    # Specifying an icon here will cause it to be displayed in the tab
    # of any file using the Diff mode
    icon='icons/diff.png'
    
    fold_function_match = ["diff "]
    
    default_classprefs = (
        StrParam('extensions', 'diff patch', fullwidth=True),
        BoolParam('use_tab_characters', False),
        BoolParam('word_wrap', False),
        )
    
    autoindent = NullAutoindent()
    
    @classmethod
    def verifyMagic(cls, header):
        # Diff files always use pairs of lines like this:
        #
        # --- /path/to/one/file
        # +++ /path/to/another/file
        #
        # to indicate the start of a diff block.  If that pattern exists, assume
        # that it is a diff file.
        lines = header.splitlines()
        found_minuses = False
        for line in lines:
            if found_minuses:
                return line.startswith("+++ ")
            if line.startswith("--- "):
                found_minuses = True
        return False
    
    def getFoldEntryPrettyName(self, start, text):
        text = text[len(start):]
        if text[0] == '-':
            pos = text.find(' ')
            if pos > 0:
                text = text[pos+1:]
        return text


class DiffPlugin(IPeppyPlugin):
    """Diff plugin to register modes and user interface.
    """
    # This registers the diff mode so that it can be used
    def getMajorModes(self):
        yield DiffEditMode
    
    # Only the actions that appear in getActions will be available
    def getCompatibleActions(self, modecls):
        if issubclass(modecls, DiffEditMode):
            return [NextDiff, PrevDiff,
                   ]

