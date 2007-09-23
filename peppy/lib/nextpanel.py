#-----------------------------------------------------------------------------
# Name:        nextpanel.py
# Purpose:     multi-pane list like the NeXT file manager
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Multi-pane list similar to the NeXT file-manager

This widget is designed for hierarchical display of data, similar to
what a tree could provide but allows more information to be displayed
at one time (at the cost of more screen real estate).

The NeXTPanel is a set of columns that adds more columns as you delve
deeper into the hierarchy.  The initial view is just a single column
displaying the root of the hierarchy.  Selecting one or more items
causes another column to be displayed to the right of the column
displaying the children of the selected items.  More columns can be
added by selecting items in the new list.

@author: Rob McMullen
@version: 0.1

Changelog:
    0.1:
        * initial release
"""

import os, sys, os.path, glob
from cStringIO import StringIO

import wx
import wx.lib.newevent
import wx.lib.splitter
import wx.lib.scrolledpanel

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt):
            if self.debuglevel > 0:
                dprint(txt)


#(NeXTPanelEvent, EVT_NEXTPANEL) = wx.lib.newevent.NewEvent()

# FIXME: the newevent.NewEvent() style didn't work; had to grab the
# PyCommandEvent pattern from the demo.
myEVT_NEXTPANEL = wx.NewEventType()
EVT_NEXTPANEL = wx.PyEventBinder(myEVT_NEXTPANEL, 1)

class NeXTPanelEvent(wx.PyCommandEvent):
    def __init__(self):
        wx.PyCommandEvent.__init__(self, myEVT_NEXTPANEL, id=-1)
        self.list = None
        self.listnum = None



class NeXTList(wx.ListBox):
    def __init__(self, parent, *args, **kw):
        wx.ListBox.__init__(self, parent, *args, **kw)
        
    def DeleteAllItems(self):
        for index in range(self.GetCount()):
            self.Deselect(index)
        self.Clear()

    def InsertStringItem(self, idx, txt):
        if idx == sys.maxint:
            self.Append(txt)
        else:
            self.Insert(txt, idx)

    def ReplaceItems(self, names):
        count = self.GetCount()
        index = 0
        for name in names:
            # NOTE: have to deselect items before changing, otherwise
            # a select event is emitted!
            #dprint("Before Deselect %d %s" % (index, name))
            #dprint("After Deselect %d %s" % (index, name))
            if index >= count:
                self.Append(name)
            else:
                self.Deselect(index)
                self.SetString(index, name)
            #dprint("After set %d %s" % (index, name))
            index += 1
        while index < count:
            # NOTE: also have to deselect items before deleting,
            # otherwise a select event is emitted!
            #dprint("Before delete %d %s" % (count, name))
            self.Deselect(index)
            self.Delete(index)
            #dprint("After delete %d %s" % (count, name))
            count -= 1
        

    def GetEffectiveMinSize(self):
        # FIXME: the real GetEffectiveSize doesn't seem to include the
        # width of the scrollbars, which throws off the scrolled
        # window calculations
        sz = self.GetSize()

        # Make the heigth smaller, because we don't want to scroll
        # vertically
        sz.height = 10
        #dprint(sz)
        return sz

class HackedScrolledPanel(wx.lib.scrolledpanel.ScrolledPanel):
    """Hacked ScrolledPanel to change the smart focus.

    The read ScrolledPanel doesn't set the focus to the correct list,
    probably because the MultiSplitterWindow isn't a real container.
    Apparently there's an undocumented wxControlContainer class that
    handles focus for real container widgets
    """
    def OnChildFocus(self, evt):
        """Override to prevent auto scrolling.

        In the original OnChildFocus if the child window that gets the
        focus is not visible, this handler will try to scroll enough
        to see it.  However, when the child is a MultiSplitterWindow,
        it always scrolls to the origin of the MultiSplitterWindow,
        regardless of which child inthe splitter has the focus.  So,
        we have to override it here to prevent auto scrolling.
        """
        evt.Skip()
        child = evt.GetWindow()
        # print "child window: %s" % child
    

class NeXTPanel(HackedScrolledPanel, debugmixin):
    """NeXT file manager-like multi-list panel.

    Displays a group of independent column lists, where the number of
    columns can grow or shrink.
    """
    debuglevel = 0
    
    def __init__(self, parent):
        HackedScrolledPanel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        self.splitter = wx.lib.splitter.MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.sizer.Add(self.splitter, 1, wx.EXPAND)

        self.viewing = -1

        c = wx.Panel(self, size=(1,1))
        self.splitter.AppendWindow(c, 1)
        self.Layout()
        self.SetAutoLayout(1)
        self.SetupScrolling()

    def resetSize(self):
        self.dprint(self.splitter.DoGetBestSize())
        self.SetVirtualSize(self.splitter.DoGetBestSize())
        self.ensureVisible(self.viewing)

    def ensureVisible(self, idx):
        self.dprint("Scrolling %d into view" % idx)
        total = 0
        sashes = []
        for i in range(self.GetNumLists()):
            total += self.splitter.GetSashPosition(i)
            sashes.append(total)
        self.dprint("sashes = %s" % sashes)
        
        if idx >= self.GetNumLists():
            idx = self.GetNumLists() - 1
        if idx > 0:
            first = sashes[idx - 1]
        else:
            first = 0
        last = sashes[idx]

        # code ripped from the wxPython demo
        sppu_x, sppu_y = self.GetScrollPixelsPerUnit()
        vs_x, vs_y = self.GetViewStart()
        clntsz = self.GetClientSize()
        new_vs_x = -1
        self.dprint("first=%d last=%d, vs=%d sppu=%d cl=%d" % (first, last, vs_x, sppu_x, clntsz.width))

        # is it before the left edge?
        if first < 0 and sppu_x > 0:
            new_vs_x = vs_x + (first / sppu_x)

        # is it past the right edge ?
        if last > clntsz.width and sppu_x > 0:
            diff = (last - clntsz.width) / sppu_x
            if first - diff * sppu_x > 0:
                new_vs_x = vs_x + diff + 1
            else:
                new_vs_x = vs_x + (first / sppu_x)

        if new_vs_x != -1:
            self.Scroll(new_vs_x, vs_y)
        

    def SetFont(self, font):
        """Overridden function to set font of all sub lists."""
        self.dprint("font=%s" % font)
        HackedScrolledPanel.SetFont(self, font)
        index = 0
        while index < self.GetNumLists():
            c = self.GetList(index)
            c.SetFont(font)
            index += 1

    def GetNumLists(self):
        return len(self.splitter._windows) - 1

    def GetList(self, index):
        if index < self.GetNumLists():
            return self.splitter.GetWindow(index)
        return None

    def AppendList(self, width=100, title=''):
        return self.InsertList(self.GetNumLists(), width, title)
    
    def InsertList(self, index, width, title):
        self.dprint(title)
        c = self.makeList(title)
        self.splitter.InsertWindow(index, c, width)
        self.viewing = index
        wx.CallAfter(self.resetSize)
        return c
    
    def DeleteList(self, index, refresh=True):
        self.dprint("removing index=%d" % index)
        if index < self.GetNumLists():
            c = self.splitter.GetWindow(index)
            self.splitter.DetachWindow(c)
            c.DeleteAllItems()
            c.Destroy()
            del c
        else:
            raise IndexError("Attempting to remove list index %d; only %d lists total" % (index, self.GetNumLists()))
        if refresh:
            self.resetSize()

    def DeleteAfter(self, index):
        self.dprint("index=%d, before: %d" % (index, self.GetNumLists()))
        self.viewing = index
        index += 1
        while index < self.GetNumLists():
            self.DeleteList(index, False)
        self.dprint("after: %d" % self.GetNumLists())
        self.resetSize()

    def makeList(self, title):
        self.dprint(title)
        c = NeXTList(self.splitter, style=wx.LB_EXTENDED|wx.LB_ALWAYS_SB,
                     pos=(9000,9000))
        c.Bind(wx.EVT_LISTBOX, self.OnListSelect)
        c.SetFont(self.GetFont())
        return c

    def findLevel(self, list):
        if list in self.splitter._windows:
            idx = self.splitter._windows.index(list)
            return idx
        return -1

    def LaunchEvent(self, list, idx):
        self.dprint("launching event for index=%d" % idx)
        newevt = NeXTPanelEvent()
        newevt.list = list
        newevt.listnum = idx
        newevt.selections = list.GetSelections()
        self.GetEventHandler().ProcessEvent(newevt)
        
        list.SetFocus()

    def OnListSelect(self, evt):
        list = evt.GetEventObject()
        idx = self.findLevel(list)
        if idx == -1:
            # list not found
            evt.Skip()
            return

        if evt.IsSelection():
            self.dprint("SELECTION: %s idx=%d %s %s" % (list, idx, evt.GetSelection(), list.GetSelections()))
        
            # If it is a selection (not deselection), create a new event
            wx.CallAfter(self.LaunchEvent, list, idx)
        else:
            self.dprint("DESELECTION: %s idx=%d %s %s" % (list, idx, evt.GetSelection(), list.GetSelections()))



class NeXTFileManager(wx.Panel, debugmixin):
    """Display the filesystem in a NeXTPanel
    """
    debuglevel = 0

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        self.dirlevels = NeXTPanel(self)
        self.sizer.Add(self.dirlevels, 1, wx.EXPAND)
        self.Bind(EVT_NEXTPANEL,self.OnPanelUpdate)

        self.list_width = 100
        self.shown = 0
        self.dirtree = ['nothing yet']

        self.Layout()

    def SetFont(self, font):
        """Overridden function to set font of all sub lists."""
        self.dprint("font=%s" % font)
        wx.Panel.SetFont(self, font)
        self.dirlevels.SetFont(font)

    def reset(self):
        self.shown = 0
        items = self.getLevelItems(-1, None)
        self.showItems(self.shown, self.dirtree[self.shown], items)

    def showItems(self, index, keyword, items):
        list = self.dirlevels.GetList(index)
        if list is None:
            if len(items) == 0:
                # don't create a new level if there are no items to add
                return
            list = self.dirlevels.AppendList(self.list_width, keyword)
        list.DeleteAllItems()
        for item in items:
            #self.dprint(item)
            index = list.InsertStringItem(sys.maxint, item)

    def getLevelItems(self, level, item):
        if level<0:
            path = '/*'
        else:
            path = os.path.join('/', *self.dirtree[0:level+1])
            path = os.path.join(path, '*')
        paths = glob.glob(path)
        names = [os.path.basename(a) for a in paths]
        names.sort()
        return names

    def OnPanelUpdate(self, evt):
        self.dprint("select on list %d, selections=%s" % (evt.listnum, str(evt.selections)))
        self.shown = evt.listnum + 1
        list = evt.list
        newitems = []
        for i in evt.selections:
            item = list.GetString(i)
            if evt.listnum >= len(self.dirtree):
                self.dirtree.append(item)
            else:
                self.dirtree[evt.listnum] = item
            newitems.extend(self.getLevelItems(evt.listnum, item))
        self.showItems(self.shown, "blah", newitems)
        self.dprint("shown=%d" % self.shown)
        self.dirlevels.DeleteAfter(self.shown)
        self.dirlevels.ensureVisible(self.shown)




if __name__ == '__main__':
    class NeXTTest(wx.Panel, debugmixin):
        """Simple test that displays a hierarchy of numbers in the
        NeXTPanel.
        """
        debuglevel = 0

        def __init__(self, parent):
            wx.Panel.__init__(self, parent)
            self.default_font = self.GetFont()
            self.font = wx.Font(8, 
                                self.default_font.GetFamily(),
                                self.default_font.GetStyle(),
                                self.default_font.GetWeight())

            self.sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.SetSizer(self.sizer)

            self.dirlevels = NeXTPanel(self)
            self.dirlevels.SetFont(self.font)
            self.sizer.Add(self.dirlevels, 1, wx.EXPAND)
            self.Bind(EVT_NEXTPANEL,self.OnPanelUpdate)

            self.lists = ['genre', 'artist', 'album']
            self.list_width = 100
            self.shown = 0

            self.Layout()

        def reset(self):
            self.shown = 0
            items = self.getLevelItems(-1, None)
            self.showItems(self.shown, self.lists[self.shown], items)

        def showItems(self, index, keyword, items):
            list = self.dirlevels.GetList(index)
            if list is None:
                list = self.dirlevels.AppendList(self.list_width, keyword)
            list.DeleteAllItems()
            for item in items:
                #self.dprint(item)
                index = list.InsertStringItem(sys.maxint, item)

        def getLevelItems(self, level, item):
            if level<0:
                return [str(i) for i in range(10,25)]
            prefix = item
            return [prefix + str(i) for i in range(8)]

        def OnPanelUpdate(self, evt):
            self.dprint("select on list %d, selections=%s" % (evt.listnum, str(evt.selections)))
            self.shown = evt.listnum + 1
            list = evt.list
            newitems = []
            for i in evt.selections:
                item = list.GetString(i)
                newitems.extend(self.getLevelItems(evt.listnum, item))
            self.showItems(self.shown, "blah", newitems)
            self.dprint("shown=%d" % self.shown)
            self.dirlevels.DeleteAfter(self.shown)
            self.dirlevels.ensureVisible(self.shown)


    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='NeXT Panel Test', size=(400,500))
    frame.CreateStatusBar()
    
    # Add a panel that the rubberband will work on.
    #panel = NeXTTest(frame)
    panel = NeXTFileManager(frame)

    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)

    panel.reset()
    
    app.MainLoop()
