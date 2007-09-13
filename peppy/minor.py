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
    name = _("Minor Modes")
    inline = False
    tooltip = _("Show or hide minor mode windows")

    def getItems(self):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            return [m.caption for m in major.minor_panes]
        return []

    def isChecked(self, index):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            return major.minor_panes[index].IsShown()
        return False

    def action(self, index=0, old=-1):
        major = self.frame.getActiveMajorMode()
        if major is not None:
            major.minor_panes[index].Show(not major.minor_panes[index].IsShown())
            major._mgr.Update()


class MinorModeIncompatibilityError(Exception):
    pass

class MinorMode(ClassSettings, debugmixin):
    """
    Mixin class for all minor modes.  A minor mode should generally be
    a subclass of wx.Window (windowless minor modes are coming in the
    future).  Minor modes may also have associated with them:

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
        """Classes using this mixin should call this method, or at
        least save the major mode."""
        
        self.major = major
        self.parent = parent
        self.window = None
        self.paneinfo = None
        
    def setup(self):
        """Hook for minor modes that don't need any user inteface
        elements.

        Rather than overriding __init__, if you don't need to create
        any windows, you can override this method to register whatever
        you need to for your minor mode.
        """
        pass

    def deletePreHook(self):
        """Hook to clean up any resources before anything else is
        deleted.

        This hook is called whether or not the minor mode has a window.
        """
        pass

    def getPaneInfo(self):
        """Create the AuiPaneInfo object for this minor mode.
        """
        paneinfo = self.getDefaultPaneInfo()
        self.paneInfoHook(paneinfo)
        return paneinfo

    def getDefaultPaneInfo(self, caption=None):
        """Convenience method to create an AuiPaneInfo object.

        AuiPaneInfo objects are used by the L{BufferFrame} to position
        the new subwindow within the managed area of the major mode.
        This hooks into the class settings (through the MinorMode's
        subclassing of ClassSettings) to allow the user to specify the
        initial size of the minor mode.

        @param caption: text string that will become the caption bar
        of the Aui-managed window.
        """
        if caption is None:
            caption = self.keyword
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption(caption).Right()
        paneinfo.DestroyOnClose(False)
        paneinfo.BestSize(wx.Size(self.settings.best_width,
                                  self.settings.best_height))
        paneinfo.MinSize(wx.Size(self.settings.min_width,
                                 self.settings.min_height))
        return paneinfo

    def paneInfoHook(self, paneinfo):
        """Hook to modify the paneinfo object before the major mode
        does anything with it.
        """
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

class MinorModeLoader(Component, debugmixin):
    """
    Trac component that handles minor mode loading.
    """
    debuglevel=0
    extensions=ExtensionPoint(IMinorModeProvider)
    implements(IMenuItemProvider)

    def __init__(self):
        # Only call this once.  Check for presense of class attribute
        if hasattr(MinorModeLoader, 'modekeys'):
            return self

        # Create the class attribute
        MinorModeLoader.modekeys={}
        
        for ext in self.extensions:
            for minor in ext.getMinorModes():
                assert self.dprint("Registering minor mode %s" % minor.keyword)
                MinorModeLoader.modekeys[minor.keyword]=minor

    default_menu=((_("View"), MenuItem(MinorModeShow).first().after(_("Major Mode"))),
                  )

    def getMenuItems(self):
        for menu, item in self.default_menu:
            yield (None, menu, item)


    def getClasses(self, major, minorlist=[]):
        """Return a list of classes corresponding to the minor mode names"""
        
        assert self.dprint("Loading minor modes %s for %s" % (str(minorlist), major))

        classes = []
        for keyword in minorlist:
            if keyword in MinorModeLoader.modekeys:
                assert self.dprint("found %s" % keyword)
                minor=MinorModeLoader.modekeys[keyword]
                classes.append(minor)
        return classes
