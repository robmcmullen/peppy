# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Recently-loaded files plugin.

This plugin demonstrates many features of plugins, including bundling of many
interfaces into one class, interfacing with the popup menu system, adding menu
items to the menu bar, how to hook into the buffer load routine, and hooking
into the configuration file load and save process.
"""
import os

from peppy.third_party.pubsub import pub
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.lib.userparams import *
from peppy.lib.dropscroller import ListReorderDialog

import peppy.vfs as vfs

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
    osx_minimal_menu = True
    
    #: Controls where the new files are added: top or bottom
    add_at_top = True
    
    #: This value is used as the keyword into RecentFilesPlugin's classprefs
    # to determine the filename containing the history list
    save_file_classpref = 'history_file'
    
    @classmethod
    def isAcceptableURL(cls, url):
        # skip files with the about: protocol
        return url.scheme != 'about' and url.scheme != 'mem'
    
    @classmethod
    def setStorage(cls, items, save=True):
        cls.storage = items
        cls.trimList()
        if save:
            pathname = RecentFilesPlugin.getFile(cls)
            fh = open(pathname,'w')
            cls.serializeStorage(fh)
    
    @classmethod
    def serializeStorage(cls, fh):
        """Serialize the current items to the file"""
        for file in cls.storage:
            fh.write("%s%s" % (file.encode('utf8'),os.linesep))
    
    @classmethod
    def loadStorage(cls):
        pathname = RecentFilesPlugin.getFile(cls)
        try:
            fh = open(pathname)
            storage = cls.unserializeStorage(fh)
        except:
            storage = []
        cls.setStorage(storage, save=False)
    
    @classmethod
    def unserializeStorage(cls, fh):
        """Unserialize items from the file into a list"""
        storage = []
        for line in fh:
            trimmed = line.decode('utf8').rstrip()
            if trimmed.strip():
                storage.append(trimmed)
        return storage
    
    @classmethod
    def append(cls, buffer=None):
        url = buffer.url
        cls.appendURL(url)
    
    @classmethod
    def trimList(cls):
        cls.trimStorage(RecentFilesPlugin.classprefs.list_length)
    
    @classmethod
    def appendURL(cls, url, extra=None):
        if cls.isAcceptableURL(url):
            item = unicode(url)
            if extra:
                item = (item, extra)
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
            
            cls.calcHash()
        
    def action(self, index=-1, multiplier=1):
        url = self.storage[index]
        assert self.dprint("opening file %s" % url)
        if vfs.exists(url):
            self.frame.open(url)
        else:
            self.frame.SetStatusText("File not found: %s" % url)


class RecentProjectFiles(RecentFiles):
    """Open a file from the list of recently opened files that belong to
    a project.
    
    Maintains a list of the most recently opened files in a project.  The list
    of files for each project is maintained separately so the list is limited
    in size by the classpref 'list_length' in L{RecentFilesPlugin}.
    """
    name = "Recent Projects"
    save_file_classpref = 'recent_project_files'
    default_menu = (("File/Recent Projects", 11), 0)
    inline = True
    
    # Have to set tooltip and global_id to None, otherwise menu system picks
    # up the values from the parent class (RecentFiles)
    global_id = None
    tooltip = None
    
    #: For this list, we add new entries at the bottom
    add_at_top = True
    
    @classmethod
    def append(cls, msg):
        mode = msg.data
        if hasattr(mode, 'project_info'):
            proj = mode.project_info
            if proj:
                name = proj.getProjectName()
                if name:
                    url = mode.buffer.url
                    cls.appendURL(url, name)
    
    @classmethod
    def serializeStorage(cls, fh):
        """Serialize the current items to the file"""
        for url, project_name in cls.storage:
            fh.write("%s%s%s%s" % (project_name.encode('utf-8'), os.linesep,
                                   url.encode('utf8'), os.linesep))
    
    @classmethod
    def unserializeStorage(cls, fh):
        """Unserialize items from the file into a list"""
        storage = []
        project_name = None
        for line in fh:
            if project_name is None:
                project_name = line.decode('utf8').strip()
            else:
                storage.append((line.decode('utf8').rstrip(), project_name))
                project_name = None
        return storage

    @classmethod
    def isAcceptableURL(cls, url):
        return True

    @classmethod
    def trimList(cls):
        list_length = RecentFilesPlugin.classprefs.list_length
        found = {}
        new_list = []
        for name, group in cls.storage:
            if group not in found:
                found[group] = 0
            if found[group] < list_length:
                new_list.append((name, group))
            found[group] += 1
        cls.storage = new_list
    
    def getItems(self):
        return self.storage
    
    def action(self, index=-1, multiplier=1):
        url, project_name = self.storage[index]
        assert self.dprint(u"opening file %s" % (url))
        self.frame.open(url)


class FileCabinet(RecentFiles):
    """Open a previously saved URL.
    
    The File Cabinet is a list of saved URLs that operate very much like
    L{RecentFiles} shown in the Open Recent menu.  The only differences are
    that the files are added only using the L{AddToFileCabinet} action, and
    the files show up in the list in the order that they were added.
    
    This list is not limited in size.
    """
    name = "File Cabinet"
    save_file_classpref = 'file_cabinet'
    default_menu = (("File/File Cabinet", 12), 0)
    inline = True
    
    # Have to set tooltip and global_id to None, otherwise menu system picks
    # up the values from the parent class (RecentFiles)
    global_id = None
    tooltip = None
    
    #: For this list, we add new entries at the bottom
    add_at_top = False

    @classmethod
    def isAcceptableURL(cls, url):
        return True

    @classmethod
    def trimList(cls):
        pass


class AddToFileCabinet(SelectAction):
    """Add to the saved URL (i.e. file cabinet) list"""
    name = "Add To File Cabinet"
    default_menu = ("File/File Cabinet", -900)
    osx_minimal_menu = True
    
    def isEnabled(self):
        return not self.frame.isOSXMinimalMenuFrame()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        # If it's called from a popup, use the tab on which it was clicked, not
        # the current mode
        if self.popup_options is not None:
            mode = self.popup_options['mode']
        else:
            mode = self.mode
        FileCabinet.appendURL(mode.buffer.url)

class ReorderFileCabinet(SelectAction):
    """Reorder list of files in File Cabinet"""
    name = "Reorder File Cabinet"
    default_menu = ("File/File Cabinet", 910)
    osx_minimal_menu = True

    def action(self, index=-1, multiplier=1):
        dlg = ListReorderDialog(self.frame, FileCabinet.storage, "Reorder File Cabinet", "URL")
        if dlg.ShowModal() == wx.ID_OK:
            items = dlg.getItems()
            FileCabinet.setStorage(items)
            FileCabinet.calcHash()
        dlg.Destroy()


class RecentFilesPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam(RecentFiles.save_file_classpref, 'recentfiles.txt', 'Filename used in the peppy configuration directory to store the list of recently opened files.'),
        IntParam('list_length', 20, 'Truncate the list to this number of files most recently opened.'),
        StrParam(RecentProjectFiles.save_file_classpref, 'recent_project_files.txt', 'Filename used in the peppy configuration directory to store the list of recently opened files.'),
        StrParam(FileCabinet.save_file_classpref, 'file_cabinet.txt', 'Filename used in the peppy configuration directory to store the list of URLs saved in the File Cabinet.'),
        )

    def activateHook(self):
        pub.subscribe(RecentFiles.append, 'buffer.opened')
        Publisher().subscribe(RecentProjectFiles.append, 'project.file.opened')
        pub.subscribe(self.getTabMenu, 'tabs.context_menu')

    def deactivateHook(self):
        pub.unsubscribe(RecentFiles.append, 'buffer.opened')
        Publisher().unsubscribe(RecentProjectFiles.append)
        pub.unsubscribe(self.getTabMenu, 'tabs.context_menu')

    @classmethod
    def getFile(cls, actioncls):
        app = wx.GetApp()
        classpref_name = actioncls.save_file_classpref
        filename = cls.classprefs._get(classpref_name)
        pathname=app.getConfigFilePath(filename)
        return pathname

    def initialActivation(self):
        RecentFiles.loadStorage()
        RecentProjectFiles.loadStorage()
        FileCabinet.loadStorage()

    def getTabMenu(self, action_classes=None):
        action_classes.extend([(-600, AddToFileCabinet)])

    def getActions(self):
        return [RecentFiles, RecentProjectFiles, FileCabinet, AddToFileCabinet, ReorderFileCabinet]
