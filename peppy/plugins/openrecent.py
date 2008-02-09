# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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
from peppy.actions import *
from peppy.lib.userparams import *


class RecentFiles(OnDemandGlobalListAction):
    name=_("Open Recent")
    default_menu = ("File", 10)
    inline=False
    
    @classmethod
    def append(cls, msg):
        buffer = msg.data
        url = buffer.url
        
        # skip files with the about: protocol
        if url.scheme == 'about':
            return

        item = unicode(url)
        # if we're adding an item that's already in the list, move it
        # to the top of the list by recreating the list
        storage = RecentFiles.storage
        if item in storage:
            newlist=[item]
            for olditem in storage:
                if olditem != item:
                    newlist.append(olditem)
            RecentFiles.setStorage(newlist)
        else:
            # New items are added at the top of this list
            storage[0:0]=[item]
            RecentFiles.setStorage(storage)

        # Trim list to max number of items
        RecentFiles.trimStorage(RecentFilesPlugin.classprefs.list_length)
            
        cls.calcHash()
        
    def action(self, index=-1, multiplier=1):
        assert self.dprint("opening file %s" % (RecentFiles.storage[index]))
        self.frame.open(RecentFiles.storage[index])



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
        storage=[]
        pathname = self.getFile()
        try:
            fh=open(pathname)
            for line in fh:
                storage.append(line.decode('utf8').rstrip())
        except:
            pass
        RecentFiles.setStorage(storage)

    def requestedShutdown(self):
        pathname = self.getFile()
        fh=open(pathname,'w')
        for file in RecentFiles.storage:
            #print "saving %s to %s" % (file,pathname)
            fh.write("%s%s" % (file.encode('utf8'),os.linesep))

    def getActions(self):
        yield RecentFiles
