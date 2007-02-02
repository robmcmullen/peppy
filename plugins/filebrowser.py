import os

from menu import *
from debug import *
from trac.core import *
from plugin import *

from pype.browser import FilesystemBrowser

class FileBrowser(FramePlugin):
    keyword="filebrowser"

    def createWindows(self,parent):
##        self.browser=wx.TextCtrl(parent, -1, "Stuff" , style=wx.TE_MULTILINE)

        self.wildcard="*"
        self.current_path=""
        
        self.browser=FilesystemBrowser(parent, self)
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption("File List").Left()
        self.frame.addPane(self.browser,paneinfo)

        self.browser.showstuff()

    # PyPE adapter

    def OnDrop(self,files):
        for file in files:
            self.frame.open(file)
        

class FileBrowserProvider(Component):
    implements(IFramePluginProvider)

    def getFramePlugins(self):
        yield FileBrowser
