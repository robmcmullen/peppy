# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""
Adapter class around PyPE's FilesystemBrowser sidebar widget.
"""

import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.buffers import *

import peppy.pype
from peppy.pype.browser import FilesystemBrowser

class FileBrowser(FramePlugin):
    keyword="filebrowser"

    default_settings = {
        'best_width': 200,
        'best_height': 500,
        'min_width': 100,
        'min_height': 100,
        }
    
    def createWindows(self,parent):
##        self.browser=wx.TextCtrl(parent, -1, "Stuff" , style=wx.TE_MULTILINE)

        self.wildcard="*"
        self.current_path=""
        
        self.browser=FilesystemBrowser(parent, self)
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption("File List (from PyPE)")
        paneinfo.Left()
        paneinfo.BestSize(wx.Size(self.settings.best_width,
                                  self.settings.best_height))
        paneinfo.MinSize(wx.Size(self.settings.min_width,
                                 self.settings.min_height))
        
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
