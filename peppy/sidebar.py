# peppy Copyright (c) 2006-2010 Rob McMullen
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
import peppy.third_party.aui as aui

from peppy.actions import *
from peppy.debug import *
from peppy.lib.userparams import *
from peppy.lib.processmanager import *

from peppy.context_menu import ContextMenuMixin

class Sidebar(ContextMenuMixin, ClassPrefs, debugmixin):
    """Mixin class for all frame sidebars.

    A frame sidebar is generally used to create a new UI window in a
    frame that is outside the purview of the major mode.  It is a
    constant regardless of which major mode is selected.
    """
    keyword = None
    caption = None

    default_classprefs = (
        # FIXME: the AUI manager always seems to go with the minimum size
        # on the initial setup.  Don't know why this is yet...
        IntParam('best_width', 100, 'Desired width of sidebar in pixels'),
        IntParam('best_height', 100, 'Desired height of sidebar in pixels'),
        IntParam('min_width', 100, 'Minimum width of sidebar in pixels\nenforced by the AuiManager'),
        IntParam('min_height', 100, 'Minimum height of sidebar in pixels\nenforced by the AuiManager'),
        BoolParam('springtab', False, 'Display in a springtab instead of its own sidebar window'),
        BoolParam('show', True),
        )

    @classmethod
    def getClasses(cls, frame):
        cls.dprint("Loading sidebars for %s" % (frame))
        classes = []
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            for sidebar in plugin.getSidebars():
                cls.dprint("found %s" % sidebar.keyword)
                classes.append(sidebar)
        return classes

    def __init__(self, parent, *args, **kwargs):
        self.frame = self.findFrameInWindowHierarchy(parent)
        wx.CallAfter(self.initPostCallback)
    
    def __del__(self):
        self.removeListeners()
    
    def getFrame(self):
        return self.frame
    
    def findFrameInWindowHierarchy(self, parent):
        """Utility function to find the peppy frame given the parent window.
        
        It's not always the case that they immediate parent of this window
        will be the L{BufferFrame}, for example when the sidebar is used in
        a L{SpringTab}, the parent of the sidebar will actually be a pop-up
        window.  This method finds the frame in the ancestry that is the real
        peppy frame.
        """
        while parent is not None:
            if isinstance(parent, wx.Frame) and hasattr(parent, 'open'):
                self.dprint("Found frame: %s" % parent)
                break
            parent = parent.GetParent()
        return parent

    def initPostCallback(self):
        """Callback method called to register any event handlers or
        publish/subscribe messages
        """
        self.createContextMenuEventBindings()
        self.createEventBindings()
        self.createListeners()
    
    def activateSidebar(self):
        """Called by frame construction to signify that the sidebar window is
        ready to be drawn.
        
        Should be overridden by the subclass if some special initialization
        needs to be performed.
        """
        pass
    
    def getOptionsForPopupActions(self):
        options = {'sidebar': self}
        return options

    def createEventBindings(self):
        """Hook to create any event bindings needed by the sidebar.
        """
        pass
    
    def createListeners(self):
        """Hook to register any publish/subscribe messages needed by the
        sidebar.
        """
        pass
    
    def removeListeners(self):
        """Hook to remove any publish/subscribe listeners subscribed to in
        L{createListeners}
        """
        pass
    
    def getPaneInfo(self):
        """Create the AuiPaneInfo object for this sidebar.
        """
        paneinfo = self.getDefaultPaneInfo()
        self.paneInfoHook(paneinfo)
        return paneinfo

    def getDefaultPaneInfo(self):
        """Factory method to return pane info.

        Most sidebars won't need to override this, but it is available
        in the case that it is necessary.  A aui.AuiPaneInfo object
        should be returned.
        """
        paneinfo = aui.AuiPaneInfo().Name(self.keyword).Caption(self.caption)
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


class JobOutputSidebarController(JobOutputMixin):
    """Simple wrapper around the JobOutputMixin interface to direct all output
    to the Information sidebar.
    """
    def __init__(self, frame, startCallback, finishCallback):
        self.frame = frame
        self.startCallback = startCallback
        self.finishCallback = finishCallback
        
    def startupCallback(self, job):
        """Callback from the JobOutputMixin when a job is successfully
        started.
        """
        self.startCallback(job)
        text = "\n" + job.getStartMessage()
        Publisher().sendMessage('peppy.log.info', (self.frame, text))

    def stdoutCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stdout."""
        Publisher().sendMessage('peppy.log.info', (self.frame, text))

    def stderrCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stderr."""
        Publisher().sendMessage('peppy.log.info', (self.frame, text))

    def finishedCallback(self, job):
        """Callback from the JobOutputMixin when the job terminates."""
        self.finishCallback(job)
        text = "\n" + job.getFinishMessage()
        Publisher().sendMessage('peppy.log.info', (self.frame, text))
