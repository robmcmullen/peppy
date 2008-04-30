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
from peppy.lib.wordwrap import texwrap

from peppy.actions.base import *
from peppy.actions import *
from peppy.debug import *


class ShiftLeft(ScintillaCmdKeyExecute):
    """Unindent a line or region"""
    alias = "unindent-region"
    name = "Shift &Left"
    default_menu = ("Transform", -500)
    icon = 'icons/text_indent_remove_rob.png'
    key_bindings = {'default': 'C-[',}
    cmd = wx.stc.STC_CMD_BACKTAB

class ShiftRight(ScintillaCmdKeyExecute):
    """Indent a line or region"""
    alias = "indent-region"
    name = "Shift &Right"
    default_menu = ("Transform", 501)
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'C-]',}
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
        self.mode.commentRegion(multiplier != 4)

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
        self.mode.commentRegion(False)

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

class RemoveTrailingWhitespace(LineOrRegionMutateAction):
    """Remove all trailing whitespace from a line."""
    alias = "remove-trailing-whitespace"
    name = "Remove Trailing Whitespace"
    tooltip = "Remove all trailing whitespace from selected lines"
    default_menu = ("Transform", 710)

    def mutateLines(self, lines):
        regex = re.compile('(.*?)([\t ]+)([\r\n]+)?$')
        out = []
        for line in lines:
            match = regex.match(line)
            if match:
                # Remove everything but the line ending (if it exists)
                out.append(match.group(1) + line[match.end(2):])
            else:
                out.append(line)
        return out


class CapitalizeWord(WordOrRegionMutateAction):
    """Title-case the current word or words in the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "capitalize-region-or-word"
    name = "Capitalize"
    key_bindings = {'emacs': 'M-C',}
    default_menu = (("Transform/Case", 810), 100)

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutateAction):
    """Upcase the current word or the highlighted region.
    
    This will alse move the cursor to the start of the next word.
    """
    alias = "upcase-region-or-word"
    name = "Upcase"
    key_bindings = {'emacs': 'M-U',}
    default_menu = ("Transform/Case", 101)
    icon = "icons/text_uppercase.png"
    default_toolbar = False

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateAction):
    """Downcase the current word or the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "downcase-region-or-word"
    name = "Downcase"
    key_bindings = {'emacs': 'M-L',}
    default_menu = ("Transform/Case", 102)
    icon = "icons/text_lowercase.png"
    default_toolbar = False

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()

class SwapcaseWord(WordOrRegionMutateAction):
    """Swap the case of the current word or the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "swapcase-region-or-word"
    name = "Swap case"
    default_menu = ("Transform/Case", 103)
    default_toolbar = False

    def mutate(self, txt):
        """Change to the opposite case (upper to lower and vice-versa).
        """
        return txt.swapcase()

class Rot13(RegionMutateAction):
    """Convert the region using the rot13 encoding."""
    alias = "rot13-region"
    name = "Rot13"
    default_menu = ("Transform", -800)

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.encode('rot13')


class Backslashify(LineOrRegionMutateAction):
    """Escape the end of line character by adding backslashes.
    
    Add backslashes to the end of every line (except the last one) in the
    region so that the end-of-line character is escaped.  This is useful, for
    instance, within C or C++ C{#define} blocks that contain multiple line
    macros.
    """
    alias = "backslashify"
    name = "Backslashify"
    default_menu = ("Transform", 610)

    def isActionAvailable(self):
        """The action is only available if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Add backslashes to the end of all lines but the last
        """
        out = []
        eol = " \\" + self.mode.getLinesep()
        for line in lines[:-1]:
            out.append(line.rstrip() + eol)
        out.append(lines[-1])
        return out


class UnBackslashify(LineOrRegionMutateAction):
    """Remove backslashes from end of line.
    
    Remove backslashes from the end of every line in the region so that the
    end- of-line character is not escaped anymore.  This is the opposite of
    L{Backslashify}.
    """
    alias = "remove-backslashes"
    name = "Remove Backslashes"
    default_menu = ("Transform", 611)

    def isActionAvailable(self):
        """The action is only available if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Add backslashes to the end of all lines but the last
        """
        out = []
        regex = re.compile(r"(.*?)\s*\\(\s)*$")
        eol = self.mode.getLinesep()
        for line in lines:
            match = regex.match(line)
            if match:
                #dprint(repr(line))
                line = match.group(1)
                if match.group(2):
                    line += match.group(2)
            out.append(line)
        return out


class Reindent(TextModificationAction):
    """Reindent a line or region."""
    alias = "reindent-region"
    name = "Reindent"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'TAB',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        s = self.mode
        s.autoindent.processTab(s)


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
        self.dprint(info.getLines())
        lines = texwrap(info.getLines(), column)
        self.dprint(lines)
        newlines = [prefix + line for line in lines]
        return newlines


class SortLines(LineOrRegionMutateAction):
    """Sort lines using a simple string comparison sort
    """
    alias = "sort-lines"
    name = "Sort Lines"
    default_menu = (("Transform/Reorder", 820), 100)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        out = [line for line in lines]
        out.sort()
        return out


class ReverseLines(LineOrRegionMutateAction):
    """Reverse the selected lines
    """
    alias = "reverse-lines"
    name = "Reverse Lines"
    default_menu = ("Transform/Reorder", -200)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        out = [line for line in lines]
        out.reverse()
        return out


class ShuffleLines(LineOrRegionMutateAction):
    """Shuffle the selected lines randomly
    """
    alias = "shuffle-lines"
    name = "Shuffle Lines"
    default_menu = ("Transform/Reorder", 210)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        import random
        
        out = [line for line in lines]
        random.shuffle(out)
        return out


class TextTransformPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text transformation actions.
    """
    def getActions(self):
        return [CapitalizeWord, UpcaseWord, DowncaseWord, SwapcaseWord,

                ShiftLeft, ShiftRight,

                Reindent, CommentRegion, UncommentRegion,
                FillParagraphOrRegion, Backslashify, UnBackslashify,

                Tabify, Untabify, RemoveTrailingWhitespace,
                
                Rot13,
                
                SortLines, ReverseLines, ShuffleLines,
                ]
