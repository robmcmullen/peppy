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

from peppy.actions.base import *
from peppy.menu import *
from peppy.debug import *


class ShiftLeft(ScintillaCmdKeyExecute):
    alias = "unindent-region"
    name = "Shift &Left"
    tooltip = "Unindent a line region"
    default_menu = ("Transform", -500)
    icon = 'icons/text_indent_remove_rob.png'
    cmd = wx.stc.STC_CMD_BACKTAB

class ShiftRight(ScintillaCmdKeyExecute):
    alias = "indent-region"
    name = "Shift &Right"
    tooltip = "Indent a line or region"
    default_menu = ("Transform", 501)
    icon = 'icons/text_indent_rob.png'
    cmd = wx.stc.STC_CMD_TAB


class CommentRegion(TextModificationAction):
    alias = "comment-region"
    name = "&Comment Region"
    tooltip = "Comment a line or region"
    default_menu = ("Transform", -600)
    key_bindings = {'emacs': 'C-C C-C',}

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(multiplier != 4)

class UncommentRegion(TextModificationAction):
    alias = "uncomment-region"
    name = "&Uncomment Region"
    tooltip = "Uncomment a line or region"
    default_menu = ("Transform", 601)

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(False)

class Tabify(LineOrRegionMutateAction):
    alias = "tabify"
    name = "&Tabify"
    tooltip = "Replace spaces with tabs at the start of lines"
    default_menu = ("Transform", -700)

    def mutateLines(self, lines):
        out = []
        for line in lines:
            unspace = line.lstrip(' ')
            if len(unspace) < len(line):
                tabs, extraspaces = divmod(len(line) - len(unspace),
                                           self.mode.classprefs.tab_size)
                out.append((tabs)*'\t' + extraspaces*' ' + unspace)
            else:
                out.append(line)
        return out

class Untabify(LineOrRegionMutateAction):
    alias = "untabify"
    name = "&Untabify"
    tooltip = "Replace tabs with spaces at the start of lines"
    default_menu = ("Transform", 701)

    def mutateLines(self, lines):
        out = []
        for line in lines:
            untab = line.lstrip('\t')
            if len(untab) < len(line):
                out.append((len(line) - len(untab))*self.mode.classprefs.tab_size*' ' + untab)
            else:
                out.append(line)
        return out
        



class CapitalizeWord(WordOrRegionMutateAction):
    """Title-case the current word and move the cursor to the start of
    the next word.
    """
    alias = "capitalize-region-or-word"
    name = "Capitalize word"
    tooltip = "Capitalize current word"
    key_bindings = {'emacs': 'M-C',}

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutateAction):
    """Upcase the current word and move the cursor to the start of the
    next word.
    """
    alias = "upcase-region-or-word"
    name = "Upcase word"
    tooltip = "Upcase current word"
    key_bindings = {'emacs': 'M-U',}

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateAction):
    """Downcase the current word and move the cursor to the start of the
    next word.
    """
    alias = "downcase-region-or-word"
    name = "Downcase word"
    tooltip = "Downcase current word"
    key_bindings = {'emacs': 'M-L',}

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()


class Reindent(TextModificationAction):
    alias = "reindent-region"
    name = "Reindent"
    tooltip = "Reindent a line or region"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'C-TAB',}

    def action(self, index=-1, multiplier=1):
        s = self.mode.stc

        # save cursor information so the cursor can be maintained at
        # the same relative location in the text after the indention
        pos = s.reindentLine()
        s.GotoPos(pos)


class TextTransformPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text transformation actions.
    """
    def getActions(self):
        return [CapitalizeWord, UpcaseWord, DowncaseWord,

                ShiftLeft, ShiftRight,

                Reindent, CommentRegion, UncommentRegion,

                Tabify, Untabify,
                ]
