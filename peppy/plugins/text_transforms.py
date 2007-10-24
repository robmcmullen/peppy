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
from peppy.lib.wordwrap import texwrap

from peppy.actions.base import *
from peppy.menu import *
from peppy.debug import *


class ShiftLeft(ScintillaCmdKeyExecute):
    """Unindent a line or region"""
    alias = "unindent-region"
    name = "Shift &Left"
    default_menu = ("Transform", -500)
    icon = 'icons/text_indent_remove_rob.png'
    cmd = wx.stc.STC_CMD_BACKTAB

class ShiftRight(ScintillaCmdKeyExecute):
    """Indent a line or region"""
    alias = "indent-region"
    name = "Shift &Right"
    default_menu = ("Transform", 501)
    icon = 'icons/text_indent_rob.png'
    cmd = wx.stc.STC_CMD_TAB


class CommentRegion(TextModificationAction):
    """Comment a line or region.
    
    This will use the current mode's comment characters to comment out
    entire blocks of lines.  The comment will start in column zero, and
    if there is an end comment delimiter, it will appear as the last
    character(s) before the end of line indicatior.
    """
    alias = "comment-region"
    name = "&Comment Region"
    default_menu = ("Transform", -600)
    key_bindings = {'emacs': 'C-C C-C',}

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(multiplier != 4)

class UncommentRegion(TextModificationAction):
    """Uncomment a line or region.
    
    This will use the current mode's comment characters to identify the
    lines in the region that have been commented out, and will remove
    the comment character(s) from the line.
    """
    alias = "uncomment-region"
    name = "&Uncomment Region"
    default_menu = ("Transform", 601)

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(False)

class Tabify(LineOrRegionMutateAction):
    """Replace spaces with tabs at the start of lines."""
    alias = "tabify"
    name = "&Tabify"
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
    """Replace tabs with spaces at the start of lines."""
    alias = "untabify"
    name = "&Untabify"
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
    """Title-case the current word.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "capitalize-region-or-word"
    name = "Capitalize word"
    key_bindings = {'emacs': 'M-C',}

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutateAction):
    """Upcase the current word.
    
    This will alse move the cursor to the start of the next word.
    """
    alias = "upcase-region-or-word"
    name = "Upcase word"
    key_bindings = {'emacs': 'M-U',}

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateAction):
    """Downcase the current word.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "downcase-region-or-word"
    name = "Downcase word"
    key_bindings = {'emacs': 'M-L',}

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()

class Rot13(RegionMutateAction):
    """Convert the region using the rot13 encoding."""
    alias = "rot13-region"
    name = "Rot13"
    default_menu = ("Transform", -800)

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.encode('rot13')


class Reindent(TextModificationAction):
    """Reindent a line or region."""
    alias = "reindent-region"
    name = "Reindent"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'C-TAB',}

    def action(self, index=-1, multiplier=1):
        s = self.mode.stc

        # save cursor information so the cursor can be maintained at
        # the same relative location in the text after the indention
        pos = s.reindentLine()
        s.GotoPos(pos)


class FillParagraphOrRegion(ParagraphOrRegionMutateAction):
    """Word-wrap the current paragraph or region."""
    alias = "fill-paragraph-or-region"
    name = "Fill Paragraph"
    default_menu = ("Transform", 603)
    key_bindings = {'default': 'M-Q',}

    def mutateParagraph(self, info):
        """Word wrap the current paragraph using the TeX algorithm."""
        prefix = info.leader_pattern
        if len(prefix.rstrip()) == len(prefix) and len(prefix) > 0:
            # no space at the end of the prefix!  Add one
            prefix += " "
        column = self.mode.classprefs.edge_column - len(prefix) - 1
        dprint(info.getLines())
        lines = texwrap(info.getLines(), column)
        dprint(lines)
        newlines = [prefix + line for line in lines]
        return newlines


class TextTransformPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text transformation actions.
    """
    def getActions(self):
        return [CapitalizeWord, UpcaseWord, DowncaseWord,

                ShiftLeft, ShiftRight,

                Reindent, CommentRegion, UncommentRegion,
                FillParagraphOrRegion,

                Tabify, Untabify,
                
                Rot13,
                ]
