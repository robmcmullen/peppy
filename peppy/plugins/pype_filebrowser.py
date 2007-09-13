# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""
Adapter class around PyPE's FilesystemBrowser sidebar widget.
"""

import os

from peppy.menu import *
from peppy.trac.core import *
from peppy.sidebar import *

import peppy.pype
from peppy.pype.browser import FilesystemBrowser

class PyPEFileBrowser(FilesystemBrowser, Sidebar):
    keyword = "filebrowser"
    caption = _("File List (from PyPE)")

    default_classprefs = (
        IntParam('best_width', 200),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        BoolParam('show', False),
        )
    
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
        yield PyPEFileBrowser
