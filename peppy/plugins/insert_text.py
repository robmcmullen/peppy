# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text insert actions.

This plugin is a collection of some actions that insert text into the STC.
"""

import os

import wx

from peppy.fundamental import FundamentalMode
from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.actions.base import *
from peppy.actions import *
from peppy.debug import *


class InsertCodePoint(SelectAction):
    """Enter a unicode character using its code point"""
    name = "Insert Unicode"
    default_menu = ("Tools", -200)
    
    def action(self, index=-1, multiplier=1):
        minibuffer = IntMinibuffer(self.mode, self, label="Code Point:")
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, val):
        try:
            text = unichr(val)
            self.mode.AddText(text)
        except Exception, e:
            self.mode.setStatusText("Invalid code point %d (%s)" % (val, e))


class InsertQuotedChar(SelectAction):
    """Quoted insert: insert the next keystroke as a raw character"""
    name = "Insert Raw Char"
    alias = "quoted-insert"
    key_bindings = {'mac': "^Q", 'emacs': "C-q", }
    default_menu = ("Tools", 201)

    def action(self, index=-1, multiplier=1):
        dprint("Repeating next %d quoted characters" % multiplier)
        self.frame.root_accel.setQuotedNext(multiplier)


class InsertRepr(SelectAction):
    """Enter a Python repr() of the string"""
    name = "Insert repr"
    default_menu = ("Tools", 202)
    
    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Text to repr():")
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.AddText(repr(text))


class OpenLine(SelectAction):
    """Enter a newline but leave the cursor where it is"""
    name = "Open Line"
    key_bindings = {'emacs': 'C-o',}
    
    def action(self, index=-1, multiplier=1):
        s = self.mode
        cursor = s.GetCurrentPos()
        if multiplier > 0:
            lines = s.getLinesep() * multiplier
            s.AddText(lines)
            s.SetAnchor(cursor)
            s.SetCurrentPos(cursor)


class InsertTextPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text insertion actions.
    """
    def getCompatibleActions(self, modecls):
        if issubclass(modecls, FundamentalMode):
            return [
                InsertCodePoint,
                InsertQuotedChar,
                InsertRepr,
                OpenLine,
                ]
