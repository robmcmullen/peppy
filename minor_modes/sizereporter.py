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
