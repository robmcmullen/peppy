# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Multi-pane list similar to the NeXT file-manager


"""

import os, sys, struct, mmap
import urllib2
from cStringIO import StringIO

import wx
import wx.lib.newevent
import wx.lib.splitter
import wx.lib.scrolledpanel

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        #print txt
        pass

    class debugmixin(object):
        pass


# FIXME: the newevent.NewEvent() style didn't work; had to grab the
# PyCommandEvent pattern from the demo.

#(NeXTPanelEvent, EVT_NEXTPANEL) = wx.lib.newevent.NewEvent()

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
        self.Clear()

    def InsertStringItem(self, idx, txt):
        if idx == sys.maxint:
            self.Append(txt)
        else:
            self.Insert(txt, idx)

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
        # If the child window that gets the focus is not visible,
        # this handler will try to scroll enough to see it.
        evt.Skip()
        child = evt.GetWindow()
        print "BLAH! %s" % child
    

class NeXTPanel(HackedScrolledPanel, debugmixin):
    """NeXT file manager-like multi-list panel.

    Displays a group of independent column lists, where the number of
    columns can grow or shrink.
    """
    def __init__(self, parent):
        HackedScrolledPanel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        self.splitter = wx.lib.splitter.MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.sizer.Add(self.splitter, 1, wx.EXPAND)

        self.font = self.GetFont()
        self.viewing = -1

        c = wx.Panel(self, size=(1,1))
        self.splitter.AppendWindow(c, 1)
        self.Layout()
        self.SetAutoLayout(1)
        self.SetupScrolling()

    def resetSize(self):
        dprint(self.splitter.DoGetBestSize())
        self.SetVirtualSize(self.splitter.DoGetBestSize())
        self.ensureVisible(self.viewing)

    def ensureVisible(self, idx):
        dprint("Scrolling %d into view" % idx)
        total = 0
        sashes = []
        for i in range(self.GetNumLists()):
            total += self.splitter.GetSashPosition(i)
            sashes.append(total)
        dprint("sashes = %s" % sashes)
        
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
        dprint("first=%d last=%d, vs=%d sppu=%d cl=%d" % (first, last, vs_x, sppu_x, clntsz.width))

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
        self.font = font
        for c in self.lists:
            c.SetFont(font)

    def GetNumLists(self):
        return len(self.splitter._windows) - 1

    def GetList(self, index):
        if index < self.GetNumLists():
            return self.splitter.GetWindow(index)
        return None

    def AppendList(self, width=100, title=''):
        return self.InsertList(self.GetNumLists(), width, title)
    
    def InsertList(self, index, width, title):
        c = self.makeList(title)
        self.splitter.InsertWindow(index, c, width)
        self.viewing = index
        wx.CallAfter(self.resetSize)
        return c
    
    def DeleteList(self, index):
        if index < self.GetNumLists():
            c = self.splitter.GetWindow(index)
            self.splitter.DetachWindow(c)
            c.Destroy()
            del c
        else:
            raise IndexError("Attempting to remove list index %d; only %d lists total" % (index, self.GetNumLists()))
        self.resetSize()

    def DeleteAfter(self, index):
        dprint("index=%d, before: %d" % (index, self.GetNumLists()))
        index += 1
        while index < self.GetNumLists():
            self.DeleteList(index)
        dprint("after: %d" % self.GetNumLists())
        self.resetSize()

    def makeList(self, title):
        c = NeXTList(self.splitter, style=wx.LB_EXTENDED|wx.LB_ALWAYS_SB)
        c.Bind(wx.EVT_LISTBOX, self.OnListSelect)
        c.SetFont(self.font)
        return c

    def findLevel(self, list):
        if list in self.splitter._windows:
            idx = self.splitter._windows.index(list)
            return idx
        return -1

    def OnListSelect(self, evt):
        list = evt.GetEventObject()
        idx = self.findLevel(list)

        dprint("%s idx=%d %s %s" % (list, idx, evt.GetSelection(), list.GetSelections()))
        
        if evt.IsSelection():
            # If it is a selection (not deselection), create a new event
            newevt = NeXTPanelEvent()
            newevt.list = list
            newevt.listnum = idx
            newevt.selections = list.GetSelections()
            self.GetEventHandler().ProcessEvent(newevt)

            list.SetFocus()
        evt.Skip()

class NeXTTest(wx.Panel, debugmixin):
    """Control to search through the MPD database to add songs to the
    playlist.

    Displays genre, artist, album, and songs.
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
            #dprint(item)
            index = list.InsertStringItem(sys.maxint, item)

    def getLevelItems(self, level, item):
        if level<0:
            return [str(i) for i in range(10,25)]
        prefix = item
        return [prefix + str(i) for i in range(8)]

    def OnPanelUpdate(self, evt):
        dprint("select on list %d, selections=%s" % (evt.listnum, str(evt.selections)))
        print evt.listnum, evt.selections
        self.shown = evt.listnum + 1
        list = evt.list
        newitems = []
        for i in evt.selections:
            item = list.GetString(i)
            newitems.extend(self.getLevelItems(evt.listnum, item))
        self.showItems(self.shown, "blah", newitems)
        dprint("shown=%d" % self.shown)
        self.dirlevels.DeleteAfter(self.shown)
        self.dirlevels.ensureVisible(self.shown)
        

if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='NeXT Panel Test', size=(300,500))
    frame.CreateStatusBar()
    
    # Add a panel that the rubberband will work on.
    panel = NeXTTest(frame)

    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)

    panel.reset()
    
    app.MainLoop()
