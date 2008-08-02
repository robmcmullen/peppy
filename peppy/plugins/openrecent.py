# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Recently-loaded files plugin.

This plugin demonstrates many features of plugins, including bundling of many
interfaces into one class, interfacing with the popup menu system, adding menu
items to the menu bar, how to hook into the buffer load routine, and hooking
into the configuration file load and save process.
"""
import os

from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.lib.userparams import *
from peppy.lib.dropscroller import ListReorderDialog

class RecentFiles(OnDemandGlobalListAction):
    """Open a file from the list of recently opened files.
    
    Maintains a list of the most recently opened files so that the next time
    you start the application you can see what you were editing last time.
    This list is automatically maintained, so every time you open a new file,
    it is added to the list.  This list is limited in size by the classpref
    'list_length' in L{RecentFilesPlugin}.
    """
    name = "Open Recent"
    default_menu = ("File", 10)
    inline = False
    add_at_top = True
    
    @classmethod
    def isAcceptableURL(cls, url):
        # skip files with the about: protocol
        return url.scheme != 'about' and url.scheme != 'mem'
    
    @classmethod
    def append(cls, msg):
        buffer = msg.data
        url = buffer.url
        cls.appendURL(url)
    
    @classmethod
    def trimList(cls):
        cls.trimStorage(RecentFilesPlugin.classprefs.list_length)
    
    @classmethod
    def appendURL(cls, url):
        if cls.isAcceptableURL(url):
            item = unicode(url)
            # if we're adding an item that's already in the list, move it
            # to the top of the list by recreating the list
            storage = cls.storage
            if item in storage:
                newlist = []
                if cls.add_at_top:
                    newlist.append(item)
                for olditem in storage:
                    if olditem != item:
                        newlist.append(olditem)
                if not cls.add_at_top:
                    newlist.append(item)
                cls.setStorage(newlist)
            else:
                # New items are added at the top of this list
                if cls.add_at_top:
                    storage[0:0]=[item]
                else:
                    storage.append(item)
                cls.setStorage(storage)

            # Trim list to max number of items
            cls.trimList()
                
            cls.calcHash()
        
    def action(self, index=-1, multiplier=1):
        assert self.dprint("opening file %s" % (self.storage[index]))
        self.frame.open(self.storage[index])


class FileCabinet(RecentFiles):
    """Open a previously saved URL.
    
    The File Cabinet is a list of saved URLs that operate very much like
    L{RecentFiles} shown in the Open Recent menu.  The only differences are
    that the files are added only using the L{AddToFileCabinet} action, and
    the files show up in the list in the order that they were added.
    
    This list is not limited in size.
    """
    name = "File Cabinet"
    default_menu = (("File/File Cabinet", 11), 0)
    inline = True
    add_at_top = False
    global_id = None
    
    # Have to set tooltip to none, otherwise menu system picks up the tooltip
    # from the parent class (RecentFiles) and doesn't attempt to scan this
    # class's docstring for the tooltip
    tooltip = None
    
    @classmethod
    def isAcceptableURL(cls, url):
        return True

    @classmethod
    def trimList(cls):
        pass

class AddToFileCabinet(SelectAction):
    """Add to the saved URL (i.e. file cabinet) list"""
    alias = "add-file-cabinet"
    name = "Add To File Cabinet"
    default_menu = (("File/File Cabinet", 11), -900)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        # If it's called from a popup, use the tab on which it was clicked, not
        # the current mode
        if hasattr(self, 'popup_options'):
            mode = self.popup_options['mode']
        else:
            mode = self.mode
        FileCabinet.appendURL(mode.buffer.url)

class ReorderFileCabinet(SelectAction):
    """Reorder list of files in File Cabinet"""
    alias = "reorder-file-cabinet"
    name = "Reorder File Cabinet"
    default_menu = (("File/File Cabinet", 11), 910)

    def action(self, index=-1, multiplier=1):
        dlg = ListReorderDialog(self.frame, FileCabinet.storage, "Reorder File Cabinet", "URL")
        if dlg.ShowModal() == wx.ID_OK:
            items = dlg.getItems()
            FileCabinet.setStorage(items)
            FileCabinet.calcHash()
        dlg.Destroy()


class RecentFilesPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('history_file', 'recentfiles.txt', 'Filename used in the peppy configuration directory to store the list of recently opened files.'),
        IntParam('list_length', 20, 'Truncate the list to this number of files most recently opened.'),
        StrParam('file_cabinet', 'file_cabinet.txt', 'Filename used in the peppy configuration directory to store the list of URLs saved in the File Cabinet.'),
        )

    def activateHook(self):
        Publisher().subscribe(RecentFiles.append, 'buffer.opened')
        Publisher().subscribe(self.getTabMenu, 'tabs.context_menu')

    def deactivateHook(self):
        Publisher().unsubscribe(RecentFiles.append)
        Publisher().unsubscribe(self.getTabMenu)

    @classmethod
    def getFile(cls, filename):
        app = wx.GetApp()
        pathname=app.getConfigFilePath(filename)
        return pathname

    @classmethod
    def loadStorage(cls, actioncls, filename):
        storage=[]
        pathname = cls.getFile(filename)
        try:
            fh=open(pathname)
            for line in fh:
                storage.append(line.decode('utf8').rstrip())
        except:
            pass
        actioncls.setStorage(storage)

    def initialActivation(self):
        self.loadStorage(RecentFiles, self.classprefs.history_file)
        self.loadStorage(FileCabinet, self.classprefs.file_cabinet)
    
    @classmethod
    def saveStorage(cls, actioncls, filename):
        pathname = cls.getFile(filename)
        fh=open(pathname,'w')
        for file in actioncls.storage:
            #print "saving %s to %s" % (file,pathname)
            fh.write("%s%s" % (file.encode('utf8'),os.linesep))

    def requestedShutdown(self):
        self.saveStorage(RecentFiles, self.classprefs.history_file)
        self.saveStorage(FileCabinet, self.classprefs.file_cabinet)

    def getTabMenu(self, msg):
        action_classes = msg.data
        action_classes.extend([AddToFileCabinet])

    def getActions(self):
        return [RecentFiles, FileCabinet, AddToFileCabinet, ReorderFileCabinet]
