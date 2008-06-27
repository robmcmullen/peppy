# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Graphviz DOT Language editing support.

L{Graphviz<http://graphviz.org/>} is a high quality open source
program to automatically layout directed and undirected graphs from a
text description of the node and edge relationships.  The description
language is called L{DOT<http://graphviz.org/doc/info/lang.html>} and
in most cases is generated by a program.  It is rare to write one by
hand, but when you have to, this mode is helpful.
"""

import os
import time

import wx

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.major import *


class ProgressBarTestMixin(object):
    def action(self, index=-1, multiplier=1):
        wx.CallAfter(self.statusbarTest)

    def statusbarTest(self):
        mode = self.frame.getActiveMajorMode()
        if mode is not None:
            mode.buffer.setBusy(True)
            statusbar = mode.status_info
            statusbar.startProgress("Testing...", 100, True)
            for i in range(100):
                if statusbar.isCancelled():
                    break
                statusbar.updateProgress(i)
                wx.Yield()
                time.sleep(self.delay)
            statusbar.stopProgress()
            mode.buffer.setBusy(False)

class SlowProgressBarTest(ProgressBarTestMixin, SelectAction):
    name = "Slow test of the progress bar"
    default_menu = "&Help/Tests"
    delay = .2

class FastProgressBarTest(ProgressBarTestMixin, SelectAction):
    name = "Fast test of the progress bar"
    default_menu = "&Help/Tests"
    delay = .01


class ShowStyles(SelectAction):
    name = "Show Line Style"
    tooltip = "Show the styling information of the current line"
    default_menu = "&Help/Tests"
    key_bindings = {'default': 'M-S',}

    @classmethod
    def worksWithMajorMode(self, mode):
        return hasattr(mode, 'showStyle')
    
    def action(self, index=-1, multiplier=1):
        self.mode.showStyle()


class MultiMinibufferTest(MinibufferAction):
    """Test of multiple minibuffers imbedded in a single parent"""
    name = "Multi Minibuffer Test"
    default_menu = "&Help/Tests"
    key_bindings = {'default': 'C-S-F3',}

    minibuffer = [IntMinibuffer, IntMinibuffer, TextMinibuffer]
    minibuffer_label = ["Int #1", "Int #2", "Text"]
    
    def processMinibuffer(self, minibuffer, mode, values):
        dprint(values)


class SandboxPlugin(IPeppyPlugin):
    """Plugin to register sandbox tests.
    """

    def getActions(self):
        return [SlowProgressBarTest, FastProgressBarTest, ShowStyles,
                MultiMinibufferTest]
