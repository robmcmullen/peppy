# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Size reporter minor mode based on the SizeReporterCtrl from the
wxPython AUI demos.  This is about as simple as a minor mode as you
can get.  No user interaction at all, just a window that is added to
the major mode's manager.
"""

import os

import wx

from menu import *
from debug import *
from trac.core import *
from minor import *

from demos.samplewidgets import SizeReportCtrl

class SizeReporterMinorMode(MinorMode):
    keyword="sizereporter"

    def createWindows(self, parent):
        self.sizerep=SizeReportCtrl(parent,mgr=self.major._mgr)
        paneinfo=self.getDefaultPaneInfo("Size Reporter")
        paneinfo.Right()
        self.major.addPane(self.sizerep,paneinfo)
        

class SizeReporterProvider(Component):
    implements(IMinorModeProvider)

    def getMinorModes(self):
        yield SizeReporterMinorMode
