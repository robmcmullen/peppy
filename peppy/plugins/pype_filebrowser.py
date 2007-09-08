# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""
Adapter class around PyPE's FilesystemBrowser sidebar widget.
"""

import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.sidebar import *

import peppy.pype
from peppy.pype.browser import FilesystemBrowser

class FileBrowser(FilesystemBrowser, Sidebar):
    keyword = "filebrowser"
    caption = _("File List (from PyPE)")

    default_settings = {
        'best_width': 200,
        'best_height': 500,
        'min_width': 100,
        'min_height': 100,
        'show': False,
        }
    
    def __init__(self, parent):
        self.frame = parent
        self.wildcard="*"
        self.current_path=""
        
        FilesystemBrowser.__init__(self, parent, self)
        self.showstuff()

    # PyPE adapter

    def OnDrop(self,files):
        for file in files:
            self.frame.open(file)
        

class FileBrowserProvider(Component):
    implements(ISidebarProvider)

    def getSidebars(self):
        yield FileBrowser
