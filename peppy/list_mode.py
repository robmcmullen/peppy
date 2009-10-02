# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""List Mode

Abstract major mode used to represent data as a sortable list.
"""

import os

import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin

from peppy.lib.column_autosize import *

from peppy.major import *
from peppy.buffers import *
from peppy.stcinterface import *
from peppy.debug import *


class ListModeActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'moveSelected')
    
    def actionWorksWithCurrentFocus(self):
        # On OS X, the control that takes keyboard focus isn't the same object
        # as the list, so we have to go up the widget hierarchy to check
        focus = self.mode.FindFocus()
        return focus == self.mode.list or focus.GetParent() == self.mode.list


class SortableListCtrl(wx.ListCtrl, ColumnAutoSizeMixin, ColumnSorterMixin):
    def __init__(self, mode):
        self.mode = mode
        wx.ListCtrl.__init__(self, mode, style=wx.LC_REPORT)
        ColumnAutoSizeMixin.__init__(self)

        self.mode.createColumns(self)
        self.itemDataMap = {}
        ColumnSorterMixin.__init__(self, self.GetColumnCount())
        # Assign icons for up and down arrows for column sorter
        getIconStorage().assignList(self)
    
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self
    
    def GetSortImages(self):
        down = getIconStorage("icons/bullet_arrow_down.png")
        up = getIconStorage("icons/bullet_arrow_up.png")
        return (down, up)

    def GetSecondarySortValues(self, col, key1, key2):
        return self.mode.GetSecondarySortValues(col, key1, key2, self.itemDataMap)


class ListMode(wx.Panel, MajorMode):
    """Abstract major mode used to represent data as a sortable list.
    
    Subclasses must override at least the L{createColumns}, L{getListItems},
    and L{getItemValues} methods in order to instantiate this class.
    """
    keyword = "List"
    icon = None
    allow_threaded_loading = False
    
    stc_class = None

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        
        wx.Panel.__init__(self, parent, -1)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.createInfoHeader(sizer)
        
        self.list = SortableListCtrl(self)
        sizer.Add(self.list, 1, wx.EXPAND)
        
        self.createInfoFooter(sizer)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()
        
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        
        self.updating = False
        self.resetList()
    
    def createColumns(self, list):
        """Columns must be created by the subclass"""
        raise NotImplementedError

    def createInfoHeader(self, sizer):
        """Hook to create controls before the list control.
        
        Any controls added here should be also added to the BoxSizer that is
        passed in to this method.
        """
        pass
    
    def createInfoFooter(self, sizer):
        """Hook to create controls after the list control.
        
        Any controls added here should be also added to the BoxSizer that is
        passed in to this method.
        """
        pass
    
    def getKeyboardCapableControls(self):
        return [self.list]
    
    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        dprint("clicked on %d" % index)

    def GetSecondarySortValues(self, col, key1, key2, itemDataMap):
        return (itemDataMap[key1][1], itemDataMap[key2][1])

    def setSelectedIndexes(self, indexes):
        """Highlight the rows contained in the indexes array"""
        
        list_count = self.list.GetItemCount()
        for index in range(list_count):
            if index in indexes:
                self.list.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            else:
                self.list.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

    def getSelectedIndexes(self):
        """Return an array of indexes that are currently selected."""
        
        indexes = []
        index = self.list.GetFirstSelected()
        while index != -1:
            assert self.dprint("index %d" % (index, ))
            indexes.append(index)
            index = self.list.GetNextSelected(index)
        return indexes
    
    def moveSelected(self, offset):
        """Move the selection up or down.
        
        If offset < 0, move the selection to the item before the first
        currently selected item, and if offset > 0 move the selection to after
        the last item that is currently selected.
        """
        indexes = self.getSelectedIndexes()
        if not indexes:
            return
        index = None
        if offset < 0:
            index = indexes[0] + offset
            if index < 0:
                index = 0
        elif offset > 0:
            index = indexes[-1] + offset
            if index >= self.list.GetItemCount():
                index = self.list.GetItemCount() - 1
        if index is not None:
            self.setSelectedIndexes([index])
            self.list.EnsureVisible(index)
    
    def resetList(self, msg=None):
        """Reset the list.
        
        No optimization here, just rebuild the entire list.
        """
        if self.updating:
            # don't process if we're currently updating the list
            dprint("skipping an update while we're in the middle of an execute")
            return
        
        # FIXME: Freeze doesn't seem to work -- on windows, this list is built
        # so slowly that you can see columns being resized.
        self.list.Freeze()
        list_count = self.list.GetItemCount()
        index = 0
        cumulative = 0
        cache = []
        show = -1
        self.list.itemDataMap = {}
        for item in self.getListItems():
            values = self.getItemRawValues(index, item)
            self.list.itemDataMap[index] = values
            
            if isinstance(values, list):
                # Make a copy of the list so the user can change it in place
                values = values[:]
            values = self.convertRawValuesToStrings(values)
                
            if index >= list_count:
                self.list.InsertStringItem(sys.maxint, values[0])
            else:
                self.list.SetStringItem(index, 0, values[0])
            col = 1
            for value in values[1:]:
                self.list.SetStringItem(index, col, value)
                col += 1
            self.list.SetItemData(index, index)
            index += 1
        
        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.list.DeleteItem(index)
        if show >= 0:
            self.list.EnsureVisible(show)

        self.list.ResizeColumns()
        self.list.Thaw()
        
        self.resetListPostHook()
    
    def resetListPostHook(self):
        """Hook for processing after the list is reset
        """
        pass
    
    def getListItems(self):
        """Subclasses must return iterator or list containing the list items
        
        """
        raise NotImplementedError
    
    def getItemRawValues(self, index, item):
        """For the specified item, return a list containing the raw object
        values that correspond to each column in the ListCtrl.
        
        There should be the same number of entries in the returned list as are
        columns in the ListCtrl.
        """
        raise NotImplementedError
    
    def convertRawValuesToStrings(self, raw_values):
        """If the values to be displayed in the ListCtrl need special
        conversion from string, a new list should be returned here.
        
        Doing nothing causes the default unicode string conversion to be used.
        """
        return [unicode(r) for r in raw_values]
    
    def isPrintingSupported(self):
        return True
    
    def getHtmlForPrinting(self):
        list_count = self.list.GetItemCount()
        html = u"<P>%s\n" % unicode(self.buffer.url)
        html += u"<P><table>\n" + self.getHtmlHeaderColumn()
        column_order = self.getValidColumnsForPrinting()
        for index in range(list_count):
            entry = self.getEntryFromIndex(index)
            columns = self.convertRawValuesToStrings(entry)
            items = []
            for i in column_order:
                items.append(columns[i])
            line = u"</td><td>".join(items)
            html += u"<tr><td>" + line + u"</td></tr>\n"
        html += u"</table>"
        return html
    
    def getValidColumnsForPrinting(self):
        """Returns a list of columns that should be included in the printout
        
        """
        return range(self.list.GetColumnCount())
    
    def getHtmlHeaderColumn(self):
        """Returns an HTML table header that contains column headers for each
        of the columns
        """
        items = []
        for i in self.getValidColumnsForPrinting():
            col = self.list.GetColumn(i)
            items.append(col.GetText())
        return u"<tr><th>" + u"</th><th>".join(items) + u"</th></tr>\n"
