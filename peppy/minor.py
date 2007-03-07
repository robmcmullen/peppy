# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Your one-stop shop for minor mode building blocks.

Minor modes provide enhancements to a major mode or a set of major
modes.  They can be very limited and only apply to some major modes,
or more general and be applicable to lots of major modes.  It just
depends on the implementation and what the goals are.

A minor mode is created by subclassing from L{MinorMode} and
implementing the L{createWindows} method if you are adding a window to
the major mode's AuiManager area, or implementing L{setup} if you
don't need an element.

Registering your minor mode means creating a trac.core.Component that
implements the L{IMinorModeProvider} interface.  This Component can
also implement L{IMenuItemProvider} and L{IToolBarItemProvider} to
provide other user interface elements.
"""

import os,re

import wx

from trac.core import *

from menu import *
from configprefs import *
from debug import *

class MinorModeShow(ToggleListAction):
    name="Minor Modes"
    inline=False
    tooltip="Show or hide minor mode windows"

    def getItems(self):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            return [m.caption for m in major.minors]
        return []

    def isChecked(self, index):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            return major.minors[index].IsShown()
        return False

    def action(self, index=0, old=-1):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            major.minors[index].Show(not major.minors[index].IsShown())
            major._mgr.Update()


class MinorModeIncompatibilityError(Exception):
    pass

class IMinorModeProvider(Interface):
    """
    Used to register a new minor mode.
    """

    def getMinorModes():
        """
        Return an iterator containing the minor mode classes
        associated with this plugin.
        """

class MinorModeLoader(Component,debugmixin):
    """
    Trac component that handles minor mode loading.
    """
    debuglevel=0
    extensions=ExtensionPoint(IMinorModeProvider)
    implements(IMenuItemProvider)

    def __init__(self):
        # Only call this once.
        if hasattr(MinorModeLoader,'modekeys'):
            return self
        
        MinorModeLoader.modekeys={}
        
        for ext in self.extensions:
            for minor in ext.getMinorModes():
                assert self.dprint("Registering minor mode %s" % minor.keyword)
                MinorModeLoader.modekeys[minor.keyword]=minor

    default_menu=(("View",MenuItem(MinorModeShow).first().after("Major Mode")),
                  )

    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)


    def load(self,major,minorlist=[]):
        assert self.dprint("Loading minor modes %s for %s" % (str(minorlist),major))
        for keyword in minorlist:
            if keyword in MinorModeLoader.modekeys:
                assert self.dprint("found %s" % keyword)
                minor=MinorModeLoader.modekeys[keyword]
                major.createMinorMode(minor)


class MinorMode(ClassSettings,debugmixin):
    """
    Base class for all minor modes.  A minor mode doesn't have to
    create any of the following, but it can:

    * a window (or multiple windows) within the major mode AUI manager

    * menu, toolbar items -- but note that these will be created using
      the IMenuBarItemProvider and IToolBarItemProvider interfaces,
      not the minor mode itself.

    * status buttons in the frame's statusbar (ala Mozilla) - not
      implemented yet, but it's coming.
    
    """

    default_settings = {
        # Set default size here.  Probably should override best_*
        # sizes in subclass
        'best_width':100,
        'best_height':100,
        'min_width':100,
        'min_height':100,
        }
    
    def __init__(self, major, parent):
        self.major=major
        self.parent=parent

        self.setup()

        self.createWindows(self.parent)
        
    def setup(self):
        """Hook for minor modes that don't need any user inteface
        elements.

        Rather than overriding __init__, if you don't need to create
        any windows, you can override this method to register whatever
        you need to for your minor mode.
        """
        pass

    def createWindows(self,parent):
        """Hook to create a window for your minor mode.

        If your minor mode needs to create a window in the major mode
        area, this is the method to use.

        @param parent: parent wx.Window that is managed by the
        BufferFrame's AuiManager
        """
        pass

    def getDefaultPaneInfo(self,caption):
        """Convenience method to create an AuiPaneInfo object.

        AuiPaneInfo objects are used by the L{BufferFrame} to position
        the new subwindow within the managed area of the major mode.
        This hooks into the class settings (through the MinorMode's
        subclassing of ClassSettings) to allow the user to specify the
        initial size of the minor mode.

        @param caption: text string that will become the caption bar
        of the Aui-managed window.
        """
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption(caption)
        paneinfo.DestroyOnClose(False)
        paneinfo.BestSize(wx.Size(self.settings.best_width,
                                  self.settings.best_height))
        paneinfo.MinSize(wx.Size(self.settings.min_width,
                                 self.settings.min_height))
        return paneinfo
    
