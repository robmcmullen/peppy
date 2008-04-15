#-----------------------------------------------------------------------------
# Name:        column_autosize.py
# Purpose:     mixin for list controls to resize columns
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007-2008 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""ColumnAutoSizeMixin -- a mixin to handle column resizing for list controls

This mixin provides the capability to resize columns in a report-mode list
control.  Columns may have fixed or scalable widths, and optionally an initial
group of columns can be constrained to fit in the visible portion of the
window upon resizing or initialization of the list.

Usage
=====

This mixin is used in subclasses of ListCtrl in LC_REPORT mode, as in the
following snippet from a constructor::

    class TestList(ColumnAutoSizeMixin, wx.ListCtrl):
        def __init__(self, parent):
            wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
            ColumnAutoSizeMixin.__init__(self)

Columns are added using the special InsertSizedColumn method, not the standard
InsertColumn method of the ListCtrl.  InsertSizedColumn has several keyword
arguments that control how the column is resized; see the docstring for the
method for a full description.  For example::

        def createColumns(self):
            self.InsertSizedColumn(0, "Index")
            self.InsertSizedColumn(1, "Filename", min=100, max=200)
            self.InsertSizedColumn(2, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
            self.InsertSizedColumn(3, "Mode", max="MMM")
            self.InsertSizedColumn(4, "Description", min=100)
            self.InsertSizedColumn(5, "URL", ok_offscreen=True)
            self.InsertSizedColumn(6, "Owner", fixed=50)

will create 6 columns, all autosized to the largest item but with the
additional constraints applied in the following cases:

Column 1 (Filename) will be clamped to the range between minimum and maximum
pixels.

Column 2 (Size) will be aligned to the right, has a minimum size, and will
be greedy and attempt to maintain its preferred size when the whole list is
scaled.

Column 3 (Mode) has a maximum allowable size given by the width in pixels of
the string "MMM" in the ListCtrl's current font.

Column 4 (Description) has a minimum size is pixels

Column 5 (URL) is allowed to be initially placed offscreen, as it is expected
to be a very wide column.  Note that by allowing this column to be placed
offscreen, subsequent columns would also be allowed offscreen.  Only columns
before an ok_offscreen=True keyword argument are scaled in an attempt to keep
those on screen.

Column 6 (Owner) is a fixed width of 50 pixels

Once the columns are set up and the list is populated with data, and every time
you add more data and want the column sizes to be recomputed, you must make a
call to ResizeColumns.  This will recalculate and redisplay the columns.


Bugs and to-do items
====================

The column sizes after a user resize (i.e.  the user uses the mouse, grabs a
border between columns, and resizes a column) are not saved.  ResizeColumn
ignores the user changes and resizes columns based on how they were set up
in InsertSizedColumn.



@author: Rob McMullen
@version: 1.5

Changelog::
    1.5:
        - windows doesn't properly resize column zero -- it's too small.  So,
          a small fudge factor is added to column zero's calculated width on
          MSW only
    1.4:
        - use column header width as column size if there are no items in the
          list
    1.3:
        - changed autosizing to expand last column to width of the containing
          window if the whole list is smaller than the window size
    1.2:
        - added 'expand' keyword
    1.1:
        - renamed to ColumnAutoSizeMixin
        - changed keyword argument 'scale' to 'greedy'
        - implemented new sizing algorithm
    1.0:
        - First public release
"""
import sys

import wx


class ColumnAutoSizeMixin(object):
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
        things will result.  Once you decide to use the ColumnAutoSizeMixin, only
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
        
        greedy: True/False value indicating whether or not the column should
        be scaled in rough proportion to its preferred width if all columns
        were allowed to be their preferred width as compared to the width
        based on attempting to fit as many columns in the list without using a
        horizontal scrollbar.  To restate: if True, the column will be greedy
        and take as much space as it requires to satisfy its autosize, min,
        and max constraints.  Otherwise it can be scaled smaller (or larger)
        as required in an attempt to fit more columns in the visible part of
        list.  (Default is False)
        
        expand: True/False indicating if the column should be expanded to fill
        available width if there is some empty space after all columns are at
        their preferred sizes.  This has no effect when the preferred sizes
        of all columns is larger than the available width, and is only used if
        you don't want empty space in your list.
        
        ok_offscreen: True/False value indicating if this column and subsequent
        columns are initially allowed to be placed offscreen if the width of
        the columns prior to it have preferred sizes that don't allow this
        column to be placed entirely on screen.  (Default is False)
        
        --
        
        Note that if both min and max are None, the column will be sized to
        its width as determined by wx.LIST_AUTOSIZE.  (Unless 'greedy' is
        explicitly set for the column, in which case the column will also
        respect the value to greedy.
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
                if 'greedy' in kwargs:
                    self.greedy = kwargs['greedy']
                else:
                    if self.min is None and self.max is None:
                        self.greedy = True
                    else:
                        self.greedy = False
                if 'expand' in kwargs:
                    self.expand = kwargs['expand']
                else:
                    self.expand = False
                if 'fixed' in kwargs:
                    self.min = self.max = kwargs['fixed']
                    self.greedy = True
        self._resize_flags[index] = ResizeFlags(**kwargs)
        if 'ok_offscreen' in kwargs and kwargs['ok_offscreen'] and index < self._allowed_offscreen:
            self._allowed_offscreen = index
        self._resize_dirty = True
        
        # Windows seems to need extra padding on column zero
        if wx.Platform == "__WXMSW__":
            self._extra_col0_padding = 4
        else:
            self._extra_col0_padding = 0

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
        
        allowed_offscreen = min(self._allowed_offscreen, self.GetColumnCount())
        
        # get font to measure text extents
        font = self.GetFont()
        dc = wx.ClientDC(self)
        dc.SetFont(font)

        flags = self._resize_flags
        
        usable_width = self.GetClientSize().width
        # We're showing the vertical scrollbar -> allow for scrollbar width
        # NOTE: on GTK, the scrollbar is included in the client size, but on
        # Windows it is not included
        if wx.Platform != '__WXMSW__':
            if self.GetItemCount() > self.GetCountPerPage():
                usable_width -= wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        remaining_width = usable_width - self._extra_col0_padding
        
        # pass 1: get preferred sizes for all columns
        before = {}
        newsize = {}
        
        # If there are no items in the list, use the header of the column as
        # the default width to provide some reasonable values.
        if self.GetItemCount() == 0:
            resize_type = wx.LIST_AUTOSIZE_USEHEADER
        else:
            resize_type = wx.LIST_AUTOSIZE
        
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, resize_type)
            before[col] = self.GetColumnWidth(col)
            resize = before[col]
            
            flag = flags[col]
            
            # setup min and max values.  The min and max may be specified as
            # a string, which will be converted into pixels here, based on
            # the current font.
            if isinstance(flag.min, str):
                flag.min = dc.GetTextExtent(flag.min)[0]
            if isinstance(flag.max, str):
                flag.max = dc.GetTextExtent(flag.max)[0]

            if flag.min is not None and resize < flag.min:
                resize = flag.min
            elif flag.max is not None and resize > flag.max:
                resize = flag.max
            newsize[col] = resize

            if col < allowed_offscreen and flag.greedy:
                remaining_width -= resize
            #print("pass1: col %d: before=%d newsize=%d remaining=%d" % (col, before[col], newsize[col], remaining_width))
            

        # pass 2: resize remaining columns
        desired_width = 0
        for col in range(allowed_offscreen):
            flag = flags[col]
            if not flag.greedy:
                resize = (newsize[col] * usable_width) / remaining_width
            
                if flag.min is not None and resize < flag.min:
                    resize = flag.min
                elif flag.max is not None and resize > flag.max:
                    resize = flag.max
                if resize is not None:
                    newsize[col] = resize
                desired_width += newsize[col]
            #print("pass2: col %d: before=%d newsize=%d desired=%d" % (col, before[col], newsize[col], desired_width))
        #print("desired=%d remaining=%d" % (desired_width, remaining_width))
        
        # pass 3: scale columns up or down if necessary
        if desired_width > remaining_width:
            pass3_width = 0
            for col in range(allowed_offscreen):
                flag = flags[col]
                if not flag.greedy:
                    resize = (newsize[col] * remaining_width) / desired_width
                
                    if flag.min is not None and resize < flag.min:
                        resize = flag.min
                    elif flag.max is not None and resize > flag.max:
                        resize = flag.max
                    if resize is not None:
                        newsize[col] = resize
                    pass3_width += newsize[col]
                #print("pass3: col %d: before=%d newsize=%d pass3_width=%d" % (col, before[col], newsize[col], pass3_width))
        else:
            # requested size of all columns is smaller than the window.  Any
            # 'expand' columns will now expand to fill
            pass3_width = 0
            expandcount = 0
            for col in range(allowed_offscreen):
                flag = flags[col]
                if flag.expand:
                    expandcount += 1
            if expandcount == 0:
                # no columns are flagged for expansion, so expand the last one
                col = self.GetColumnCount() - 1
                newsize[col] += remaining_width
                #print("Resizing last column %d = %d" % (col, newsize[col]))
            else:
                for col in range(allowed_offscreen):
                    flag = flags[col]
                    if flag.expand:
                        distribwidth = (remaining_width - desired_width) / expandcount
                        resize = newsize[col] + distribwidth
                    
                        if flag.max is not None and resize > flag.max:
                            resize = flag.max
                        newsize[col] = resize
                        expandcount -= 1
                        #print("pass3: col %d: before=%d newsize=%d distribwidth=%d" % (col, before[col], newsize[col], distribwidth))

        # pass 4: set column widths
        for col in range(self.GetColumnCount()):
            width = newsize[col]
            if col == 0:
                width += self._extra_col0_padding
            #print("col %d: before=%s resized=%s" % (col, before[col], width))
            if width != before[col]:
                self.SetColumnWidth(col, width)
        self.Thaw()
        self._resize_dirty = False


if __name__ == "__main__":
    import sys, random
    
    class TestList1(ColumnAutoSizeMixin, wx.ListCtrl):
        def __init__(self, parent):
            wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
            ColumnAutoSizeMixin.__init__(self)

            self.rows = 50
            self.examples = [0, (1,20), (1,20), (4,10), (4,5), (10,30), (100,200), (5,10)]

            self.createColumns()
            self.reset()
        
        def createColumns(self):
            self.InsertSizedColumn(0, "Index")
            self.InsertSizedColumn(1, "Num")
            self.InsertSizedColumn(2, "Filename", min=75, max=200)
            self.InsertSizedColumn(3, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
            self.InsertSizedColumn(4, "Mode", min="M", max="MMM")
            self.InsertSizedColumn(5, "Description", min=75)
            self.InsertSizedColumn(6, "URL", ok_offscreen=True)
            self.InsertSizedColumn(7, "Owner", fixed=50)

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
                self.SetStringItem(index, 1, str(index))
                for col in range(2, self.GetColumnCount()):
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

    class TestList2(TestList1):
        def createColumns(self):
            self.InsertSizedColumn(0, "Index")
            self.InsertSizedColumn(1, "Num")
            self.InsertSizedColumn(2, "Filename", min=75, max=200)
            self.InsertSizedColumn(3, "Size", wx.LIST_FORMAT_RIGHT, min=30, greedy=True)
            self.InsertSizedColumn(4, "Mode", min="M", max="MMM")
            self.InsertSizedColumn(5, "Description", min=75)

    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Column resizer test')
    frame.CreateStatusBar()
    
    list1 = TestList1(frame)
    list2 = TestList2(frame)
    
    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(frame, -1, "List with stuff allowed offscreen:"), 0, wx.EXPAND)
    sizer.Add(list1, 1, wx.EXPAND)
    sizer.Add(wx.StaticText(frame, -1, ""), 0, wx.EXPAND)
    sizer.Add(wx.StaticText(frame, -1, "List with nothing allowed offscreen:"), 0, wx.EXPAND)
    sizer.Add(list2, 1, wx.EXPAND)
  
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    
    app.MainLoop()
