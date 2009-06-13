# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Simple sidebar to display a hierarchy of the filesystem
"""

import os, os.path, time
import wx

from peppy.actions import *
from peppy.sidebar import *

from peppy.configprefs import *

from projecttree import ProjectTree

class ProjectSidebar(ProjectTree, Sidebar):
    keyword = "projectsidebar"
    caption = "Projects"

    default_classprefs = (
        IntParam('best_width', 300),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        BoolParam('springtab', True),
        BoolParam('show', False),
        )
    
    def __init__(self, parent, *args, **kwargs):
        Sidebar.__init__(self, parent)
        ProjectTree.__init__(self, parent, None, size=(self.classprefs.best_width, self.classprefs.best_height))
        
        self.isBusy = 0
        self.start_busy = None
        self.progress = None
        self.timer = None
        self.Bind(wx.EVT_TIMER, self.OnTick)
    
    def activateSpringTab(self):
        """Callback function from the SpringTab handler requesting that we
        initialize ourselves.
        
        """
        paths = self.getProjectPaths()
        known = ProjectPlugin.getKnownProjects()
        for url, project_info in known.iteritems():
            path = os.path.normpath(str(url.path))
            if path not in paths:
                self.addProject(path, options={'name': project_info.getProjectName()})

        mode = self.frame.getActiveMajorMode()
        self.ensurePathVisible(unicode(mode.buffer.url.path))
        self.StartBusy("Scanning Project Directories for File Changes")
        wx.GetApp().Yield(True)
        self.updateTreeIfNewEntriesFound()
        self.StopBusy()
    
    def updateTreeIfNewEntriesFound(self, parent=None):
        """Add watchers that will update each subdirectory.
        
        When this is made visible, it's possible that enough time has elapsed
        that the filesystem has changed since the last time the tree was
        updated.  The ProjectTree watchers can be used to recreate the trees,
        but we have to do it on every tree node that has children.
        """
        if parent is None:
            parent = self.root
        nodes = self.getChildren(parent)
        for node in nodes:
            if self.tree.ItemHasChildren(node) and self.tree.IsExpanded(node):
                path = self.tree.GetPyData(node)['path']
                self.dprint("adding %s to watch list" % path)
                self.addDirectoryWatcher(node)
                #self.watchDirectory(path, flag=True, data=node, delay=0)
                self.updateTreeIfNewEntriesFound(node)
                wx.GetApp().Yield(True)

    def openFiles(self, files):
        for file in files:
            self.frame.findTabOrOpen(file)

    def OnTick(self, evt):
        """Pulse the indicator on every tick of the clock"""
        self.progress.updateProgress(-1)

    def StartBusy(self, message="Querying SCM"):
        """Show and start the busy indicator"""
        self.isBusy += 1
        if self.isBusy > 1:
            return

        mode = self.frame.getActiveMajorMode()
        self.progress = mode.status_info
        self.progress.startProgress(message)
        self.progress_message = message
        self.start_busy = time.time()
        self.timer = wx.Timer(self)
        self.timer.Start(100)

    def StopBusy(self, message=None):
        """Stop and then hide the busy indicator"""
        self.isBusy -= 1
        if self.isBusy > 0:
            return
        if self.timer.IsRunning():
            self.timer.Stop()
        if not message:
            message = "Finished %s in %0.2fs" % (self.progress_message, time.time() - self.start_busy)
        self.progress.stopProgress(message)
        self.progress = None
        self.timer = None

