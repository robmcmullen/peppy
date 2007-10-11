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

Registering your minor mode means creating a yapsy plugin extending
the IPeppyPlugin interface that returns a list of minor modes through
the getMinorModes method.
"""

import os,re

import wx

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.debug import *
from peppy.lib.userparams import *

class MinorMode(ClassPrefs, debugmixin):
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

    default_classprefs = (
        # Set default size here.  Probably should override best_*
        # sizes in subclass
        IntParam('best_width', 100),
        IntParam('best_height', 100),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        )

    @classmethod
    def getValidMinorModes(cls, mode):
        valid = []
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            for minor in plugin.getMinorModes():
                if minor.worksWithMajorMode(mode):
                    valid.append(minor)
        dprint(valid)
        return valid

    @classmethod
    def worksWithMajorMode(self, mode):
        raise NotImplementedError("Must override this each minor mode subclass to determine if it can work with specified major mode")
    
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
        paneinfo.BestSize(wx.Size(self.classprefs.best_width,
                                  self.classprefs.best_height))
        paneinfo.MinSize(wx.Size(self.classprefs.min_width,
                                 self.classprefs.min_height))
        return paneinfo

    def paneInfoHook(self, paneinfo):
        """Hook to modify the paneinfo object before the major mode
        does anything with it.
        """
        pass
