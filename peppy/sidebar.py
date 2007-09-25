# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Your one-stop shop for sidebar building blocks.

Sidebars provide extra UI windows for frames that aren't dependent (or
can exist outside of) a major mode.

A sidebar is created by subclassing from some wx.Window object and
using the Sidebar mixin.

Registering your sidebar means creating a yapsy plugin extending the
IPeppyPlugin interface that returns a list of sidebars through the
getSidebars method.
"""

import os,re

import wx

from peppy.menu import *
from peppy.debug import *
from peppy.lib.userparams import *


class Sidebar(ClassPrefs, debugmixin):
    """Mixin class for all frame sidebars.

    A frame sidebar is generally used to create a new UI window in a
    frame that is outside the purview of the major mode.  It is a
    constant regardless of which major mode is selected.
    """
    keyword = None
    caption = None

    default_classprefs = (
        IntParam('best_width', 100),
        IntParam('best_height', 200),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        BoolParam('show', True),
        )

    @classmethod
    def getSidebarMap(cls):
        # Only call this once.
        if hasattr(Sidebar,'sidebarmap'):
            return cls.sidebarmap
        
        cls.sidebarmap={}
        
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for ext in plugins:
            for sidebar in ext.getSidebars():
                #dprint("Registering frame sidebar %s" % sidebar.keyword)
                cls.sidebarmap[sidebar.keyword]=sidebar
        return cls.sidebarmap

    @classmethod
    def getClasses(cls, frame, sidebarlist=[]):
        #dprint("Loading sidebars %s for %s" % (str(sidebarlist),frame))
        classes = []
        sidebarmap = cls.getSidebarMap()
        for keyword in sidebarlist:
            keyword = keyword.strip()
            if keyword in sidebarmap:
                #self.dprint("found %s" % keyword)
                sidebar = sidebarmap[keyword]
                classes.append(sidebar)
        return classes

    def __init__(self, frame):
        self.frame=frame
        
    def getPaneInfo(self):
        """Create the AuiPaneInfo object for this minor mode.
        """
        paneinfo = self.getDefaultPaneInfo()
        self.paneInfoHook(paneinfo)
        return paneinfo

    def getDefaultPaneInfo(self):
        """Factory method to return pane info.

        Most sidebars won't need to override this, but it is available
        in the case that it is necessary.  A wx.aui.AuiPaneInfo object
        should be returned.
        """
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption(self.caption)
        paneinfo.BestSize(wx.Size(self.classprefs.best_width,
                                  self.classprefs.best_height))
        paneinfo.MinSize(wx.Size(self.classprefs.min_width,
                                 self.classprefs.min_height))
        paneinfo.Show(self.classprefs.show)
        return paneinfo

    def paneInfoHook(self, paneinfo):
        """Hook to modify the paneinfo object before the major mode
        does anything with it.
        """
        pass
