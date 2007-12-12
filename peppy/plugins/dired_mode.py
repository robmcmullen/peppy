# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Dired Mode

Major mode for displaying a list of files in a directory
"""

import os

import wx

import peppy.vfs as vfs

from peppy.lib.columnsizer import *

from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.buffers import *
from peppy.debug import *


class DiredSTC(NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    pass


class DiredRefresh(SelectAction):
    """Refresh the current list"""
    alias = "dired-refresh"
    name = "Refresh"
    tooltip = "Refresh the current view to show any changes."
    default_menu = ("Actions", -1000)
    key_bindings = {'default': "F5", }

    def action(self, index=-1, multiplier=1):
        self.mode.editwin.reset()


class FlagMixin(object):
    """Mixin to set a flag and move to the next item in the list"""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.editwin.setFlag(self.flag)
        self.mode.editwin.moveSelected(multiplier)

class FlagBackwardsMixin(object):
    """Mixin to set a flag and move to the previous item in the list."""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.editwin.setFlag(self.flag)
        self.mode.editwin.moveSelected(-1)


class DiredNext(FlagMixin, SelectAction):
    alias = "dired-next"
    name = "Move to Next Item"
    tooltip = "Move the selection to the next item in the list."
    default_menu = ("Actions", 100)
    key_bindings = {'default': "N", }

class DiredPrevious(FlagBackwardsMixin, SelectAction):
    alias = "dired-previous"
    name = "Move to Previous Item"
    tooltip = "Move the selection to the previous item in the list."
    default_menu = ("Actions", 101)
    key_bindings = {'default': "P", }


class DiredDelete(FlagMixin, SelectAction):
    alias = "dired-delete"
    name = "Mark for Deletion"
    tooltip = "Mark the selected buffer for deletion."
    default_menu = ("Actions", 120)
    key_bindings = {'default': "D", }
    flag = 'D'

class DiredDeleteBackwards(FlagBackwardsMixin, SelectAction):
    alias = "dired-delete-backwards"
    name = "Mark for Deletion and Move Backwards"
    tooltip = "Mark the selected buffer for deletion and move to the previous item."
    default_menu = ("Actions", 121)
    key_bindings = {'default': "C-D", }
    flag = 'D'


class DiredSave(FlagMixin, SelectAction):
    alias = "dired-save"
    name = "Mark for Save"
    tooltip = "Mark the selected buffer to be saved."
    default_menu = ("Actions", -110)
    key_bindings = {'default': "S", }
    flag = 'S'

class DiredSaveBackwards(FlagBackwardsMixin, SelectAction):
    alias = "dired-save-backwards"
    name = "Mark for Save and Move Backwards"
    tooltip = "Mark the selected buffer to be saved and move to the previous item."
    default_menu = ("Actions", 111)
    key_bindings = {'default': "C-S", }
    flag = 'S'


class DiredMark(FlagMixin, SelectAction):
    alias = "dired-mark"
    name = "Mark for Display"
    tooltip = "Mark the selected buffer to be displayed."
    default_menu = ("Actions", 130)
    key_bindings = {'default': "M", }
    flag = 'M'

class DiredMarkBackwards(FlagBackwardsMixin, SelectAction):
    alias = "dired-mark-backwards"
    name = "Mark for Display and Move Backwards"
    tooltip = "Mark the selected buffer to be displayed and move to the previous item."
    default_menu = ("Actions", 130)
    key_bindings = {'default': "C-M", }
    flag = 'M'


class DiredClearFlags(SelectAction):
    alias = "dired-clear-flags"
    name = "Clear Flags"
    tooltip = "Clear all flags from the selected item(s)."
    default_menu = ("Actions", 199)
    key_bindings = {'default': "U", }

    def action(self, index=-1, multiplier=1):
        self.mode.editwin.clearFlags()
        if multiplier > 1: multiplier = -1
        self.mode.editwin.moveSelected(multiplier)


class DiredExecute(SelectAction):
    alias = "dired-execute"
    name = "Save or Delete Marked Buffers"
    tooltip = "Act on the marked buffers according to their flags."
    default_menu = ("Actions", -300)
    key_bindings = {'default': "X", }

    def action(self, index=-1, multiplier=1):
        self.mode.editwin.execute()


class DiredShow(SelectAction):
    alias = "dired-show"
    name = "Show Buffer"
    tooltip = "Show the buffer in a new tab."
    default_menu = ("Actions", -400)
    key_bindings = {'default': "O", }

    def action(self, index=-1, multiplier=1):
        buffer = self.mode.editwin.getFirstSelectedBuffer()
        if buffer:
            self.frame.newBuffer(buffer)

class DiredReplace(SelectAction):
    alias = "dired-replace"
    name = "Replace Buffer"
    tooltip = "Show the buffer in place of this tab."
    default_menu = ("Actions", 401)
    key_bindings = {'default': "F", }

    def action(self, index=-1, multiplier=1):
        buffer = self.mode.editwin.getFirstSelectedBuffer()
        if buffer:
            self.frame.setBuffer(buffer)


class DiredEditor(wx.ListCtrl, ColumnSizerMixin, debugmixin):
    """ListCtrl to show list of buffers and operate on them.
    """
    debuglevel = 0

    def __init__(self, parent, mode):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)
        self.mode = mode

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
#        Publisher().subscribe(self.reset, 'buffer.opened')
#        Publisher().subscribe(self.reset, 'buffer.closed')
#        Publisher().subscribe(self.reset, 'buffer.modified')

        self.flags = {}

        self.createColumns()
        self.updating = False
        self.url = self.mode.buffer.url
        self.reset()
        self.setSelectedIndexes([0])
    
    def deletePreHook(self):
        Publisher().unsubscribe(self.reset)

    def createColumns(self):
        self.InsertColumn(0, "Flags")
        self.InsertColumn(1, "Filename")
        self.InsertColumn(2, "Size")
        self.InsertColumn(3, "Mode")
        self.InsertColumn(4, "URL")

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        path = self.GetItem(index, 4).GetText()
        self.dprint("clicked on %d: path=%s" % (index, path))
        self.mode.frame.open(path)

    def setSelectedIndexes(self, indexes):
        """Highlight the rows contained in the indexes array"""
        
        list_count = self.GetItemCount()
        for index in range(list_count):
            if index in indexes:
                self.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            else:
                self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

    def getSelectedIndexes(self):
        """Return an array of indexes that are currently selected."""
        
        indexes = []
        index = self.GetFirstSelected()
        while index != -1:
            assert self.dprint("index %d" % (index, ))
            indexes.append(index)
            index = self.GetNextSelected(index)
        return indexes
    
    def getFirstSelectedBuffer(self):
        """Get the Buffer object of the first selected item in the list."""
        index = self.GetFirstSelected()
        if index == -1:
            return None
        key = self.GetItem(index, 4).GetText()
        buffer = Dired.findBufferByURL(key)
        return buffer

    def moveSelected(self, dir):
        """Move the selection up or down.
        
        If dir < 0, move the selection to the item before the first currently
        selected item, and if dir > 0 move the selection to after the last
        item that is currently selected.
        """
        indexes = self.getSelectedIndexes()
        if not indexes:
            return
        index = None
        if dir < 0:
            index = indexes[0] - 1
            if index < 0:
                index = 0
        elif dir > 0:
            index = indexes[-1] + 1
            if index >= self.GetItemCount():
                index = self.GetItemCount() - 1
        if index is not None:
            self.setSelectedIndexes([index])
    
    def getFlags(self, key):
        """Get the flags for the given key.
        
        If the key has not been seen before, create an initial state for those
        flags (which is all flags cleared) and return that.
        """
        if key not in self.flags:
            self.flags[key] = ""
        return self.flags[key]
    
    def setFlag(self, flag):
        """Set the specified flag for all the selected items.
        
        flag: a single character representing the flag to set
        """
        indexes = self.getSelectedIndexes()
        for index in indexes:
            key = self.GetItem(index, 4).GetText()
            dprint("index=%d key=%s" % (index, key))
            flags = self.getFlags(key)
            if flag not in flags:
                # flags are stored as a sorted string, but there's no direct
                # way to sort a string, so it has to be converted to a list,
                # sorted, and converted back
                tmp = [f for f in flags]
                tmp.append(flag)
                tmp.sort()
                flags = "".join(tmp)
                self.flags[key] = flags
                self.SetStringItem(index, 0, flags)
    
    def clearFlags(self):
        """Clear all flags for the selected items."""
        indexes = self.getSelectedIndexes()
        for index in indexes:
            key = self.GetItem(index, 4).GetText()
            self.flags[key] = ""
            self.SetStringItem(index, 0, self.flags[key])
    
    def execute(self):
        """Operate on all the flags for each of the buffers.
        
        For each buffer item, process the flags to perform the requested action.
        """
        delete_self = None
        try:
            list_count = self.GetItemCount()
            for index in range(list_count):
                key = self.GetItem(index, 4).GetText()
                flags = self.flags[key]
                dprint("flags %s for %s" % (flags, key))
                if not flags:
                    continue
                self.updating = True
                buffer = Dired.findBufferByURL(key)
                if 'S' in flags:
                    buffer.save()
                if 'D' in flags:
                    if buffer.modified:
                        Publisher().sendMessage('peppy.log.error', "Buffer %s modified.  Not deleting.\n" % key)
                    elif buffer == self.mode.buffer:
                        # BadThings happen if you try to delete this buffer
                        # in the middle of the delete process!
                        dprint("Deleting me!  Save till later")
                        delete_self = buffer
                    elif not buffer.permanent:
                        buffer.removeAllViewsAndDelete()
                        del self.flags[key]
                        # skip processing any other flags if the buffer has
                        # been deleted.
                        continue
                elif 'M' in flags:
                    self.mode.frame.newBuffer(buffer)
                self.flags[key] = ""
        finally:
            if delete_self is not None:
                dprint("OK, now deleting myself")
                self.deletePreHook()
                # delete the buffer using call after to allow any pending
                # events to the list to be cleaned up
                wx.CallAfter(delete_self.removeAllViewsAndDelete)
            elif self.updating:
                self.updating = False
                self.reset()

    def getKey(self, name):
        url = self.url.resolve2(name)
        mode = []
        if vfs.is_folder(url):
            url.path.endswith_slash = True
            mode.append("d")
        else:
            url.path.endswith_slash = False
            mode.append("-")
        if vfs.can_read(url):
            mode.append("r")
        else:
            mode.append("-")
        if vfs.can_write(url):
            mode.append("w")
        else:
            mode.append("-")
        return url, "".join(mode)

    def reset(self, msg=None):
        """Reset the list.
        
        No optimization here, just rebuild the entire list.
        """
        if self.updating:
            # don't process if we're currently updating the list
            dprint("skipping an update while we're in the middle of an execute")
            return
        
        # FIXME: Freeze doesn't seem to work -- on windows, this list is built
        # so slowly that you can see columns being resized.
        self.Freeze()
        list_count = self.GetItemCount()
        index = 0
        cumulative = 0
        cache = []
        show = -1
        for name in vfs.get_names(self.url):
            key, mode = self.getKey(name)
            flags = self.getFlags(key)
            if index >= list_count:
                self.InsertStringItem(sys.maxint, flags)
            else:
                self.SetStringItem(index, 0, flags)
            self.SetStringItem(index, 1, name)
            self.SetStringItem(index, 2, str(vfs.get_size(key)))
            self.SetStringItem(index, 3, mode)
            self.SetStringItem(index, 4, str(key))

            index += 1
        
        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)
        if show >= 0:
            self.EnsureVisible(show)

        self.resizeColumns([-60,200,0,0,-200])
        self.Thaw()


class DiredMode(MajorMode):
    """
    A temporary Major Mode to load another mode in the background
    """
    keyword = "Dired"
    icon='icons/folder_explore.png'
    allow_threaded_loading = False
    
    stc_class = DiredSTC

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match is a folder
        if vfs.is_folder(url):
            return True
        return False

    def createEditWindow(self,parent):
        win = DiredEditor(parent, self)
        return win
    
    def deleteWindowPreHook(self):
        self.editwin.deletePreHook()


class DiredModePlugin(IPeppyPlugin):
    """Yapsy plugin to register DiredMode
    """
    def getMajorModes(self):
        yield DiredMode

    def getCompatibleActions(self, mode):
        if mode == DiredMode:
            return [
                DiredRefresh,
                DiredNext, DiredPrevious,
                DiredSave, DiredSaveBackwards,
                DiredDelete, DiredDeleteBackwards,
                DiredMark, DiredMarkBackwards,
                DiredClearFlags,
                DiredShow, DiredReplace,
                DiredExecute,
                ]
        return []
