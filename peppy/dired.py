# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dired Mode

Major mode for displaying a list of files in a directory
"""

import os, datetime

import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin

import peppy.vfs as vfs

from peppy.lib.column_autosize import *

from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.buffers import *
from peppy.stcinterface import *
from peppy.debug import *


def getCompactDate(mtime, recent_months=6):
    """Get a printable representation of a date in a compact format
    
    Return a string in unix ls -l style date format, where the date in the most
    recent number of months shows the time instead of the year.  Once the time
    is older than the recent months, replace the time with the year.  E.g.
    a recent date will be displayed like "Apr 20 12:34" and a date older than
    the specified number of months will be displayed "Apr 20 1999"
    """
    recent_seconds = datetime.datetime.now() - datetime.timedelta(recent_months * 30)
    if mtime < recent_seconds:
        s = mtime.strftime("%b %d  %Y")
    else:
        s = mtime.strftime("%b %d %H:%M")
    return s


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
        self.mode.reset(sort=True)


class FlagMixin(object):
    """Mixin to set a flag and move to the next item in the list"""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        self.mode.moveSelected(multiplier)

class FlagBackwardsMixin(object):
    """Mixin to set a flag and move to the previous item in the list."""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        self.mode.moveSelected(-1)


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
        self.mode.clearFlags()
        if multiplier > 1: multiplier = -1
        self.mode.moveSelected(multiplier)


class DiredExecute(SelectAction):
    alias = "dired-execute"
    name = "Save or Delete Marked Buffers"
    tooltip = "Act on the marked buffers according to their flags."
    default_menu = ("Actions", -300)
    key_bindings = {'default': "X", }

    def action(self, index=-1, multiplier=1):
        self.mode.execute()


class DiredShow(SelectAction):
    alias = "dired-show"
    name = "Show Buffer"
    tooltip = "Show the buffer in a new tab."
    default_menu = ("Actions", -400)
    key_bindings = {'default': "O", }

    def action(self, index=-1, multiplier=1):
        url = self.mode.getFirstSelectedKey()
        if url:
            self.frame.open(url)

class DiredReplace(SelectAction):
    alias = "dired-replace"
    name = "Replace Buffer"
    tooltip = "Show the buffer in place of this tab."
    default_menu = ("Actions", 401)
    key_bindings = {'default': "F", }

    def action(self, index=-1, multiplier=1):
        url = self.mode.getFirstSelectedKey()
        if url:
            wx.CallAfter(self.frame.open, url, mode_to_replace=self.mode)


class DiredMode(wx.ListCtrl, ColumnAutoSizeMixin, ColumnSorterMixin, MajorMode):
    """Directory viewing mode

    Dired is a directory viewing mode that works like an extremely bare-bones
    file manager.
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

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT, pos=(9000,9000))
        ColumnAutoSizeMixin.__init__(self)

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.flags = {}
        self.createColumns()
        self.itemDataMap = {}
        ColumnSorterMixin.__init__(self, self.GetColumnCount())
        
        self.updating = False
        self.url = self.buffer.url
        self.reset()
        self.setSelectedIndexes([0])
        
        # Assign icons for up and down arrows for column sorter
        getIconStorage().assignList(self)
        
        # default to sort by filename
        self.SortListItems(1)
    
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self
    
    def GetSortImages(self):
        down = getIconStorage("icons/bullet_arrow_down.png")
        up = getIconStorage("icons/bullet_arrow_up.png")
        return (down, up)

    def GetSecondarySortValues(self, col, key1, key2):
        return (self.itemDataMap[key1][1], self.itemDataMap[key2][1])

    def createListenersPostHook(self):
#        Publisher().subscribe(self.reset, 'buffer.opened')
#        Publisher().subscribe(self.reset, 'buffer.closed')
#        Publisher().subscribe(self.reset, 'buffer.modified')
        pass

    def removeListenersPostHook(self):
        Publisher().unsubscribe(self.reset)

    def createColumns(self):
        self.InsertSizedColumn(0, "Flags", min=30, max=30, greedy=True)
        self.InsertSizedColumn(1, "Filename", min=100)
        self.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
        self.InsertSizedColumn(3, "Date")
        self.InsertSizedColumn(4, "Mode")
        self.InsertSizedColumn(5, "Description", min=100, greedy=True)
        self.InsertSizedColumn(6, "URL", ok_offscreen=True)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        path = self.GetItem(index, 6).GetText()
        self.dprint("clicked on %d: path=%s" % (index, path))
        self.frame.open(path)

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
    
    def getFirstSelectedKey(self):
        """Get the Buffer object of the first selected item in the list."""
        index = self.GetFirstSelected()
        if index == -1:
            return None
        key = self.GetItem(index, 6).GetText()
        return key

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
            key = self.GetItem(index, 6).GetText()
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
            key = self.GetItem(index, 6).GetText()
            self.flags[key] = ""
            self.SetStringItem(index, 0, self.flags[key])
    
    def execute(self):
        """Operate on all the flags for each of the buffers.
        
        For each buffer item, process the flags to perform the requested action.
        """
        list_count = self.GetItemCount()
        for index in range(list_count):
            url = self.GetItem(index, 6).GetText()
            flags = self.flags[url]
            dprint("flags %s for %s" % (flags, url))
            if not flags:
                continue
            if 'D' in flags:
                dprint("Not actually deleting %s" % url)
            elif 'M' in flags:
                self.frame.open(url)
            self.flags[url] = ""
            self.SetStringItem(index, 0, self.flags[url])

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

    def reset(self, msg=None, sort=False):
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
        self.itemDataMap = {}
        for name in vfs.get_names(self.url):
            # FIXME: should get_names always return unicode? Until then, create
            # a unicode version of the name
            if isinstance(name, str):
                name = name.decode("utf-8")
            key, mode = self.getKey(name)
            flags = self.getFlags(key)
            metadata = vfs.get_metadata(key)
            if index >= list_count:
                self.InsertStringItem(sys.maxint, flags)
            else:
                self.SetStringItem(index, 0, flags)
            self.SetStringItem(index, 1, name)
            self.SetStringItem(index, 2, str(metadata['size']))
            self.SetStringItem(index, 3, getCompactDate(metadata['mtime']))
            self.SetStringItem(index, 4, mode)
            desc = metadata['description']
            if not desc:
                desc = metadata['mimetype']
            self.SetStringItem(index, 5, desc)
            self.SetStringItem(index, 6, unicode(key))
            self.SetItemData(index, index)
            self.itemDataMap[index] = (index, name, metadata['size'],
                                       metadata['mtime'], mode,
                                       metadata['description'], unicode(key))

            index += 1
        
        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)
        if show >= 0:
            self.EnsureVisible(show)

        self.ResizeColumns()
        
        if sort:
            self.SortListItems()
        self.Thaw()
