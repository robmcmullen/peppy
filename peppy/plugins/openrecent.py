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


class OpenRecent(GlobalList, ClassPrefs):
    name=_("Open Recent")
    inline=False

    default_classprefs = (
        IntParam('list_length', 10),
        )

    storage=[]
    others=[]

    @classmethod
    def append(cls, url):
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
        if len(cls.storage)>cls.classprefs.list_length:
            cls.storage[cls.classprefs.list_length:]=[]
        cls.update()
##        dprint("AFTER: storage: %s" % cls.storage)
##        dprint("AFTER: others: %s" % cls.others)
        
    @classmethod
    def load(cls,pathname):
        try:
            fh=open(pathname)
            cls.storage=[]
            for line in fh:
                cls.storage.append(line.rstrip())
            cls.update()
        except:
            pass

    @classmethod
    def save(cls,pathname):
        fh=open(pathname,'w')
        for file in cls.storage:
            #print "saving %s to %s" % (file,pathname)
            fh.write("%s%s" % (file,os.linesep))

    def action(self,state=None,index=0):
        assert self.dprint("opening file %s" % (self.storage[index]))
        self.frame.open(self.storage[index])



class RecentFilesPlugin(IPeppyPlugin):
    def activate(self):
        IPeppyPlugin.activate(self)
        Publisher().subscribe(self.loadConf, 'peppy.config.load')
        Publisher().subscribe(self.saveConf, 'peppy.config.save')
        Publisher().subscribe(self.bufferOpened, 'buffer.opened')

    def deactivate(self):
        IPeppyPlugin.deactivate(self)
        Publisher().unsubscribe(self.loadConf)
        Publisher().unsubscribe(self.saveConf)
        Publisher().unsubscribe(self.bufferOpened)

    def loadConf(self, msg):
        app = wx.GetApp()
        filename=app.classprefs.recentfiles
        pathname=app.getConfigFilePath(filename)
        OpenRecent.load(pathname)
    
    def saveConf(self, msg):
        app = wx.GetApp()
        filename=app.classprefs.recentfiles
        pathname=app.getConfigFilePath(filename)
        OpenRecent.save(pathname)        

    def getMenuItems(self):
        yield (None,_("File"),MenuItem(OpenRecent).after(_("&Open File...")).before("opensep"))

    def bufferOpened(self, msg):
        buffer = msg.data
        OpenRecent.append(buffer.url)
