# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Simple sidebar to display a hierarchy of the filesystem
"""

import os
import wx

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.sidebar import *

from peppy.configprefs import *


class FileBrowser(wx.GenericDirCtrl, Sidebar):
    keyword = "filebrowser"
    caption = "File Browser"

    default_classprefs = (
        IntParam('best_width', 300),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        BoolParam('springtab', True),
        BoolParam('show', False),
        BoolParam('show_hidden', False, 'Show hidden files?'),
        )
    
    def __init__(self, parent, *args, **kwargs):
        Sidebar.__init__(self, parent)
        self.wildcard=u"All Files (*)|*"
        self.current_path=""
        
        wx.GenericDirCtrl.__init__(self, parent, -1, style=wx.DIRCTRL_SHOW_FILTERS, size=(self.classprefs.best_width, self.classprefs.best_height), filter=self.wildcard)
        self.SetFilter(self.wildcard)
        self.ShowHidden(self.classprefs.show_hidden)
        tree = self.GetTreeCtrl()
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)

    def OnActivate(self, evt):
        path = self.GetFilePath()
        self.frame.open(path)


class FileBrowserPlugin(IPeppyPlugin):
    def getSidebars(self):
        yield FileBrowser
