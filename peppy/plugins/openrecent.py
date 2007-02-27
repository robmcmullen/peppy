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

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.buffers import *
from peppy.configprefs import *


class OpenRecent(GlobalList, ClassSettings):
    name="Open Recent"
    inline=False

    default_settings = {
        'list_length': 10,
        }

    storage=[]
    others=[]

    @classmethod
    def append(cls,item):
##        dprint("BEFORE: storage: %s" % cls.storage)
##        dprint("BEFORE: others: %s" % cls.others)
        
        # skip files with the about: protocol
        if item.startswith('about:'):
            return

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
        if len(cls.storage)>cls.settings.list_length:
            cls.storage[cls.settings.list_length:]=[]
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
            print "saving %s to %s" % (file,pathname)
            fh.write("%s%s" % (file,os.linesep))

    def action(self,state=None,index=0):
        assert self.dprint("opening file %s" % (self.storage[index]))
        self.frame.open(self.storage[index])



class OpenRecentConfExtender(Component):
    implements(IConfigurationExtender)
    implements(IMenuItemProvider)
    implements(IBufferOpenPostHook)

    def loadConf(self,app):
        filename=app.settings.recentfiles
        pathname=app.getConfigFilePath(filename)
        OpenRecent.load(pathname)
    
    def saveConf(self,app):
        filename=app.settings.recentfiles
        pathname=app.getConfigFilePath(filename)
        OpenRecent.save(pathname)        

    def getMenuItems(self):
        yield (None,"File",MenuItem(OpenRecent).after("&Open File...").before("opensep"))

    def openPostHook(self,buffer):
        OpenRecent.append(buffer.filename)
        
