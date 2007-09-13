# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Your one-stop shop for sidebar building blocks.

Sidebars provide extra UI windows for frames that aren't dependent (or
can exist outside of) a major mode.

A sidebar is created by subclassing from some wx.Window object and
using the Sidebar mixin.

Registering your sidebar means creating a trac.core.Component that
implements the L{ISidebarProvider} interface.  This Component can
also implement L{IMenuItemProvider} and L{IToolBarItemProvider} to
provide other user interface elements.
"""

import os,re

import wx

from trac.core import *

from menu import *
from configprefs import *
from debug import *


class SidebarShow(ToggleListAction):
    name=_("Sidebars")
    inline=False
    tooltip=_("Show or hide sidebar windows")

    def getItems(self):
        return [m.caption for m in self.frame.sidebar_panes]

    def isChecked(self, index):
        return self.frame.sidebar_panes[index].IsShown()

    def action(self, index=0, old=-1):
        self.frame.sidebar_panes[index].Show(not self.frame.sidebar_panes[index].IsShown())
        self.frame._mgr.Update()



class Sidebar(ClassSettings):
    """Mixin class for all frame sidebars.

    A frame sidebar is generally used to create a new UI window in a
    frame that is outside the purview of the major mode.  It is a
    constant regardless of which major mode is selected.
    """
    keyword = None
    caption = None

    default_settings = {
        'best_width': 100,
        'best_height': 200,
        'min_width': 100,
        'min_height': 100,
        'show': True,
        }
    
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
        paneinfo.BestSize(wx.Size(self.settings.best_width,
                                  self.settings.best_height))
        paneinfo.MinSize(wx.Size(self.settings.min_width,
                                 self.settings.min_height))
        paneinfo.Show(self.settings.show)
        return paneinfo

    def paneInfoHook(self, paneinfo):
        """Hook to modify the paneinfo object before the major mode
        does anything with it.
        """
        pass
    


class ISidebarProvider(Interface):
    """
    Add a frame sidebar to a new frame.
    """

    def getSidebars():
        """
        Return iterator containing list of frame sidebars.
        """

class SidebarLoader(Component, debugmixin):
    debuglevel=0
    
    extensions=ExtensionPoint(ISidebarProvider)
    implements(IMenuItemProvider)

    def __init__(self):
        # Only call this once.
        if hasattr(SidebarLoader,'sidebarmap'):
            return self
        
        SidebarLoader.sidebarmap={}
        
        for ext in self.extensions:
            for sidebar in ext.getSidebars():
                assert self.dprint("Registering frame sidebar %s" % sidebar.keyword)
                SidebarLoader.sidebarmap[sidebar.keyword]=sidebar

    default_menu=((_("View"), MenuItem(SidebarShow).first().after(_("sidebars"))),
                  )

    def getMenuItems(self):
        for menu, item in self.default_menu:
            yield (None, menu, item)


    def getClasses(self,frame,sidebarlist=[]):
        assert self.dprint("Loading sidebars %s for %s" % (str(sidebarlist),frame))
        classes = []
        for keyword in sidebarlist:
            keyword = keyword.strip()
            if keyword in SidebarLoader.sidebarmap:
                assert self.dprint("found %s" % keyword)
                sidebar = SidebarLoader.sidebarmap[keyword]
                classes.append(sidebar)
        return classes

