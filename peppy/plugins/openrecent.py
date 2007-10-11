# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Recently-loaded files plugin.  This plugin demonstrates many features
of plugins, including bundling of many interfaces into one class,
OpenRecentConfExtender.  It adds an item to the menu bar, hooks into
the buffer load routine, and hooks into the configuration file load
and save process.
"""
import os

from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.lib.userparams import *


class RecentFiles(GlobalList):
    name=_("Open Recent")
    inline=False

    storage=[]
    others=[]

    @classmethod
    def append(cls, msg):
        buffer = msg.data
        url = buffer.url
##        dprint("BEFORE: storage: %s" % cls.storage)
##        dprint("BEFORE: others: %s" % cls.others)
        
        # skip files with the about: protocol
        if url.protocol == 'about':
            return

        item = str(url)
        # if we're adding an item that's already in the list, move it
        # to the top of the list by recreating the list
        if item in cls.storage:
            newlist=[item]
            for olditem in cls.storage:
                if olditem != item:
                    newlist.append(olditem)
            cls.storage=newlist
        else:
            # New items are added at the top of this list
            cls.storage[0:0]=[item]

        # Trim list to max number of items
        if len(cls.storage)>RecentFilesPlugin.classprefs.list_length:
            cls.storage[RecentFilesPlugin.classprefs.list_length:]=[]
        cls.update()
##        dprint("AFTER: storage: %s" % cls.storage)
##        dprint("AFTER: others: %s" % cls.others)
        
    def action(self, index=-1, multiplier=1):
        assert self.dprint("opening file %s" % (self.storage[index]))
        self.frame.open(self.storage[index])



class RecentFilesPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('history_file', 'recentfiles.txt', 'Filename used in the peppy configuration directory\nto store the list of recently opened files.'),
        IntParam('list_length', 10, 'Truncate the list to this number of\nfiles most recently opened.'),
        )

    def activate(self):
        IPeppyPlugin.activate(self)
        Publisher().subscribe(RecentFiles.append, 'buffer.opened')

    def deactivate(self):
        IPeppyPlugin.deactivate(self)
        Publisher().unsubscribe(RecentFiles.append)
        
    @classmethod
    def getFile(cls):
        filename=cls.classprefs.history_file
        app = wx.GetApp()
        pathname=app.getConfigFilePath(filename)
        return pathname

    def initialActivation(self):
        pathname = self.getFile()
        try:
            fh=open(pathname)
            RecentFiles.storage=[]
            for line in fh:
                RecentFiles.storage.append(line.rstrip())
            RecentFiles.update()
        except:
            pass

    def requestedShutdown(self):
        pathname = self.getFile()
        fh=open(pathname,'w')
        for file in RecentFiles.storage:
            #print "saving %s to %s" % (file,pathname)
            fh.write("%s%s" % (file,os.linesep))

    def getMenuItems(self):
        yield (None,_("File"),MenuItem(RecentFiles).after(_("&Open File...")).before("opensep"))
