import os

from menu import *
from debug import *
from trac.core import *
from plugin import *


class OpenRecent(GlobalList):
    name="Open Recent"
    inline=False
    maxlen=6

    storage=[]
    others=[]

    @classmethod
    def append(cls,item):
        dprint("BEFORE: storage: %s" % cls.storage)
        dprint("BEFORE: others: %s" % cls.others)
        # New items are added at the top of this list
        if item in cls.storage:
            newlist=[item]
            for olditem in cls.storage:
                if olditem != item:
                    newlist.append(olditem)
            cls.storage=newlist
        else:
            cls.storage[0:0]=[item]
        if len(cls.storage)>cls.maxlen:
            cls.storage[cls.maxlen:]=[]
        cls.update()
        dprint("AFTER: storage: %s" % cls.storage)
        dprint("AFTER: others: %s" % cls.others)
        
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
        #fh=open(pathname)
        for file in cls.storage:
            print "saving %s to %s" % (file,pathname)

    def action(self,state=None,index=0):
        self.dprint("opening file %s" % (self.storage[index]))
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
        
