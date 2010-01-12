# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import wx
import wx.stc

from peppy.yapsy.plugins import *

from peppy.actions import *
from peppy.actions.base import *


class ElectricChar(SelectAction):
    """Special trigger function for 'electric' characters that change the
    text in addition to inserting themselves.
    
    Used in the autoindent code.
    
    @skip_translation
    """
    name = "ElectricChar"
    needs_keyboard_focus = True
    
    def addKeyBindingToAcceleratorList(self, accel_list):
        for char in self.mode.autoindent.getElectricChars():
            self.dprint("Registering %s as electric character" % char)
            accel_list.registerElectricChar(char, self, self.mode)
            
    def actionKeystroke(self, evt, multiplier=1, **kwargs):
        mode = self.mode
        uchar = unichr(evt.GetUnicodeKey())
        
        # FIXME: Because the autoindenter depends on the styling information,
        # need to make sure the document is up to date.  But, is this call to
        # style the entire document fast enough in practice, or will it have
        # to be optimized?
        mode.Colourise(0, mode.GetTextLength())
        
        for i in range(multiplier):
            if mode.autoindent.electricChar(mode, uchar):
                # If the autoindenter handles the char, it will insert the char.
                pass
            else:
                # If the autoindenter doesn't handle the character for some
                # reason, we are then left to insert it.
                mode.AddText(uchar)


class ElectricReturn(TextModificationAction):
    """Indent the next line following a return
    
    Using the autoindenter for the current major mode, indent the next line
    after the return to the appropriate level.  For example, in Python mode
    the next line would be indented if you press return after an if statement,
    and the next line indent would be reduced by one intentation level if you
    press return after a C{raise} or C{return} statement.
    
    By default, this is bound to both RET and S-RET because I found it was very
    easy to hit S-RET by mistake when the last character in the line was a
    shifted character like ')' or ':'.  Without this S-RET binding, Scintilla
    would insert a raw CR in the text instead of autoindenting.
    """
    name = "Electric Return"
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': ['RET', 'S-RET'],}
    needs_keyboard_focus = True

    def action(self, index=-1, multiplier=1):
        if self.mode.spell and self.mode.classprefs.spell_check:
            pos = self.mode.GetCurrentPos()
            self.mode.spell.checkWord(pos)
        self.mode.autoindent.processReturn(self.mode)

class ScintillaReturn(ScintillaCmdKeyExecute):
    """Insert a end of line character and move to the beginning of the next
    line.
    
    """
    key_bindings = {'default': 'RET'}
    cmd = wx.stc.STC_CMD_NEWLINE


class ElectricDelete(TextModificationAction):
    """Delete all whitespace from cursor forward to the next non-blank character
    """
    name = "Electric Delete"
    key_bindings = {'default': 'DELETE',}
    needs_keyboard_focus = True

    def action(self, index=-1, multiplier=1):
        self.mode.autoindent.electricDelete(self.mode)

class ScintillaDelete(ScintillaCmdKeyExecute):
    """Delete character to the right of the cursor"""
    key_bindings = {'default': 'DELETE',}
    cmd = wx.stc.STC_CMD_CLEAR


class ElectricBackspace(TextModificationAction):
    """Delete all whitespace from cursor back to the last non-blank character
    """
    name = "Electric Backspace"
    key_bindings = {'default': 'BACK',}
    needs_keyboard_focus = True

    def action(self, index=-1, multiplier=1):
        self.mode.autoindent.electricBackspace(self.mode)

class ScintillaBackspace(ScintillaCmdKeyExecute):
    """Delete character to the left of the cursor"""
    key_bindings = {'default': 'BACK'}
    cmd = wx.stc.STC_CMD_DELETEBACK


class Reindent(TextModificationAction):
    """Reindent a line or region.
    
    Recalculates the indentation for the selected region, using the current
    major mode's algorithm for indentation.
    """
    name = "Reindent"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'TAB',}

    def action(self, index=-1, multiplier=1):
        s = self.mode
        
        # FIXME: Because the autoindenter depends on the styling information,
        # need to make sure the document is up to date.  But, is this call to
        # style the entire document fast enough in practice, or will it have
        # to be optimized?
        s.Colourise(0, s.GetTextLength())

        start, end = s.GetSelection2()
        if start == end:
            dprint("no selection; cursor at %s" % start)
            s.autoindent.processTab(s)
        else:
            dprint("selection: %s - %s" % (start, end))
            line = s.LineFromPosition(start)
            end = s.LineFromPosition(end)
            s.autoindent.debuglevel = True
            s.BeginUndoAction()
            while line <= end:
                pos = s.autoindent.reindentLine(s, linenum=line)
                line += 1
            s.SetSelection(start, pos)
            s.GetLineRegion()
            s.EndUndoAction()


class ElectricActionsPlugin(IPeppyPlugin):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    def getCompatibleActions(self, modecls):
        # autoindent is a class attribute and therefore can be looked-up here
        if hasattr(modecls, 'autoindent'):
            return [ElectricChar, ElectricReturn, ElectricDelete,
                    ElectricBackspace, Reindent,
                    ]
        elif issubclass(modecls, wx.stc.StyledTextCtrl):
            # For modes that still use Scintilla but aren't subclassed from
            # FundamentalMode, need to provide a way to process the return,
            # delete, and backspace keys
            return [ScintillaReturn, ScintillaDelete,
                    ScintillaBackspace,
                    ]
        return []
