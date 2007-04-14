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

class FileBrowser(Sidebar):
    keyword = "filebrowser"
    caption = _("File List (from PyPE)")

    default_settings = {
        'best_width': 200,
        'best_height': 500,
        'min_width': 100,
        'min_height': 100,
        'show': False,
        }
    
    def getSidebarWindow(self,parent):
        self.wildcard="*"
        self.current_path=""
        
        self.browser=FilesystemBrowser(parent, self)
        return self.browser

    def initPostHook(self):
        self.browser.showstuff()

    # PyPE adapter

    def OnDrop(self,files):
        for file in files:
            self.frame.open(file)
        

class FileBrowserProvider(Component):
    implements(ISidebarProvider)

    def getSidebars(self):
        yield FileBrowser
