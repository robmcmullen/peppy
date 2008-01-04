#-----------------------------------------------------------------------------
# Name:        columnsizer.py
# Purpose:     mixin for list controls to resize columns
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007-2008 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""columnsizer -- a mixin to handle column resizing for list controls

This mixin provides the capabibility to resize columns in a report-mode list
control.  Columns may have fixed or scalable widths, and optionally an initial
group of columns can be constrained to fit in the visible portion of the
window upon resizing or initialization of the list.

Usage
=====

This mixin is used in subclasses of ListCtrl in LC_REPORT mode, as in the
following snippet from a constructor:

class TestList(ColumnSizerMixin, wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)

Columns are added using the special InsertSizedColumn method, not the standard
InsertColumn method of the ListCtrl.  InsertSizedColumn has several keyword
arguments that control how the column is resized; see the docstring for the
method for a full description.  For example,

    def createColumns(self):
        self.InsertSizedColumn(0, "Index")
        self.InsertSizedColumn(1, "Filename", min=100, max=200)
        self.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, scale=False)
        self.InsertSizedColumn(3, "Mode", max="MMM")
        self.InsertSizedColumn(4, "Description", min=100)
        self.InsertSizedColumn(5, "URL", ok_offscreen=True)
        self.InsertSizedColumn(6, "Owner", fixed=50)

will create 6 columns, all autosized to the largest item but with the
additional constraits applied in the following cases:

* Column 1 (Filename) will be clamped to the range between minimum and maximum
pixels.

* Column 2 (Size) will be aligned to the right, has a minimum size, and won't
be greedy about its maximum size when the whole list is scaled.

* Column 3 (Mode) has a maximum allowable size given by the width in pixels of
the string "MMM" in the ListCtrl's current font.

* Column 4 (Description) has a minimum size is pixels

* Column 5 (URL) is allowed to be initially placed offscreen, as it is expected
to be a very wide column.  Note that by allowing this column to be placed
offscreen, subsequent columns would also be allowed offscreen.  Only columns
before an ok_offscreen=True keyword argument are scaled in an attempt to keep
those on screen.

* Column 6 (Owner) is a fixed width of 50 pixels

Once the columns are set up and the list is populated with data, and every time
you add more data and want the column sizes to be recomputed, you must make a
call to ResizeColumns.  This will recalculate and redisplay the columns.


Bugs and to-do items
====================

* the column sizes after a user resize (i.e.  the user uses the mouse, grabs
a border between columns, and resizes a column) are not saved.  ResizeColumn
ignores the user changes and resizes columns based on how they were set up
in InsertSizedColumn.



@author: Rob McMullen
@version: 1.0

Changelog:
    1.0:
        * First public release
"""
import sys

import wx


class ColumnSizerMixin(object):
    """Enhancement to ListCtrl (Report mode only) to handle initial column
    sizing.

    Resizes columns to a size based on the contents, or with a minimum, a
    maximum, or a fixed size.  It is geared to create reasonable column sizes
    upon initial display of the ListCtrl, but is also used in response to
    resize events.
    """
    def __init__(self, *args, **kwargs):
        """Initialized required parameters.
        
        This constructor must be called within the init method of the
        associated ListCtrl class using this mixin in order to set up some
        required parameters.
        
        If the automatic scaling is used in response to user resize events and
        the ListCtrl class also binds the wx.EVT_SIZE event, it will have to
        manually call the mixin's OnSize method, otherwise the mixin will not
        automatically resize the columns in the list.
        
        Keyword arguments recognized:
        
        resize: True/False value indicating if the wx.EVT_SIZE event should be
        caught and the list columns should be resized in response to the user
        resizing the window.  (Default is True)
        """
        self._resize_flags = None
        self._resize_dirty = True
        self._last_size = None
        self._resize_flags = {}
        self._allowed_offscreen = sys.maxint
        if 'resize' in kwargs:
            resize = kwargs['resize']
        else:
            resize = True
        if resize:
            self.Bind(wx.EVT_SIZE, self._onSize)
    
    def InsertSizedColumn(self, index, title, *args, **kwargs):
        """Insert a column in the ListCtrl, used instead of InsertColumn.
        
        Insert a column into the ListCtrl, replacing a call to InsertColumn.
        Don't mix calls to InsertColumn and InsertSizedColumn, as undefined
        things will result.  Once you decide to use the ColumnSizerMixin, only
        use InsertSizedColumn to insert columns.  You can insert a non-sized
        column by specifying the same value for min and max.
        
        All arguments to InsertColumn are accepted to this method, and are
        handled as expected.
        
        Keyword parameters control how the column resizing takes place.  The
        following keyword arguments are accepted:
        
        min: minimum allowable width for the column.  If min is an integer,
        that value is used.  If min is a string, the width in pixels of the
        string in the current font is used as the minimum size.  If min is
        not specified or is None, there is no minimum size and the column can
        be sized down to zero width.
        
        max: maximum allowable width for the column.  As for min, the value for
        max can be an integer or a string or None, but in this case specifies
        the maximum width.  If None, there is no maximum size.
        
        scale: True/False value indicating whether or not the column should
        be scaled in rough proportion to its preferred width if all columns
        were allowed to be their preferred width as compared to the width
        based on attempting to fit as many columns in the list without using
        a horizontal scrollbar.  Basically, if scale is false, the column
        will be greedy and take as much space as it requires to satisfy
        its autosize, min, and max constraints.  Otherwise it can be scaled
        smaller (or larger) as required in an attempt to fit more columns in
        the visible part of list.
        
        ok_offscreen: True/False value indicating if this column and subsequent
        columns are initially allowed to be placed offscreen if the width of
        the columns prior to it have preferred sizes that don't allow this
        column to be placed entirely on screen.
        
        --
        
        Note that if both min and max are None, the column will be sized to
        its width as determined by wx.LIST_AUTOSIZE.  (Unless 'scale' is
        explicitly set for the column, in which case the column will also
        respect the value to scale.
        """
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
                if 'fixed' in kwargs:
                    self.min = self.max = kwargs['fixed']
                    self.scale = False
        self._resize_flags[index] = ResizeFlags(**kwargs)
        if 'ok_offscreen' in kwargs and kwargs['ok_offscreen'] and index < self._allowed_offscreen:
            self._allowed_offscreen = index
        self._resize_dirty = True

    def _onSize(self, evt):
        if self._last_size is None or self._last_size != evt.GetSize():
            self._resize_dirty = True
            self._last_size = evt.GetSize()
            if wx.Platform == '__WXGTK__':
                self.ResizeColumns()
            else:
                wx.CallAfter(self.ResizeColumns)
        evt.Skip()
        
    def ResizeColumns(self):
        """User callable method to compute and display new sizes of all columns.
        
        Use this method to recompute and redisplay the column sizes when, for
        instance, you change the contents of the list.
        """
        if self:
            # Have to check for object existence because an event might be
            # scheduled between the time the OnSize event is called and when
            # CallAfter gets around to executing ResizeColumns
            self._resize_dirty = True
            self._ResizeColumns()
        
    def _ResizeColumns(self):
        """Private method to actually handle the column resizes.
        
        Don't call this from user code, this is an internal method that
        actually does the heavy lifting to resize all the columns.
        """
        if not self._resize_dirty:
            return
        self.Freeze()
        
        # get font to measure text extents
        font = self.GetFont()
        dc = wx.ClientDC(self)
        dc.SetFont(font)

        flags = self._resize_flags
        autosized_width = 0
        
        # Resize all columns to their autosizedly determined width
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, wx.LIST_AUTOSIZE)
            flag = flags[col]
            if col < self._allowed_offscreen:
                after = self.GetColumnWidth(col)
                autosized_width += after
        
        # Loop through again and adjust once we know the total widths
        w, h = self.GetClientSizeTuple()
        for col in range(self.GetColumnCount()):
            before = self.GetColumnWidth(col)
            resize = before
            
            flag = flags[col]
            if col < self._allowed_offscreen and flag.scale:
                resize = (before * w) / autosized_width
            
            # setup min and max values.  The min and max may be specified as
            # a string, which will be converted into pixels here, based on
            # the current font.
            small = flag.min
            if isinstance(small, str):
                small = dc.GetTextExtent(small)[0]
            large = flag.max
            if isinstance(large, str):
                large = dc.GetTextExtent(large)[0]

            if small and resize < small:
                resize = small
            elif large and resize > large:
                resize = large
                
            #print("col %d: before=%s resized=%s" % (col, before, resize))
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

            self.rows = 50
            self.examples = [0, (1,20), (4,10), (4,5), (10,30), (100,200), (5,10)]

            self.createColumns()
            self.reset()
        
        def createColumns(self):
            self.InsertSizedColumn(0, "Index")
            self.InsertSizedColumn(1, "Filename", min=100, max=200)
            self.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, scale=False)
            self.InsertSizedColumn(3, "Mode", max="MMM")
            self.InsertSizedColumn(4, "Description", min=100)
            self.InsertSizedColumn(5, "URL", ok_offscreen=True)
            self.InsertSizedColumn(6, "Owner", fixed=50)

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

            self.ResizeColumns()
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
