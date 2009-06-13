# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Simple sidebar to display a hierarchy of the filesystem
"""

import os, os.path
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
        self.wildcard=u"All Files (*)|*"
        
        # Must initialize the wx component first, otherwise will get strange
        # errors because the event handler called by Sidebar.__init__ allows
        # an event to be processed before the two-phase init of the window is
        # finished.  See bug #566 for more info.
        wx.GenericDirCtrl.__init__(self, parent, -1, style=wx.DIRCTRL_SHOW_FILTERS, size=(self.classprefs.best_width, self.classprefs.best_height), filter=self.wildcard)
        Sidebar.__init__(self, parent)
        
        self.current_path=""
        self.SetFilter(self.wildcard)
        self.ShowHidden(self.classprefs.show_hidden)
        tree = self.GetTreeCtrl()
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
    
    def activateSpringTab(self):
        """Callback function from the SpringTab handler requesting that we
        initialize ourselves.
        
        """
        mode = self.frame.getActiveMajorMode()
        path = mode.buffer.cwd()
        self.ExpandPath(path)

    def OnActivate(self, evt):
        path = self.GetFilePath()
        if os.path.isfile(path):
            self.frame.open(path)
        else:
            evt.Skip()


class FileBrowserPlugin(IPeppyPlugin):
    def getSidebars(self):
        yield FileBrowser
