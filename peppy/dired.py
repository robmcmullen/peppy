# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dired Mode

Major mode for displaying a list of files in a directory
"""

import os, datetime

import wx

import peppy.vfs as vfs

from peppy.yapsy.plugins import *
from peppy.list_mode import *
from peppy.buffers import *
from peppy.stcinterface import *
from peppy.context_menu import *
from peppy.debug import *

# Can't reliably use strftime, because it returns the month encoded in some
# coding that apparently is unable to be discovered in a cross-platform manner.
months = [None,
          _("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"),
          _("Jul"), _("Aug"), _("Sep"), _("Oct"), _("Nov"), _("Dec")]

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
        s = u"%s %02d  %s" % (months[mtime.month], mtime.day, mtime.year)
    else:
        s = u"%s %02d %02d:%02d" % (months[mtime.month], mtime.day, mtime.hour, mtime.minute)
    return s


class DiredPopupActions(ContextMenuActions):
    """Helper class to pass as an argument to the pubsub call to
    'dired.context_menu'
    """
    def __init__(self, mode, entries):
        ContextMenuActions.__init__(self)
        self.mode = mode
        self.entries = entries
    
    def getMajorMode(self):
        return self.mode
    
    def getEntries(self):
        return self.entries
    
    def getMimeType(self):
        """Returns the MIME type of the entries if they are all the same, or
        None if they are different.
        
        """
        mime = None
        for entry in self.entries:
            if mime is None:
                mime = entry.getMimeType()
            elif mime != entry.getMimeType():
                mime = None
                break
        return mime
    
    def getOptions(self):
        options = ContextMenuActions.getOptions(self)
        options['mimetype'] = self.getMimeType()
        options['dired.entries'] = self.getEntries()
        return options


class DiredEntry(object):
    """Helper class representing one line in the dired list
    
    """
    def __init__(self, index, base_url, name):
        self.index = index
        self.basename = name
        self.url, self.mode = self.getKey(base_url, name)
        self.flags = ""
        self.metadata = vfs.get_metadata(self.url)
    
    def __getitem__(self, k):
        if k==0:
            return self.index
        elif k==1:
            return self.getBasename()
        elif k==2:
            return self.getSize()
        elif k==3:
            return self.getDate()
        elif k==4:
            return self.getMode()
        elif k==5:
            return self.getDescription()
        return self.getURL()

    def getKey(self, base_url, name):
        if isinstance(name, str):
            name = name.decode("utf-8")
        url = base_url.resolve2(name)
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
        url = unicode(url)
        return url, "".join(mode)

    def getBasename(self):
        return self.basename
    
    def getURL(self):
        return self.url
    
    def getSize(self):
        return self.metadata['size']
    
    def getDate(self):
        return self.metadata['mtime']
    
    def getCompactDate(self):
        return getCompactDate(self.metadata['mtime'])
    
    def getMode(self):
        return self.mode
    
    def getDescription(self):
        desc = self.metadata['description']
        if not desc:
            desc = self.metadata['mimetype']
        return desc
    
    def getMimeType(self):
        return self.metadata['mimetype']

    def getFlags(self):
        """Get the flags for the given key.
        
        If the key has not been seen before, create an initial state for those
        flags (which is all flags cleared) and return that.
        """
        return self.flags
    
    def setFlags(self, flags):
        """Set the specified flag for all the selected items.
        
        flag: a single character representing the flag to set
        """
        self.flags = flags


class DiredSTC(NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    pass


class DiredMode(ListMode):
    """Directory viewing mode

    Dired is a directory viewing mode that works like an extremely bare-bones
    file manager.
    """
    keyword = "Dired"
    icon='icons/folder_explore.png'
    allow_threaded_loading = False
    
    stc_class = DiredSTC

    default_classprefs = (
        StrParam('sort_filenames_if_scheme', 'file', help="Comma separated list of URI schemes that cause the initial display of files to be sorted by filename"),
        )
    
    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match is a folder
        if vfs.is_folder(url):
            return True
        return False

    def __init__(self, parent, wrapper, buffer, frame):
        self.url = buffer.url
        
        # Need to maintain two maps; the original order based on the index
        # number when the entries were inserted into the list, and the
        # standard itemDataMap list.  itemDataMap maintains the current order
        # that is used by the ColumnSorterMixin to reorder the list when one
        # of the column headings is clicked.
        self.origDataMap = {}
        
        ListMode.__init__(self, parent, wrapper, buffer, frame)
    
    def setViewPositionData(self, options=None):
        self.resetList()
        self.setSelectedIndexes([0])
        
        # default to sort by filename
        initial_sort = self.classprefs.sort_filenames_if_scheme.split(',')
        if self.url.scheme in initial_sort:
            self.list.SortListItems(1)
    
    def GetSecondarySortValues(self, col, key1, key2, itemDataMap):
        return (itemDataMap[key1].getBasename(), itemDataMap[key2].getBasename())

    def createColumns(self, list):
        list.InsertSizedColumn(0, "Flags", min=30, max=30, greedy=True)
        list.InsertSizedColumn(1, "Filename", min=100)
        list.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
        list.InsertSizedColumn(3, "Date")
        list.InsertSizedColumn(4, "Mode")
        list.InsertSizedColumn(5, "Description", min=100, greedy=True)
        list.InsertSizedColumn(6, "URL", ok_offscreen=True)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        entry = self.getEntryFromIndex(index)
        path = entry.getURL()
        self.dprint("clicked on %d: path=%s" % (index, path))
        self.frame.open(path)

    def getFirstSelectedKey(self):
        """Get the Buffer object of the first selected item in the list."""
        index = self.list.GetFirstSelected()
        if index == -1:
            return None
        key = self.list.GetItem(index, 6).GetText()
        return key

    def setFlag(self, flag):
        """Set the specified flag for all the selected items.
        
        flag: a single character representing the flag to set
        """
        indexes = self.getSelectedIndexes()
        for index in indexes:
            entry = self.getEntryFromIndex(index)
            flags = entry.getFlags()
            dprint("index=%d key=%s" % (index, entry.getURL()))
            if flag not in flags:
                # flags are stored as a sorted string, but there's no direct
                # way to sort a string, so it has to be converted to a list,
                # sorted, and converted back
                tmp = [f for f in flags]
                tmp.append(flag)
                tmp.sort()
                flags = "".join(tmp)
                entry.setFlags(flags)
                self.list.SetStringItem(index, 0, flags)

    def clearFlags(self):
        """Clear all flags for the selected items."""
        indexes = self.getSelectedIndexes()
        for index in indexes:
            entry = self.getEntryFromIndex(index)
            flags = ""
            entry.setFlags(flags)
            self.list.SetStringItem(index, 0, flags)
    
    def execute(self):
        """Operate on all the flags for each of the buffers.
        
        For each buffer item, process the flags to perform the requested action.
        """
        list_count = self.list.GetItemCount()
        for index in range(list_count):
            entry = self.getEntryFromIndex(index)
            url = entry.getURL()
            flags = entry.getFlags()
            dprint("flags %s for %s" % (flags, url))
            if not flags:
                continue
            if 'D' in flags:
                dprint("Not actually deleting %s" % url)
            elif 'M' in flags:
                self.frame.open(url)
            flags = ""
            entry.setFlags(flags)
            self.list.SetStringItem(index, 0, flags)
    
    def getEntryFromIndex(self, index):
        """Return the DiredEntry from the list index.
        
        This is not as simple as it may seem because the list can be reordered,
        changing the meaning of index as it was originally created.  To
        return the correct entry given the list index, an additional layer of
        abstraction is needed: the ItemData field of the list points to the
        real entry.
        """
        orig_index = self.list.GetItemData(index)
        entry = self.origDataMap[orig_index]
        return entry

    def getSelectedEntries(self):
        """Return the currently selected entries.
        
        The entries are returned in the same order as currently displayed in
        the list.
        """
        entries = []
        indexes = self.getSelectedIndexes()
        for index in indexes:
            entry = self.getEntryFromIndex(index)
            entries.append(entry)
        return entries
    
    def resetList(self, msg=None, sort=False):
        """Wrapper around ListMode.resetList because we need to do a few more
        things.
        """
        if self.updating:
            # don't process if we're currently updating the list
            dprint("skipping an update while we're in the middle of an execute")
            return
        self.origDataMap = {}
        
        self.Freeze()
        ListMode.resetList(self, msg)
        
        if sort:
            self.SortListItems()
        self.Thaw()
    
    def getListItems(self):
        return vfs.get_names(self.url)
    
    def getItemRawValues(self, index, name):
        entry = DiredEntry(index, self.url, name)
        self.origDataMap[index] = entry
        return entry
    
    def convertRawValuesToStrings(self, entry):
        return (entry.getFlags(), entry.getBasename(), str(entry.getSize()),
                entry.getCompactDate(), entry.getMode(), entry.getDescription(),
                entry.getURL())
    
    def getPopupActions(self, evt, x, y):
        # id will be -1 if the point is not on any list item; otherwise it is
        # the index of the item.
        id, flags = self.list.HitTest(wx.Point(x, y))
        dprint("id=%d flags=%d" % (id, flags))
        entries = self.getSelectedEntries()
        action_classes = DiredPopupActions(self, entries)
        Publisher().sendMessage('dired.context_menu', action_classes)
        return action_classes
