# peppy Copyright (c) 2006-2010 Rob McMullen
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


class ScintillaCmdKeyExecuteOnLine(ScintillaCmdKeyExecute):
    """Subclass of ScintillaCmdKeyExecute to operate on at full line at minimum.
    
    If a selection already exists, nothing is done to alter the region;
    however, if the cursor is on a line and there is no selection, a selection
    is made out of the current line and the Scintilla command is called to
    operate on the selection.
    """
    
    def action(self, index=-1, multiplier=1):
        pos, end = self.mode.GetSelection()
        if pos == end:
            line = self.mode.GetCurrentLine()
            start = self.mode.PositionFromLine(line)
            end = self.mode.PositionFromLine(line+1)
            self.mode.SetSelection(start, end)
        ScintillaCmdKeyExecute.action(self, index, multiplier)


class ScintillaCommandsPlugin(IPeppyPlugin):
    """Plugin containing overridable actions for most of the default Scintilla
    keystrokes.
    
    Most Scintilla functions are bound to default keystrokes, but in order to
    provide a way within peppy to redefine those keystrokes, they have to be
    declared as actions.  Peppy uses the L{ScintillaCmdKeyExecute} action to
    map a keystroke to a Scintilla command.
    """
    # Note that the actions are defined within the plugin class so that it's
    # efficient to do introspection to find the list of scintilla commands.
    
    
    # Stuff from the scintilla source showing the default key bindings
    #    {SCK_TAB,           SCI_SHIFT,      SCI_BACKTAB},
    class ShiftLeft(ScintillaCmdKeyExecuteOnLine):
        """Unindent a line or region"""
        alias = "unindent-region"
        name = "Shift &Left"
        default_menu = ("Transform", -500)
        icon = 'icons/text_indent_remove_rob.png'
        key_bindings = {'default': 'M-[', 'emacs': ['M-[', 'C-c C-S-,'],}
        cmd = wx.stc.STC_CMD_BACKTAB

    #    {SCK_ESCAPE,        SCI_NORM,       SCI_CANCEL},
    #    {SCK_LEFT,          SCI_NORM,       SCI_CHARLEFT},
    class PreviousCharacter(ScintillaCmdKeyExecute):
        """Move the cursor to previous character"""
        key_bindings = {'default': 'LEFT', 'emacs': ['LEFT', 'C-b'],}
        cmd = wx.stc.STC_CMD_CHARLEFT
        
    #    {SCK_LEFT,          SCI_SHIFT,      SCI_CHARLEFTEXTEND},
    class PreviousCharacterExtend(ScintillaCmdKeyExecute):
        """Move the cursor to previous character and extend the selection"""
        key_bindings = {'default': 'S-LEFT',}
        cmd = wx.stc.STC_CMD_CHARLEFTEXTEND
        
    #    {SCK_LEFT,          SCI_ASHIFT,     SCI_CHARLEFTRECTEXTEND},
    class PreviousCharacterRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor to previous character and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-LEFT',}
        cmd = wx.stc.STC_CMD_CHARLEFTRECTEXTEND
        
    #    {SCK_RIGHT,         SCI_NORM,       SCI_CHARRIGHT},
    class NextCharacter(ScintillaCmdKeyExecute):
        """Move the cursor to next character"""
        key_bindings = {'default': 'RIGHT', 'emacs': ['RIGHT', 'C-f'],}
        cmd = wx.stc.STC_CMD_CHARRIGHT

    #    {SCK_RIGHT,         SCI_SHIFT,      SCI_CHARRIGHTEXTEND},
    class NextCharacterExtend(ScintillaCmdKeyExecute):
        """Move the cursor to next character and extend the selection"""
        key_bindings = {'default': 'S-RIGHT',}
        cmd = wx.stc.STC_CMD_CHARRIGHTEXTEND

    #    {SCK_RIGHT,         SCI_ASHIFT,     SCI_CHARRIGHTRECTEXTEND},
    class NextCharacterRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor to next character and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-RIGHT',}
        cmd = wx.stc.STC_CMD_CHARRIGHTRECTEXTEND

    #    {SCK_DELETE,        SCI_NORM,       SCI_CLEAR},
    class DeleteNextCharacter(ScintillaCmdKeyExecute):
        """Delete character to the right of the cursor"""
        cmd = wx.stc.STC_CMD_CLEAR

    #    {SCK_INSERT,        SCI_CTRL,       SCI_COPY},
    #    {SCK_DELETE,        SCI_SHIFT,      SCI_CUT},

    #    {SCK_BACK,          SCI_NORM,       SCI_DELETEBACK},
    #    {SCK_BACK,          SCI_SHIFT,      SCI_DELETEBACK},
    class DeletePreviousCharacter(ScintillaCmdKeyExecute):
        """Delete character to the left of the cursor"""
        key_bindings = {'default': 'S-BACK'}
        cmd = wx.stc.STC_CMD_DELETEBACK

    # STC_CMD_DELETEBACKNOTLINE
    #    {SCK_BACK,          SCI_CSHIFT,     SCI_DELLINELEFT},
    class DeleteLineBeforeCursor(ScintillaCmdKeyExecute):
        """Delete all characters on the line before the cursor"""
        key_bindings = {'default': 'C-S-BACK'}
        cmd = wx.stc.STC_CMD_DELLINELEFT

    #    {SCK_DELETE,        SCI_CSHIFT,     SCI_DELLINERIGHT},
    class DeleteLineAfterCursor(ScintillaCmdKeyExecute):
        """Delete all characters on the line after the cursor"""
        key_bindings = {'default': 'C-S-DELETE', 'emacs': 'C-k', 'mac': 'C-k'}
        cmd = wx.stc.STC_CMD_DELLINERIGHT

    #    {SCK_BACK,          SCI_CTRL,       SCI_DELWORDLEFT},
    class DeletePreviousWord(ScintillaCmdKeyExecute):
        """Delete the previous word"""
        key_bindings = {'default': 'C-BACK'}
        cmd = wx.stc.STC_CMD_DELWORDLEFT

    #    {SCK_DELETE,        SCI_CTRL,       SCI_DELWORDRIGHT},
    class DeleteNextWord(ScintillaCmdKeyExecute):
        """Delete the previous word"""
        key_bindings = {'default': 'C-DELETE'}
        cmd = wx.stc.STC_CMD_DELWORDRIGHT

    #    {SCK_END,           SCI_CTRL,       SCI_DOCUMENTEND},
    class EndOfBuffer(ScintillaCmdKeyExecute):
        """Move the cursor to the end of the buffer"""
        key_bindings = {'default': 'C-END'}
        cmd = wx.stc.STC_CMD_DOCUMENTEND

    #    {SCK_END,           SCI_CSHIFT,     SCI_DOCUMENTENDEXTEND},
    class EndOfBufferExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the end of the buffer and extend the selection"""
        key_bindings = {'default': 'C-S-END'}
        cmd = wx.stc.STC_CMD_DOCUMENTENDEXTEND

    #    {SCK_HOME,          SCI_CTRL,       SCI_DOCUMENTSTART},
    class BeginningOfBuffer(ScintillaCmdKeyExecute):
        """Move the cursor to the start of the buffer"""
        key_bindings = {'default': 'C-HOME'}
        cmd = wx.stc.STC_CMD_DOCUMENTSTART

    #    {SCK_HOME,          SCI_CSHIFT,     SCI_DOCUMENTSTARTEXTEND},
    class BeginningOfBufferExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the start of the buffer and extend the
        selection
        """
        key_bindings = {'default': 'C-S-HOME'}
        cmd = wx.stc.STC_CMD_DOCUMENTSTARTEXTEND

    #    {SCK_INSERT,        SCI_NORM,       SCI_EDITTOGGLEOVERTYPE},
    class ToggleOvertype(ScintillaCmdKeyExecute):
        """Toggle between insert and overtype modes"""
        key_bindings = {'default': 'INSERT',}
        cmd = wx.stc.STC_CMD_EDITTOGGLEOVERTYPE
            
    #    //'L',              SCI_CTRL,       SCI_FORMFEED,
    # STC_CMD_HOME
    #    {SCK_HOME,          SCI_ALT,        SCI_HOMEDISPLAY},
    class BeginningOfLine(ScintillaCmdKeyExecute):
        """Move the cursor to the start of the current line"""
        key_bindings = {'default': 'M-HOME', 'emacs': ['M-HOME', 'M-C-A'],}
        cmd = wx.stc.STC_CMD_HOMEDISPLAY

    #//    {SCK_HOME,        SCI_ASHIFT,     SCI_HOMEDISPLAYEXTEND},
    # STC_CMD_HOMERECTEXTEND
    # STC_CMD_HOMEWRAP
    # STC_CMD_HOMEWRAPEXTEND
    #    {'T',               SCI_CSHIFT,     SCI_LINECOPY},
    class CopyLine(ScintillaCmdKeyExecute):
        """Copy the current line"""
        key_bindings = {'default': 'C-S-t', 'emacs': None,}
        cmd = wx.stc.STC_CMD_LINECOPY

    #    {'L',               SCI_CTRL,       SCI_LINECUT},
    class CutLine(ScintillaCmdKeyExecute):
        """Cut the current line"""
        key_bindings = {'default': 'C-l',}
        cmd = wx.stc.STC_CMD_LINECUT

    #    {'L',               SCI_CSHIFT,     SCI_LINEDELETE},
    class DeleteLine(ScintillaCmdKeyExecute):
        """Delete the current line"""
        key_bindings = {'default': 'C-S-l',}
        cmd = wx.stc.STC_CMD_LINEDELETE

    #    {SCK_DOWN,          SCI_NORM,       SCI_LINEDOWN},
    class NextLine(ScintillaCmdKeyExecute):
        """Move the cursor down a line"""
        key_bindings = {'default': 'DOWN', 'emacs': ['DOWN', 'C-n'],}
        cmd = wx.stc.STC_CMD_LINEDOWN

    #    {SCK_DOWN,          SCI_SHIFT,      SCI_LINEDOWNEXTEND},
    class NextLineExtend(ScintillaCmdKeyExecute):
        """Move the cursor down a line and extend the selection"""
        key_bindings = {'default': 'S-DOWN',}
        cmd = wx.stc.STC_CMD_LINEDOWNEXTEND

    #    {SCK_DOWN,          SCI_ASHIFT,     SCI_LINEDOWNRECTEXTEND},
    class NextLineRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor down a line and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-DOWN',}
        cmd = wx.stc.STC_CMD_LINEDOWNRECTEXTEND

    #    {SCK_END,           SCI_NORM,       SCI_LINEEND},
    class EndOfLine(ScintillaCmdKeyExecute):
        """Move the cursor to the end of the current line"""
        key_bindings = {'default': 'END', 'emacs': ['END', 'C-e'],}
        cmd = wx.stc.STC_CMD_LINEEND

    #    {SCK_END,           SCI_ALT,        SCI_LINEENDDISPLAY},
    #//    {SCK_END,         SCI_ASHIFT,     SCI_LINEENDDISPLAYEXTEND},
    #    {SCK_END,           SCI_SHIFT,      SCI_LINEENDEXTEND},
    class EndOfLineExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the end of the current line and extend the
        selection
        """
        key_bindings = {'default': 'S-END',}
        cmd = wx.stc.STC_CMD_LINEENDEXTEND

    #    {SCK_END,           SCI_ASHIFT,     SCI_LINEENDRECTEXTEND},
    class EndOfLineRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the end of the current line and extend the
        rectangular selection
        """
        key_bindings = {'default': 'M-S-END',}
        cmd = wx.stc.STC_CMD_LINEENDRECTEXTEND

    # STC_CMD_LINEENDWRAP
    # STC_CMD_LINEENDWRAPEXTEND
    #    {SCK_DOWN,          SCI_CTRL,       SCI_LINESCROLLDOWN},
    class ScrollDown(ScintillaCmdKeyExecute):
        """Scroll the editing window down"""
        key_bindings = {'default': 'C-DOWN',}
        cmd = wx.stc.STC_CMD_LINESCROLLDOWN

    #    {SCK_UP,            SCI_CTRL,       SCI_LINESCROLLUP},
    class ScrollUp(ScintillaCmdKeyExecute):
        """Scroll the editing window up"""
        key_bindings = {'default': 'C-UP',}
        cmd = wx.stc.STC_CMD_LINESCROLLUP

    #    {'T',               SCI_CTRL,       SCI_LINETRANSPOSE},
    class TransposeLine(ScintillaCmdKeyExecute):
        """Swap the current line for the previous line"""
        key_bindings = {'default': 'C-t', 'emacs': None,}
        cmd = wx.stc.STC_CMD_LINETRANSPOSE

    #    {SCK_UP,            SCI_NORM,       SCI_LINEUP},
    class PreviousLine(ScintillaCmdKeyExecute):
        """Move the cursor up a line"""
        key_bindings = {'default': 'UP', 'emacs': ['UP', 'C-p'],}
        cmd = wx.stc.STC_CMD_LINEUP

    #    {SCK_UP,            SCI_SHIFT,      SCI_LINEUPEXTEND},
    class PreviousLineExtend(ScintillaCmdKeyExecute):
        """Move the cursor up a line and extend the selection"""
        key_bindings = {'default': 'S-UP',}
        cmd = wx.stc.STC_CMD_LINEUPEXTEND

    #    {SCK_UP,            SCI_ASHIFT,     SCI_LINEUPRECTEXTEND},
    class PreviousLineRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor up a line and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-UP',}
        cmd = wx.stc.STC_CMD_LINEUPRECTEXTEND

    #    {'U',               SCI_CTRL,       SCI_LOWERCASE},
    #    {SCK_RETURN,        SCI_NORM,       SCI_NEWLINE},
    #    {SCK_RETURN,        SCI_SHIFT,      SCI_NEWLINE},
    #    {SCK_NEXT,          SCI_NORM,       SCI_PAGEDOWN},
    class PageDown(ScintillaCmdKeyExecute):
        """Scroll down a page"""
        key_bindings = {'default': ['PAGEDOWN', 'NEXT'],}
        cmd = wx.stc.STC_CMD_PAGEDOWN

    #    {SCK_NEXT,          SCI_SHIFT,      SCI_PAGEDOWNEXTEND},
    class PageDownExtend(ScintillaCmdKeyExecute):
        """Scroll down a page and extend the selection"""
        key_bindings = {'default': 'S-PAGEDOWN',}
        cmd = wx.stc.STC_CMD_PAGEDOWNEXTEND

    #    {SCK_NEXT,          SCI_ASHIFT,     SCI_PAGEDOWNRECTEXTEND},
    class PageDownRectExtend(ScintillaCmdKeyExecute):
        """Scroll down a page and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-PAGEDOWN',}
        cmd = wx.stc.STC_CMD_PAGEDOWNRECTEXTEND

    #    {SCK_PRIOR,         SCI_NORM,       SCI_PAGEUP},
    class PageUp(ScintillaCmdKeyExecute):
        """Scroll up a page"""
        key_bindings = {'default': ['PAGEUP', 'PRIOR'],}
        cmd = wx.stc.STC_CMD_PAGEUP

    #    {SCK_PRIOR,         SCI_SHIFT,      SCI_PAGEUPEXTEND},
    class PageUpExtend(ScintillaCmdKeyExecute):
        """Scroll up a page and extend the selection"""
        key_bindings = {'default': 'S-PAGEUP',}
        cmd = wx.stc.STC_CMD_PAGEUPEXTEND

    #    {SCK_PRIOR,         SCI_ASHIFT,     SCI_PAGEUPRECTEXTEND},
    class PageUpRectExtend(ScintillaCmdKeyExecute):
        """Scroll up a page and extend the rectangular selection"""
        key_bindings = {'default': 'M-S-PAGEUP',}
        cmd = wx.stc.STC_CMD_PAGEUPRECTEXTEND

    #    {']',               SCI_CTRL,       SCI_PARADOWN},
    class ParaDown(ScintillaCmdKeyExecute):
        """Scroll down a paragraph"""
        key_bindings = {'default': 'C-]',}
        cmd = wx.stc.STC_CMD_PARADOWN

    #    {']',               SCI_CSHIFT,     SCI_PARADOWNEXTEND},
    class ParaDownExtend(ScintillaCmdKeyExecute):
        """Scroll down a paragraph and extend the selection"""
        key_bindings = {'default': 'C-S-]',}
        cmd = wx.stc.STC_CMD_PARADOWNEXTEND

    #    {'[',               SCI_CTRL,       SCI_PARAUP},
    class ParaUp(ScintillaCmdKeyExecute):
        """Scroll up a paragraph"""
        key_bindings = {'default': 'C-[',}
        cmd = wx.stc.STC_CMD_PARAUP

    #    {'[',               SCI_CSHIFT,     SCI_PARAUPEXTEND},
    class ParaUpExtend(ScintillaCmdKeyExecute):
        """Scroll up a paragraph and extend the selection"""
        key_bindings = {'default': 'C-S-[',}
        cmd = wx.stc.STC_CMD_PARAUPEXTEND

    #    {SCK_INSERT,        SCI_SHIFT,      SCI_PASTE},
    # STC_CMD_REDO
    # STC_CMD_SELECTALL
    # STC_CMD_STUTTEREDPAGEDOWN
    # STC_CMD_STUTTEREDPAGEDOWNEXTEND
    # STC_CMD_STUTTEREDPAGEUP
    # STC_CMD_STUTTEREDPAGEUPEXTEND
    #    {'D',               SCI_CTRL,       SCI_SELECTIONDUPLICATE},
    class DuplicateSelection(ScintillaCmdKeyExecute):
        """Duplicate the selection"""
        key_bindings = {'default': 'C-d',}
        # wx.stc.STC_CMD_SELECTIONDUPLICATE isn't mapped from the scintilla
        # source SCI_SELECTIONDUPLICATE as of wxPython 2.8.8.1, but the
        # integer equivalent works
        cmd = 2469

    #    {SCK_DIVIDE,        SCI_CTRL,       SCI_SETZOOM},
    #    {SCK_TAB,           SCI_NORM,       SCI_TAB},
    class ShiftRight(ScintillaCmdKeyExecuteOnLine):
        """Indent a line or region"""
        alias = "indent-region"
        name = "Shift &Right"
        default_menu = ("Transform", 501)
        icon = 'icons/text_indent_rob.png'
        key_bindings = {'default': 'M-]', 'emacs': ['M-]', 'C-c C-S-.'],}
        cmd = wx.stc.STC_CMD_TAB

    #    {SCK_BACK,          SCI_ALT,        SCI_UNDO},
    #    {'U',               SCI_CSHIFT,     SCI_UPPERCASE},
    #    {SCK_HOME,          SCI_NORM,       SCI_VCHOME},
    class BeginningTextOfLine(ScintillaCmdKeyExecute):
        """Move the cursor to first non-blank character in the line"""
        key_bindings = {'default': 'HOME', 'emacs': ['HOME', 'C-a'],}
        cmd = wx.stc.STC_CMD_VCHOME
            
    #    {SCK_HOME,          SCI_SHIFT,      SCI_VCHOMEEXTEND},
    class BeginningTextOfLineExtend(ScintillaCmdKeyExecute):
        """Move the cursor to first non-blank character in the line and extend
        the selection
        """
        key_bindings = {'default': 'S-HOME',}
        cmd = wx.stc.STC_CMD_VCHOMEEXTEND
            
    #    {SCK_HOME,          SCI_ASHIFT,     SCI_VCHOMERECTEXTEND},
    class BeginningTextOfLineRectExtend(ScintillaCmdKeyExecute):
        """Move the cursor to first non-blank character in the line and extend
        the rectangular selection
        """
        key_bindings = {'default': 'M-S-HOME',}
        cmd = wx.stc.STC_CMD_VCHOMERECTEXTEND
            
    # STC_CMD_VCHOMEWRAP
    # STC_CMD_VCHOMEWRAPEXTEND
    #    {SCK_LEFT,          SCI_CTRL,       SCI_WORDLEFT},
    class PreviousWord(ScintillaCmdKeyExecute):
        """Move the cursor to the previous word break"""
        key_bindings = {'default': 'C-LEFT', 'emacs': ['C-LEFT', 'M-b'],}
        cmd = wx.stc.STC_CMD_WORDLEFT

    # STC_CMD_WORDLEFTENDEXTEND
    #    {SCK_LEFT,          SCI_CSHIFT,     SCI_WORDLEFTEXTEND},
    class PreviousWordExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the previous word break and extend the selection"""
        key_bindings = {'default': 'C-S-LEFT',}
        cmd = wx.stc.STC_CMD_WORDLEFTEXTEND

    #    {'/',               SCI_CTRL,       SCI_WORDPARTLEFT},
    class PreviousWordPart(ScintillaCmdKeyExecute):
        """Move the cursor to the previous word part"""
        key_bindings = {'default': 'C-\\',}
        cmd = wx.stc.STC_CMD_WORDPARTLEFT

    #    {'/',               SCI_CSHIFT,     SCI_WORDPARTLEFTEXTEND},
    class PreviousWordPartExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the previous word part and extend the selection"""
        key_bindings = {'default': 'C-S-\\',}
        cmd = wx.stc.STC_CMD_WORDPARTLEFTEXTEND

    #    {'\\',              SCI_CTRL,       SCI_WORDPARTRIGHT},
    class NextWordPart(ScintillaCmdKeyExecute):
        """Move the cursor to the next word part"""
        # conflicts with the default emacs keybinding for undo, so emacs mode
        # doesn't have a keybinding
        key_bindings = {'default': 'C-/', 'emacs': None}
        cmd = wx.stc.STC_CMD_WORDPARTRIGHT

    #    {'\\',              SCI_CSHIFT,     SCI_WORDPARTRIGHTEXTEND},
    class NextWordPartExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the next word part and extend the selection"""
        # conflicts with the default emacs keybinding for redo, so emacs mode
        # doesn't have a keybinding
        key_bindings = {'default': 'C-S-/', 'emacs': None}
        cmd = wx.stc.STC_CMD_WORDPARTRIGHTEXTEND

    #    {SCK_RIGHT,         SCI_CTRL,       SCI_WORDRIGHT},
    class NextWord(ScintillaCmdKeyExecute):
        """Move the cursor to the next word break"""
        key_bindings = {'default': 'C-RIGHT', 'emacs': ['C-RIGHT', 'M-f'],}
        cmd = wx.stc.STC_CMD_WORDRIGHT

    # STC_CMD_WORDRIGHTENDEXTEND
    #    {SCK_RIGHT,         SCI_CSHIFT,     SCI_WORDRIGHTEXTEND},
    class NextWordExtend(ScintillaCmdKeyExecute):
        """Move the cursor to the next word break and extend the selection"""
        key_bindings = {'default': 'C-S-RIGHT',}
        cmd = wx.stc.STC_CMD_WORDRIGHTEXTEND

    # Font zooming is handled in fundamental_menu.py
    #    {SCK_ADD,           SCI_CTRL,       SCI_ZOOMIN},
    #    {SCK_SUBTRACT,      SCI_CTRL,       SCI_ZOOMOUT},


    # Cache that holds the list of actions
    scintilla_actions = []

    def getActions(self):
        # Compute the list of actions.
        if not self.scintilla_actions:
            actions = []
            for attr in dir(self):
                obj = getattr(self, attr)
                if isinstance(obj, type) and issubclass(obj, ScintillaCmdKeyExecute):
                    actions.append(obj)
            self.__class__.scintilla_actions = actions
        return self.scintilla_actions
