# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Buffer List Mode

Major mode for displaying a list of buffers and operating on them.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.list_mode import ListModeActionMixin
from peppy.list_mode import *
from peppy.buffers import *
from peppy.stcinterface import *
from peppy.debug import *


class ListAllDocuments(SelectAction):
    """Display a list of all buffers."""
    name = "List All Documents"
    default_menu = ("Documents", 100)
    key_bindings = {'emacs': "C-x C-b", }

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:buffers")


class BufferListSTC(NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    def getShortDisplayName(self, url):
        return "Document List"


class FlagMixin(ListModeActionMixin):
    """Mixin to set a flag and move to the next item in the list"""
    flag = None
    direction = 1
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return hasattr(modecls, 'setFlag')
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        self.mode.moveSelected(multiplier * self.direction)

class FlagBackwardsMixin(FlagMixin):
    """Mixin to set a flag and move to the previous item in the list."""
    direction = -1


class BufferListDelete(FlagMixin, SelectAction):
    """Mark the selected buffer for deletion."""
    name = "Mark for Deletion"
    default_menu = ("Actions", 120)
    key_bindings = {'default': "d", }
    flag = 'D'

class BufferListDeleteBackwards(FlagBackwardsMixin, SelectAction):
    """Mark the selected buffer for deletion and move to the previous item."""
    name = "Mark for Deletion and Move Backwards"
    default_menu = ("Actions", 121)
    key_bindings = {'default': "C-d", }
    flag = 'D'


class BufferListSave(FlagMixin, SelectAction):
    """Mark the selected buffer to be saved."""
    name = "Mark for Save"
    default_menu = ("Actions", -110)
    key_bindings = {'default': "s", }
    flag = 'S'

class BufferListSaveBackwards(FlagBackwardsMixin, SelectAction):
    name = "Mark for Save and Move Backwards"
    """Mark the selected buffer to be saved and move to the previous item."""
    default_menu = ("Actions", 111)
    key_bindings = {'default': "C-s", }
    flag = 'S'


class BufferListMark(FlagMixin, SelectAction):
    """Mark the selected buffer to be displayed."""
    name = "Mark for Display"
    default_menu = ("Actions", 130)
    key_bindings = {'default': "m", }
    flag = 'M'

class BufferListMarkBackwards(FlagBackwardsMixin, SelectAction):
    """Mark the selected buffer to be displayed and move to the previous item."""
    name = "Mark for Display and Move Backwards"
    default_menu = ("Actions", 130)
    key_bindings = {'default': "C-m", }
    flag = 'M'


class BufferListClearFlags(ListModeActionMixin, SelectAction):
    """Clear all flags from the selected item(s)."""
    name = "Clear Flags"
    default_menu = ("Actions", 199)
    key_bindings = {'default': "u", }

    def action(self, index=-1, multiplier=1):
        self.mode.clearFlags()
        if multiplier > 1: multiplier = -1
        self.mode.moveSelected(multiplier)


class BufferListExecute(ListModeActionMixin, SelectAction):
    """Act on the marked buffers according to their flags."""
    name = "Save or Delete Marked Buffers"
    default_menu = ("Actions", -300)
    key_bindings = {'default': "x", }

    def action(self, index=-1, multiplier=1):
        self.mode.execute()


class BufferListShow(ListModeActionMixin, SelectAction):
    """Show the buffer in a new tab."""
    name = "Show Buffer"
    default_menu = ("Actions", -400)
    key_bindings = {'default': "o", }

    def action(self, index=-1, multiplier=1):
        buffer = self.mode.getFirstSelectedBuffer()
        if buffer:
            self.frame.newBuffer(buffer)

class BufferListReplace(ListModeActionMixin, SelectAction):
    """Show the buffer in place of this tab."""
    name = "Replace Buffer"
    default_menu = ("Actions", 401)
    key_bindings = {'default': "f", }

    def action(self, index=-1, multiplier=1):
        buffer = self.mode.getFirstSelectedBuffer()
        if buffer:
            self.frame.setBuffer(buffer)


class BufferListMode(ListMode):
    """View the list of currently opened buffers
    """
    keyword = "BufferList"
    icon='icons/page_white_stack.png'
    allow_threaded_loading = False
    
    stc_class = BufferListSTC

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:buffers
        if url.scheme == 'about' and url.path == 'buffers':
            return True
        return False

    def __init__(self, parent, wrapper, buffer, frame):
        self.flags = {}
        ListMode.__init__(self, parent, wrapper, buffer, frame)
        self.setSelectedIndexes([0])
    
    def GetSecondarySortValues(self, col, key1, key2, itemDataMap):
        return (itemDataMap[key1][1], itemDataMap[key2][1])

    def createListenersPostHook(self):
        Publisher().subscribe(self.resetList, 'buffer.opened')
        Publisher().subscribe(self.resetList, 'buffer.closed')
        Publisher().subscribe(self.resetList, 'buffer.modified')

    def removeListenersPostHook(self):
        Publisher().unsubscribe(self.resetList)

    def createColumns(self, list):
        list.InsertSizedColumn(0, "Flags", min="MMMM", max="MMMM", greedy=True)
        list.InsertSizedColumn(1, "Buffer", min=100, greedy=False)
        list.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
        list.InsertSizedColumn(3, "Mode")
        list.InsertSizedColumn(4, "URL", ok_offscreen=True)

    def getFirstSelectedBuffer(self):
        """Get the Buffer object of the first selected item in the list."""
        index = self.list.GetFirstSelected()
        if index == -1:
            return None
        key = self.list.GetItem(index, 4).GetText()
        buffer = BufferList.findBufferByURL(key)
        return buffer

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
            key = self.list.GetItem(index, 4).GetText()
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
                self.list.SetStringItem(index, 0, flags)
                self.list.itemDataMap[index][0] = flags
    
    def clearFlags(self):
        """Clear all flags for the selected items."""
        indexes = self.getSelectedIndexes()
        for index in indexes:
            key = self.list.GetItem(index, 4).GetText()
            self.flags[key] = ""
            self.list.SetStringItem(index, 0, self.flags[key])
            self.list.itemDataMap[index][0] = self.flags[key]
 
    def execute(self):
        """Operate on all the flags for each of the buffers.
        
        For each buffer item, process the flags to perform the requested action.
        """
        delete_self = None
        try:
            list_count = self.list.GetItemCount()
            for index in range(list_count):
                key = self.list.GetItem(index, 4).GetText()
                flags = self.flags[key]
                dprint("flags %s for %s" % (flags, key))
                if not flags:
                    continue
                self.updating = True
                buffer = BufferList.findBufferByURL(key)
                if 'S' in flags:
                    buffer.save()
                if 'D' in flags:
                    if buffer.modified:
                        Publisher().sendMessage('peppy.log.error', "Buffer %s modified.  Not deleting.\n" % key)
                    elif buffer == self.buffer:
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
                    self.frame.newBuffer(buffer)
                self.flags[key] = ""
        finally:
            if delete_self is not None:
                dprint("OK, now deleting myself")
                # delete the buffer using call after to allow any pending
                # events to the list to be cleaned up
                wx.CallAfter(delete_self.removeAllViewsAndDelete)
            elif self.updating:
                self.updating = False
                self.resetList()
    
    def getListItems(self):
        return BufferList.getBuffers()
    
    def getItemRawValues(self, index, buf):
        key = unicode(buf.url)
        flags = self.getFlags(key)
        # Must return a list instead of a tuple because flags gets changed
        return [flags, buf.getTabName(), buf.stc.GetLength(), buf.defaultmode.keyword, key]


class BufferListModePlugin(IPeppyPlugin):
    """Yapsy plugin to register BufferListMode
    """
    def getMajorModes(self):
        yield BufferListMode

    def getActions(self):
        return [ListAllDocuments]

    def getCompatibleActions(self, modecls):
        if issubclass(modecls, BufferListMode):
            return [
                BufferListSave, BufferListSaveBackwards,
                BufferListDelete, BufferListDeleteBackwards,
                BufferListMark, BufferListMarkBackwards,
                BufferListClearFlags,
                BufferListShow, BufferListReplace,
                BufferListExecute,
                ]
