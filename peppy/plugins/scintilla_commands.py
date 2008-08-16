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

# Stuff from the scintilla source showing the default key bindings
#    {SCK_TAB,           SCI_SHIFT,      SCI_BACKTAB},
#    {SCK_ESCAPE,        SCI_NORM,       SCI_CANCEL},
#    {SCK_LEFT,          SCI_NORM,       SCI_CHARLEFT},
#    {SCK_LEFT,          SCI_SHIFT,      SCI_CHARLEFTEXTEND},
#    {SCK_LEFT,          SCI_ASHIFT,     SCI_CHARLEFTRECTEXTEND},
class PreviousCharacter(ScintillaCmdKeyExecute):
    alias = "previous-character"
    name = "Cursor to previous character"
    tooltip = "Move the cursor left"
    key_bindings = {'emacs': 'C-B',}
    cmd = wx.stc.STC_CMD_CHARLEFT
    
#    {SCK_RIGHT,         SCI_NORM,       SCI_CHARRIGHT},
#    {SCK_RIGHT,         SCI_SHIFT,      SCI_CHARRIGHTEXTEND},
#    {SCK_RIGHT,         SCI_ASHIFT,     SCI_CHARRIGHTRECTEXTEND},
class NextCharacter(ScintillaCmdKeyExecute):
    alias = "next-character"
    name = "Cursor to next character"
    tooltip = "Move the cursor right"
    key_bindings = {'emacs': 'C-F',}
    cmd = wx.stc.STC_CMD_CHARRIGHT

#    {SCK_DELETE,        SCI_NORM,       SCI_CLEAR},
#    {SCK_INSERT,        SCI_CTRL,       SCI_COPY},
#    {SCK_DELETE,        SCI_SHIFT,      SCI_CUT},
#    {SCK_BACK,          SCI_NORM,       SCI_DELETEBACK},
#    {SCK_BACK,          SCI_SHIFT,      SCI_DELETEBACK},
# STC_CMD_DELETEBACKNOTLINE
#    {SCK_BACK,          SCI_CSHIFT,     SCI_DELLINELEFT},
#    {SCK_DELETE,        SCI_CSHIFT,     SCI_DELLINERIGHT},
#    {SCK_BACK,          SCI_CTRL,       SCI_DELWORDLEFT},
#    {SCK_DELETE,        SCI_CTRL,       SCI_DELWORDRIGHT},
#    {SCK_END,           SCI_CTRL,       SCI_DOCUMENTEND},
#    {SCK_END,           SCI_CSHIFT,     SCI_DOCUMENTENDEXTEND},
#    {SCK_HOME,          SCI_CTRL,       SCI_DOCUMENTSTART},
#    {SCK_HOME,          SCI_CSHIFT,     SCI_DOCUMENTSTARTEXTEND},
#    {SCK_INSERT,        SCI_NORM,       SCI_EDITTOGGLEOVERTYPE},
#    //'L',              SCI_CTRL,       SCI_FORMFEED,
# STC_CMD_HOME
#    {SCK_HOME,          SCI_ALT,        SCI_HOMEDISPLAY},
#//    {SCK_HOME,        SCI_ASHIFT,     SCI_HOMEDISPLAYEXTEND},
class BeginningOfLine(ScintillaCmdKeyExecute):
    alias = "beginning-of-line"
    name = "Cursor to Start of Line"
    tooltip = "Move the cursor to the start of the current line"
    key_bindings = {'emacs': 'M-C-A',}
    cmd = wx.stc.STC_CMD_HOMEDISPLAY
        
# STC_CMD_HOMERECTEXTEND
# STC_CMD_HOMEWRAP
# STC_CMD_HOMEWRAPEXTEND
#    {'T',               SCI_CSHIFT,     SCI_LINECOPY},
#    {'L',               SCI_CTRL,       SCI_LINECUT},
#    {'L',               SCI_CSHIFT,     SCI_LINEDELETE},
#    {SCK_DOWN,          SCI_NORM,       SCI_LINEDOWN},
class NextLine(ScintillaCmdKeyExecute):
    alias = "next-line"
    name = "Cursor to next line"
    tooltip = "Move the cursor down a line"
    key_bindings = {'emacs': 'C-N',}
    cmd = wx.stc.STC_CMD_LINEDOWN

#    {SCK_DOWN,          SCI_SHIFT,      SCI_LINEDOWNEXTEND},
#    {SCK_DOWN,          SCI_ASHIFT,     SCI_LINEDOWNRECTEXTEND},
#    {SCK_END,           SCI_NORM,       SCI_LINEEND},
class EndOfLine(ScintillaCmdKeyExecute):
    alias = "end-of-line"
    name = "Cursor to End of Line"
    tooltip = "Move the cursor to the end of the current line"
    key_bindings = {'default': 'END', 'emacs': 'C-E',}
    cmd = wx.stc.STC_CMD_LINEEND

#    {SCK_END,           SCI_ALT,        SCI_LINEENDDISPLAY},
#//    {SCK_END,         SCI_ASHIFT,     SCI_LINEENDDISPLAYEXTEND},
#    {SCK_END,           SCI_SHIFT,      SCI_LINEENDEXTEND},
#    {SCK_END,           SCI_ASHIFT,     SCI_LINEENDRECTEXTEND},
# STC_CMD_LINEENDWRAP
# STC_CMD_LINEENDWRAPEXTEND
#    {SCK_DOWN,          SCI_CTRL,       SCI_LINESCROLLDOWN},
#    {SCK_UP,            SCI_CTRL,       SCI_LINESCROLLUP},
#    {'T',               SCI_CTRL,       SCI_LINETRANSPOSE},
#    {SCK_UP,            SCI_NORM,       SCI_LINEUP},
class PreviousLine(ScintillaCmdKeyExecute):
    alias = "previous-line"
    name = "Cursor to previous line"
    tooltip = "Move the cursor up a line"
    key_bindings = {'emacs': 'C-P',}
    cmd = wx.stc.STC_CMD_LINEUP

#    {SCK_UP,            SCI_SHIFT,      SCI_LINEUPEXTEND},
#    {SCK_UP,            SCI_ASHIFT,     SCI_LINEUPRECTEXTEND},
#    {'U',               SCI_CTRL,       SCI_LOWERCASE},
#    {SCK_RETURN,        SCI_NORM,       SCI_NEWLINE},
#    {SCK_RETURN,        SCI_SHIFT,      SCI_NEWLINE},
#    {SCK_NEXT,          SCI_NORM,       SCI_PAGEDOWN},
#    {SCK_NEXT,          SCI_SHIFT,      SCI_PAGEDOWNEXTEND},
#    {SCK_NEXT,          SCI_ASHIFT,     SCI_PAGEDOWNRECTEXTEND},
#    {SCK_PRIOR,         SCI_NORM,       SCI_PAGEUP},
#    {SCK_PRIOR,         SCI_SHIFT,      SCI_PAGEUPEXTEND},
#    {SCK_PRIOR,         SCI_ASHIFT,     SCI_PAGEUPRECTEXTEND},
#    {']',               SCI_CTRL,       SCI_PARADOWN},
#    {']',               SCI_CSHIFT,     SCI_PARADOWNEXTEND},
#    {'[',               SCI_CTRL,       SCI_PARAUP},
#    {'[',               SCI_CSHIFT,     SCI_PARAUPEXTEND},
#    {SCK_INSERT,        SCI_SHIFT,      SCI_PASTE},
# STC_CMD_REDO
# STC_CMD_SELECTALL
# STC_CMD_STUTTEREDPAGEDOWN
# STC_CMD_STUTTEREDPAGEDOWNEXTEND
# STC_CMD_STUTTEREDPAGEUP
# STC_CMD_STUTTEREDPAGEUPEXTEND
#    {'D',               SCI_CTRL,       SCI_SELECTIONDUPLICATE},
#    {SCK_DIVIDE,        SCI_CTRL,       SCI_SETZOOM},
#    {SCK_TAB,           SCI_NORM,       SCI_TAB},
#    {SCK_BACK,          SCI_ALT,        SCI_UNDO},
#    {'U',               SCI_CSHIFT,     SCI_UPPERCASE},
#    {SCK_HOME,          SCI_NORM,       SCI_VCHOME},
class BeginningTextOfLine(ScintillaCmdKeyExecute):
    alias = "beginning-text-of-line"
    name = "Cursor to first non-blank character in the line"
    tooltip = "Move the cursor to the start of the current line"
    key_bindings = {'default': 'HOME', 'emacs': 'C-A',}
    cmd = wx.stc.STC_CMD_VCHOME
        
#    {SCK_HOME,          SCI_SHIFT,      SCI_VCHOMEEXTEND},
#    {SCK_HOME,          SCI_ASHIFT,     SCI_VCHOMERECTEXTEND},
# STC_CMD_VCHOMEWRAP
# STC_CMD_VCHOMEWRAPEXTEND
#    {SCK_LEFT,          SCI_CTRL,       SCI_WORDLEFT},
class PreviousWord(ScintillaCmdKeyExecute):
    alias = "previous-word"
    name = "Cursor to previous word"
    tooltip = "Move the cursor left to the previous word break"
    key_bindings = {'emacs': 'M-B',}
    cmd = wx.stc.STC_CMD_WORDLEFT

#    {SCK_LEFT,          SCI_CSHIFT,     SCI_WORDLEFTEXTEND},
# STC_CMD_WORDLEFTENDEXTEND
# STC_CMD_WORDLEFTEXTEND
#    {'/',               SCI_CTRL,       SCI_WORDPARTLEFT},
#    {'/',               SCI_CSHIFT,     SCI_WORDPARTLEFTEXTEND},
#    {'\\',              SCI_CTRL,       SCI_WORDPARTRIGHT},
#    {'\\',              SCI_CSHIFT,     SCI_WORDPARTRIGHTEXTEND},
#    {SCK_RIGHT,         SCI_CTRL,       SCI_WORDRIGHT},
class NextWord(ScintillaCmdKeyExecute):
    alias = "next-word"
    name = "Cursor to next word"
    tooltip = "Move the cursor right to the next word break"
    key_bindings = {'emacs': 'M-F',}
    cmd = wx.stc.STC_CMD_WORDRIGHT

#    {SCK_RIGHT,         SCI_CSHIFT,     SCI_WORDRIGHTEXTEND},
# STC_CMD_WORDRIGHTENDEXTEND
# STC_CMD_WORDRIGHTEXTEND
#    {SCK_ADD,           SCI_CTRL,       SCI_ZOOMIN},
#    {SCK_SUBTRACT,      SCI_CTRL,       SCI_ZOOMOUT},



class ScintillaCommandsPlugin(IPeppyPlugin):
    def getActions(self):
        return [BeginningOfLine, BeginningTextOfLine, EndOfLine,
                PreviousLine, NextLine,
                NextCharacter, PreviousCharacter,
                NextWord, PreviousWord,
            ]
