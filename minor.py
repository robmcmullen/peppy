# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Your one-stop shop for minor mode building blocks.  Base class,
interface, loader, all you could need to define a new minor mode.
Except for examples, which are in other directories.
"""

import os,re

import wx

from trac.core import *

from configprefs import *
from debug import *

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

class MinorModeLoader(Component):
    """
    Trac component that handles minor mode loading.
    """
    extensions=ExtensionPoint(IMinorModeProvider)

    def __init__(self):
        # Only call this once.
        if hasattr(MinorModeLoader,'modekeys'):
            return self
        
        MinorModeLoader.modekeys={}
        
        for ext in self.extensions:
            for minor in ext.getMinorModes():
                dprint("Registering minor mode %s" % minor.keyword)
                MinorModeLoader.modekeys[minor.keyword]=minor

    def load(self,major,minorlist=[]):
        dprint("Loading minor modes %s for %s" % (str(minorlist),major))
        for keyword in minorlist:
            if keyword in MinorModeLoader.modekeys:
                dprint("found %s" % keyword)
                minor=MinorModeLoader.modekeys[keyword]
                major.createMinorMode(minor)


class MinorMode(ClassSettingsMixin,debugmixin):
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

    def __init__(self, major, parent):
        ClassSettingsMixin.__init__(self)
        self.major=major
        self.parent=parent

        self.setup()

        self.createWindows(self.parent)
        
    def setup(self):
        pass

    def createWindows(self,parent):
        pass

    def getDefaultPaneInfo(self,caption):
        paneinfo=wx.aui.AuiPaneInfo().Name(self.keyword).Caption(caption)
        paneinfo.BestSize(wx.Size(self.settings.best_width,
                                  self.settings.best_height))
        paneinfo.MinSize(wx.Size(self.settings.min_width,
                                 self.settings.min_height))
        return paneinfo
    
