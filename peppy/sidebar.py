# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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
    debuglevel = 0
    
    keyword = None
    caption = None

    default_classprefs = (
        # FIXME: the AUI manager always seems to go with the minimum size
        # on the initial setup.  Don't know why this is yet...
        IntParam('best_width', 100, 'Desired width of sidebar in pixels'),
        IntParam('best_height', 100, 'Desired height of sidebar in pixels'),
        IntParam('min_width', 100, 'Minimum width of sidebar in pixels\nenforced by the AuiManager'),
        IntParam('min_height', 100, 'Minimum height of sidebar in pixels\nenforced by the AuiManager'),
        BoolParam('show', True),
        )

    @classmethod
    def getClasses(cls, frame, sidebarlist=[]):
        cls.dprint("Loading sidebars %s for %s" % (str(sidebarlist),frame))
        classes = []
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            for sidebar in plugin.getSidebars():
                if sidebar.keyword in sidebarlist:
                    cls.dprint("found %s" % sidebar.keyword)
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
