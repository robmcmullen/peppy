# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
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

from peppy import *
from peppy.menu import *
from peppy.major import *


class SlowProgressBarTest(SelectAction):
    name = "Slow test of the progress bar"
    tooltip = "Test the progress bar"
    delay = .2

    def action(self, pos=-1):
        mode = self.frame.getActiveMajorMode()
        if mode is not None:
            mode.buffer.setBusy(True)
            statusbar = mode.statusbar
            statusbar.startProgress("Testing...", 100, True)
            for i in range(100):
                wx.Yield()
                if statusbar.isCancelled():
                    break
                statusbar.updateProgress(i)
                time.sleep(self.delay)
            statusbar.stopProgress()
            mode.buffer.setBusy(False)
        
class FastProgressBarTest(SlowProgressBarTest):
    name = "Fast test of the progress bar"
    delay = .01

class SandboxPlugin(MajorModeMatcherBase,debugmixin):
    """Plugin to register sandbox tests.
    """
    implements(IMenuItemProvider)

    default_menu=((None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(FastProgressBarTest)),
                  (None,"Test",MenuItem(SlowProgressBarTest)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)
