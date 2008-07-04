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


class InsertTextPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text insertion actions.
    """
    def getCompatibleActions(self, mode):
        if issubclass(mode.__class__, FundamentalMode):
            return [InsertCodePoint,
                    ]
        return []
