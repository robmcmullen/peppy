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
    alias = _("unindent-region")
    name = _("Shift &Left")
    tooltip = _("Unindent a line region")
    icon = 'icons/text_indent_remove_rob.png'
    cmd = wx.stc.STC_CMD_BACKTAB

class ShiftRight(ScintillaCmdKeyExecute):
    alias = _("indent-region")
    name = _("Shift &Right")
    tooltip = _("Indent a line or region")
    icon = 'icons/text_indent_rob.png'
    cmd = wx.stc.STC_CMD_TAB


class CommentRegion(BufferModificationAction):
    alias = _("comment-region")
    name = _("&Comment Region")
    tooltip = _("Comment a line or region")
    key_bindings = {'emacs': 'C-C C-C',}

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(multiplier != 4)

class UncommentRegion(BufferModificationAction):
    alias = _("uncomment-region")
    name = _("&Uncomment Region")
    tooltip = _("Uncomment a line or region")

    def action(self, index=-1, multiplier=1):
        self.mode.stc.commentRegion(False)

class Tabify(LineOrRegionMutateAction):
    alias = _("tabify")
    name = _("&Tabify")
    tooltip = _("Replace spaces with tabs at the start of lines")

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
    alias = _("untabify")
    name = _("&Untabify")
    tooltip = _("Replace tabs with spaces at the start of lines")
    icon = 'icons/text_indent_rob.png'

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
    alias = _("capitalize-region-or-word")
    name = _("Capitalize word")
    tooltip = _("Capitalize current word")
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
    alias = _("upcase-region-or-word")
    name = _("Upcase word")
    tooltip = _("Upcase current word")
    key_bindings = {'emacs': 'M-U',}

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateAction):
    """Downcase the current word and move the cursor to the start of the
    next word.
    """
    alias = _("downcase-region-or-word")
    name = _("Downcase word")
    tooltip = _("Downcase current word")
    key_bindings = {'emacs': 'M-L',}

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()


class Reindent(BufferModificationAction):
    alias = _("reindent-region")
    name = _("Reindent")
    tooltip = _("Reindent a line or region")
    icon = 'icons/text_indent_rob.png'
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

    default_menu=(("Fundamental",_("&Transform"),MenuItem(ShiftLeft)),
                  ("Fundamental",_("&Transform"),MenuItem(ShiftRight)),
                  ("Fundamental",_("&Transform"),Separator(_("shift")).last()),
                  ("Fundamental",_("&Transform"),MenuItem(Reindent)),
                  ("Fundamental",_("&Transform"),MenuItem(CommentRegion)),
                  ("Fundamental",_("&Transform"),MenuItem(UncommentRegion)),
                  ("Fundamental",_("&Transform"),Separator(_("shift")).last()),
                  ("Fundamental",_("&Transform"),MenuItem(Tabify)),
                  ("Fundamental",_("&Transform"),MenuItem(Untabify)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)
    
    default_tools=(("Fundamental",None,Menu(_("&Transform")).after(_("Major Mode"))),
                   ("Fundamental",_("&Transform"),MenuItem(ShiftLeft)),
                   ("Fundamental",_("&Transform"),MenuItem(ShiftRight)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

    default_keys=(("Fundamental",CapitalizeWord),
                  ("Fundamental",UpcaseWord),
                  ("Fundamental",DowncaseWord),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)
