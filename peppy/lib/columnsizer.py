#-----------------------------------------------------------------------------
# Name:        columnsizer.py
# Purpose:     mixin for list controls to resize columns
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""columnsizer -- a mixin to handle column resizing for list controls

This mixin provides the capabibility to resize columns in a
report-mode list control.  Integer flags are used for each column to
indicate whether the column should be a fixed size or a width
proportional to te length of the largest item in the column.  It also
tries (with only some success) to avoid using a horizontal scrollbar
if at all possible.
"""
import sys

import wx

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt
        return True

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt):
            if self.debuglevel > 0:
                dprint(txt)
            return True

class ColumnSizerMixin(debugmixin):
    """Enhancement to ListCtrl to handle column resizing.

    Resizes columns to a fixed size or based on the size of the
    contents, but constrains the whole width to the visible area of
    the list.  Theoretically there won't be any horizontal scrollbars,
    but this doesnt' yet work on GTK, at least.
    """
    def __init__(self, *args, **kw):
        self._resize_flags = None
        self._resize_dirty = True
        self._last_size = None
        self._resize_flags = {}
        self._allowed_offscreen = sys.maxint
        self.Bind(wx.EVT_SIZE, self.OnSize)
    
    def InsertSizedColumn(self, index, title, *args, **kwargs):
        # min=None, max=None, scale=None, can_scroll=False):
        wx.ListCtrl.InsertColumn(self, index, title, *args)
        
        class ResizeFlags(object):
            def __init__(self, **kwargs):
                if 'min' in kwargs:
                    self.min = kwargs['min']
                else:
                    self.min = None
                if 'max' in kwargs:
                    self.max = kwargs['max']
                else:
                    self.max = None
                if 'scale' in kwargs:
                    self.scale = kwargs['scale']
                else:
                    if self.min is None and self.max is None:
                        self.scale = False
                    else:
                        self.scale = True
        self._resize_flags[index] = ResizeFlags(**kwargs)
        if 'can_scroll' in kwargs and kwargs['can_scroll'] and index < self._allowed_offscreen:
            self._allowed_offscreen = index
        self._resize_dirty = True

    def OnSize(self, evt):
        #dprint(evt.GetSize())
        if self._last_size is None or self._last_size != evt.GetSize():
            self._resize_dirty = True
            self._last_size = evt.GetSize()
            wx.CallAfter(self.resizeColumnsIfDirty)
        evt.Skip()
        
    def resizeColumnsIfDirty(self):
        # OnSize gets called a lot, so only do the column resize one
        # time unless the data has changed
        if self._resize_dirty:
            self._resizeColumns()
        
    def resizeColumns(self):
        if self:
            self._resize_dirty = True
            self._resizeColumns()
        else:
            # This happens because an event might be scheduled between
            # the time the OnSize event is called and the CallAfter
            # gets around to executing the resizeColumns
            assert self.dprint("caught dead object error for %s" % self)
            pass
        
    def _resizeColumns(self):
        if not self._resize_dirty:
            return
        self.Freeze()
            
        flags = self._resize_flags
        autosized_width = 0
        fixed_width = 0
        
        # Resize all columns to their autosizedly determined width
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, wx.LIST_AUTOSIZE)
            flag = flags[col]
            if col < self._allowed_offscreen:
                after = self.GetColumnWidth(col)
                autosized_width += after
        
        # Loop through again and adjust once we know the total widths
        w, h = self.GetClientSizeTuple()
        assert self.dprint("client width = %d, fixed_width = %d" % (w, fixed_width))
        w -= fixed_width
        allowed_offscreen = min(self._allowed_offscreen, self.GetColumnCount())
        for col in range(allowed_offscreen):
            before = self.GetColumnWidth(col)
            resize = before
            
            flag = flags[col]
            if flag.scale:
                resize = (before * w) / autosized_width
                          
            if flag.min and resize < flag.min:
                resize = flag.min
            elif flag.max and resize > flag.max:
                resize = flag.max
                
            assert self.dprint("col %d: before=%d resized=%d" % (col, before, resize))
            if resize != before:
                self.SetColumnWidth(col, resize)
        self.Thaw()
        self._resize_dirty = False


if __name__ == "__main__":
    import sys, random
    
    class TestList(ColumnSizerMixin, wx.ListCtrl):
        def __init__(self, parent):
            wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
            ColumnSizerMixin.__init__(self)

            self.rows = 5
            self.examples = [0, (1,20), (4,10), (4,5), (10,30), (100,200)]

            self.createColumns()
            self.reset()
        
        def createColumns(self):
            self.InsertSizedColumn(0, "Index")
            self.InsertSizedColumn(1, "Filename", min=100, max=200)
            self.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, scale=False)
            self.InsertSizedColumn(3, "Mode", max=100)
            self.InsertSizedColumn(4, "Description", min=100)
            self.InsertSizedColumn(5, "URL", can_scroll=True)

        def reset(self, msg=None):
            # FIXME: Freeze doesn't seem to work -- on windows, this list is built
            # so slowly that you can see columns being resized.
            self.Freeze()
            list_count = self.GetItemCount()
            for index in range(self.rows):
                if index >= list_count:
                    self.InsertStringItem(sys.maxint, str(index))
                else:
                    self.SetStringItem(index, 0, str(index))
                for col in range(1, len(self.examples)):
                    random_range = self.examples[col]
                    letter = chr(col+ord("A"))
                    item = letter*random.randint(*random_range)
                    self.SetStringItem(index, col, item)
            
            if index < list_count:
                for i in range(index, list_count):
                    # always delete the first item because the list gets
                    # shorter by one each time.
                    self.DeleteItem(index)

            self.resizeColumns()
            self.Thaw()


    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Column resizer test')
    frame.CreateStatusBar()
    
    panel = TestList(frame)

    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    
    app.MainLoop()
