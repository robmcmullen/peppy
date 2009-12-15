# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Tab Change actions

A group of actions used to change the contents of the current tab to something
else, or to adjust the tabs themselves.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.frame import *
from peppy.actions import *
from peppy.debug import *


class TabLeft(SelectAction):
    alias = "tab-left"
    name = "Select Previous Tab"
    tooltip = "Move the focus to the tab left of the current tab."
    default_menu = ("Window", 210)
    key_bindings = {'default': "M-LEFT", 'mac': "C-{",}

    def action(self, index=-1, multiplier=1):
        self.frame.tabs.AdvanceSelection(False)


class TabRight(SelectAction):
    alias = "tab-right"
    name = "Select Next Tab"
    tooltip = "Move the focus to the tab right of the current tab."
    default_menu = ("Window", -200)
    key_bindings = {'default': "M-RIGHT", 'mac': "C-}",}

    def action(self, index=-1, multiplier=1):
        self.frame.tabs.AdvanceSelection(True)


class TabChangePlugin(IPeppyPlugin):
    """Yapsy plugin to register the tab change actions
    """
    def getActions(self):
        return [TabLeft, TabRight]
