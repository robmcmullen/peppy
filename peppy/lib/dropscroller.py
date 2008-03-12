#-----------------------------------------------------------------------------
# Name:        dropscroller.py
# Purpose:     auto scrolling for a list that's being used as a drop target
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxPython
#-----------------------------------------------------------------------------
"""
Automatic scrolling mixin for a list control, including an indicator
showing where the items will be dropped.

It would be nice to have somethin similar for a tree control as well,
but I haven't tackled that yet.
"""
import sys, pickle

import wx

class ListDropScrollerMixin(object):
    """Automatic scrolling for ListCtrls for use when using drag and drop.

    This mixin is used to automatically scroll a list control when
    approaching the top or bottom edge of a list.  Currently, this
    only works for lists in report mode.

    Add this as a mixin in your list, and then call processListScroll
    in your DropTarget's OnDragOver method.  When the drop ends, call
    finishListScroll to clean up the resources (i.e. the wx.Timer)
    that the dropscroller uses and make sure that the insertion
    indicator is erased.

    The parameter interval is the delay time in milliseconds between
    list scroll steps.

    If indicator_width is negative, then the indicator will be the
    width of the list.  If positive, the width will be that number of
    pixels, and zero means to display no indicator.
    """
    def __init__(self, interval=200, width=-1):
        """Don't forget to call this mixin's init method in your List.

        Interval is in milliseconds.
        """
        self._auto_scroll_timer = None
        self._auto_scroll_interval = interval
        self._auto_scroll = 0
        self._auto_scroll_save_y = -1
        self._auto_scroll_save_width = width
        self.Bind(wx.EVT_TIMER, self.OnAutoScrollTimer)
        
    def _startAutoScrollTimer(self, direction = 0):
        """Set the direction of the next scroll, and start the
        interval timer if it's not already running.
        """
        if self._auto_scroll_timer == None:
            self._auto_scroll_timer = wx.Timer(self, wx.TIMER_ONE_SHOT)
            self._auto_scroll_timer.Start(self._auto_scroll_interval)
        self._auto_scroll = direction

    def _stopAutoScrollTimer(self):
        """Clean up the timer resources.
        """
        self._auto_scroll_timer = None
        self._auto_scroll = 0

    def _getAutoScrollDirection(self, index):
        """Determine the scroll step direction that the list should
        move, based on the index reported by HitTest.
        """
        first_displayed = self.GetTopItem()

        if first_displayed == index:
            # If the mouse is over the first index...
            if index > 0:
                # scroll the list up unless...
                return -1
            else:
                # we're already at the top.
                return 0
        elif index >= first_displayed + self.GetCountPerPage() - 1:
            # If the mouse is over the last visible item, but we're
            # not at the last physical item, scroll down.
            return 1
        # we're somewhere in the middle of the list.  Don't scroll
        return 0

    def getDropIndex(self, x, y, index=None, flags=None):
        """Find the index to insert the new item, which could be
        before or after the index passed in.
        """
        if index is None:
            index, flags = self.HitTest((x, y))

        if index == wx.NOT_FOUND: # not clicked on an item
            if (flags & (wx.LIST_HITTEST_NOWHERE|wx.LIST_HITTEST_ABOVE|wx.LIST_HITTEST_BELOW)): # empty list or below last item
                index = sys.maxint # append to end of list
                #print "getDropIndex: append to end of list: index=%d" % index
            elif (self.GetItemCount() > 0):
                if y <= self.GetItemRect(0).y: # clicked just above first item
                    index = 0 # append to top of list
                    #print "getDropIndex: before first item: index=%d, y=%d, rect.y=%d" % (index, y, self.GetItemRect(0).y)
                else:
                    index = self.GetItemCount() + 1 # append to end of list
                    #print "getDropIndex: after last item: index=%d" % index
        else: # clicked on an item
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)
            #print "getDropIndex: landed on %d, y=%d, rect=%s" % (index, y, rect)

            # NOTE: On all platforms, the y coordinate used by HitTest
            # is relative to the scrolled window.  There are platform
            # differences, however, because on GTK the top of the
            # vertical scrollbar stops below the header, while on MSW
            # the top of the vertical scrollbar is equal to the top of
            # the header.  The result is the y used in HitTest and the
            # y returned by GetItemRect are offset by a certain amount
            # on GTK.  The HitTest's y=0 in GTK corresponds to the top
            # of the first item, while y=0 on MSW is in the header.
            
            # From Robin Dunn: use GetMainWindow on the list to find
            # the actual window on which to draw
            if self != self.GetMainWindow():
                y += self.GetMainWindow().GetPositionTuple()[1]

            # If the user is dropping into the lower half of the rect,
            # we want to insert _after_ this item.
            if y >= (rect.y + rect.height/2):
                index = index + 1

        return index

    def processListScroll(self, x, y):
        """Main handler: call this with the x and y coordinates of the
        mouse cursor as determined from the OnDragOver callback.

        This method will determine which direction the list should be
        scrolled, and start the interval timer if necessary.
        """
        index, flags = self.HitTest((x, y))

        direction = self._getAutoScrollDirection(index)
        if direction == 0:
            self._stopAutoScrollTimer()
        else:
            self._startAutoScrollTimer(direction)
            
        drop_index = self.getDropIndex(x, y, index=index, flags=flags)
        count = self.GetItemCount()
        if count == 0:
            # don't show any lines if we don't have any items in the list
            return
        elif drop_index >= count:
            index = min(count, drop_index)
            rect = self.GetItemRect(index - 1)
            y = rect.y + rect.height + 1
        else:
            rect = self.GetItemRect(drop_index)
            y = rect.y

        # From Robin Dunn: on GTK & MAC the list is implemented as
        # a subwindow, so have to use GetMainWindow on the list to
        # find the actual window on which to draw
        if self != self.GetMainWindow():
            y -= self.GetMainWindow().GetPositionTuple()[1]

        if self._auto_scroll_save_y == -1 or self._auto_scroll_save_y != y:
            #print "main window=%s, self=%s, pos=%s" % (self, self.GetMainWindow(), self.GetMainWindow().GetPositionTuple())
            if self._auto_scroll_save_width < 0:
                self._auto_scroll_save_width = rect.width
            dc = self._getIndicatorDC()
            self._eraseIndicator(dc)
            dc.DrawLine(0, y, self._auto_scroll_save_width, y)
            self._auto_scroll_save_y = y

    def finishListScroll(self):
        """Clean up timer resource and erase indicator.
        """
        self._stopAutoScrollTimer()
        self._eraseIndicator()
        
    def OnAutoScrollTimer(self, evt):
        """Timer event handler to scroll the list in the requested
        direction.
        """
        #print "_auto_scroll = %d, timer = %s" % (self._auto_scroll, self._auto_scroll_timer is not None)
        if self._auto_scroll == 0:
            # clean up timer resource
            self._auto_scroll_timer = None
        else:
            dc = self._getIndicatorDC()
            self._eraseIndicator(dc)
            if self._auto_scroll < 0:
                self.EnsureVisible(self.GetTopItem() + self._auto_scroll)
                self._auto_scroll_timer.Start()
            else:
                self.EnsureVisible(self.GetTopItem() + self.GetCountPerPage())
                self._auto_scroll_timer.Start()
        evt.Skip()

    def _getIndicatorDC(self):
        dc = wx.ClientDC(self.GetMainWindow())
        dc.SetPen(wx.Pen(wx.WHITE, 3))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetLogicalFunction(wx.XOR)
        return dc

    def _eraseIndicator(self, dc=None):
        if dc is None:
            dc = self._getIndicatorDC()
        if self._auto_scroll_save_y >= 0:
            # erase the old line
            dc.DrawLine(0, self._auto_scroll_save_y,
                        self._auto_scroll_save_width, self._auto_scroll_save_y)
        self._auto_scroll_save_y = -1


class PickledDataObject(wx.CustomDataObject):
    """Sample custom data object storing indexes of the selected items"""
    def __init__(self):
        wx.CustomDataObject.__init__(self, "Pickled")

class PickledDropTarget(wx.PyDropTarget):
    """Custom drop target modified from the wxPython demo."""

    def __init__(self, window):
        wx.PyDropTarget.__init__(self)
        self.dv = window

        # specify the type of data we will accept
        self.data = PickledDataObject()
        self.SetDataObject(self.data)

    def cleanup(self):
        self.dv.finishListScroll()

    # some virtual methods that track the progress of the drag
    def OnEnter(self, x, y, d):
        print "OnEnter: %d, %d, %d\n" % (x, y, d)
        return d

    def OnLeave(self):
        print "OnLeave\n"
        self.cleanup()

    def OnDrop(self, x, y):
        print "OnDrop: %d %d\n" % (x, y)
        self.cleanup()
        return True

    def OnDragOver(self, x, y, d):
        top = self.dv.GetTopItem()
        print "OnDragOver: %d, %d, %d, top=%s" % (x, y, d, top)

        self.dv.processListScroll(x, y)

        # The value returned here tells the source what kind of visual
        # feedback to give.  For example, if wxDragCopy is returned then
        # only the copy cursor will be shown, even if the source allows
        # moves.  You can use the passed in (x,y) to determine what kind
        # of feedback to give.  In this case we return the suggested value
        # which is based on whether the Ctrl key is pressed.
        return d

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        print "OnData: %d, %d, %d\n" % (x, y, d)

        self.cleanup()
        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list of lines and give it to the viewer
            items = pickle.loads(self.data.GetData())
            self.dv.AddDroppedItems(x, y, items)

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d


if __name__ == '__main__':
    class TestList(wx.ListCtrl, ListDropScrollerMixin):
        """Simple list control that provides a drop target and uses
        the new mixin for automatic scrolling.
        """
        
        def __init__(self, parent, name, count=100):
            wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)

            # The mixin needs to be initialized
            ListDropScrollerMixin.__init__(self, interval=200)
            
            self.dropTarget=PickledDropTarget(self)
            self.SetDropTarget(self.dropTarget)

            self.create(name, count)
            
            self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)

        def create(self, name, count):
            """Set up some test data."""
            
            self.InsertColumn(0, "#")
            self.InsertColumn(1, "Title")
            for i in range(count):
                self.InsertStringItem(sys.maxint, str(i))
                self.SetStringItem(i, 1, "%s-%d" % (name, i))

        def OnStartDrag(self, evt):
            index = evt.GetIndex()
            print "beginning drag of item %d" % index

            # Create the data object containing all currently selected
            # items
            data = PickledDataObject()
            items = []
            index = self.GetFirstSelected()
            while index != -1:
                items.append((self.GetItem(index, 0).GetText(),
                              self.GetItem(index, 1).GetText()))
                index = self.GetNextSelected(index)
            data.SetData(pickle.dumps(items,-1))

            # And finally, create the drop source and begin the drag
            # and drop opperation
            dropSource = wx.DropSource(self)
            dropSource.SetData(data)
            print "Begining DragDrop\n"
            result = dropSource.DoDragDrop(wx.Drag_AllowMove)
            print "DragDrop completed: %d\n" % result

        def AddDroppedItems(self, x, y, items):
            index = self.getDropIndex(x, y)
            print "At (%d,%d), index=%d, adding %s" % (x, y, index, items)

            list_count = self.GetItemCount()
            for item in items:
                if index == -1:
                    index = 0
                index = self.InsertStringItem(index, item[0])
                self.SetStringItem(index, 1, item[1])
                index += 1
        
        def clear(self, evt):
            self.DeleteAllItems()

    class ListPanel(wx.SplitterWindow):
        def __init__(self, parent):
            wx.SplitterWindow.__init__(self, parent)

            self.list1 = TestList(self, "left", 100)
            self.list2 = TestList(self, "right", 10)
            self.SplitVertically(self.list1, self.list2)
            self.Layout()

    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='List Drag Test', size=(400,500))
    frame.CreateStatusBar()
    
    panel = ListPanel(frame)
    label = wx.StaticText(frame, -1, "Drag items from a list to either list.\nThe lists will scroll when the cursor\nis near the first and last visible items")

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
    sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 5)
    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    btn1 = wx.Button(frame, -1, "Clear List 1")
    btn1.Bind(wx.EVT_BUTTON, panel.list1.clear)
    btn2 = wx.Button(frame, -1, "Clear List 2")
    btn2.Bind(wx.EVT_BUTTON, panel.list2.clear)
    hsizer.Add(btn1, 1, wx.EXPAND)
    hsizer.Add(btn2, 1, wx.EXPAND)
    sizer.Add(hsizer, 0, wx.EXPAND)
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    
    app.MainLoop()
