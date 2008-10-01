#-----------------------------------------------------------------------------
# Name:        springtabs.py
# Purpose:     Tab-bar control that pops up windows when clicked
#
# Author:      Rob McMullen
#
# Created:     2008
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""SpringTabs

This module provides popup windows from a group of tabs

"""

import os, sys, struct, Queue, threading, time, socket
from cStringIO import StringIO

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt


class FakePopupWindow(wx.MiniFrame):
    def __init__(self, parent, style=None):
        super(FakePopupWindow, self).__init__(parent, style = wx.NO_BORDER |wx.FRAME_FLOAT_ON_PARENT
                              | wx.FRAME_NO_TASKBAR)
        #self.Bind(wx.EVT_KEY_DOWN , self.OnKeyDown)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
    
    def OnChar(self, evt):
        #print("OnChar: keycode=%s" % evt.GetKeyCode())
        self.GetParent().GetEventHandler().ProcessEvent(evt)

    def Position(self, position, size):
        #print("pos=%s size=%s" % (position, size))
        self.Move((position[0]+size[0], position[1]+size[1]))
        
    def SetPosition(self, position):
        #print("pos=%s" % (position))
        self.Move((position[0], position[1]))
        
    def ActivateParent(self):
        """Activate the parent window
        @postcondition: parent window is raised

        """
        parent = self.GetParent()
        parent.Raise()
        parent.SetFocus()

    def OnFocus(self, evt):
        """Raise and reset the focus to the parent window whenever
        we get focus.
        @param evt: event that called this handler

        """
        print("On Focus: set focus to %s" % str(self.GetParent()))
        self.ActivateParent()
        evt.Skip()



class SpringTabItem(object):
    def __init__(self, title, window, icon=None):
        self.title = title
        self.window = window
        self.border = 4
    
    def getBorder(self):
        return self.border
    
    def getSize(self, dc):
        w, h = dc.GetTextExtent(self.title)
        return w, h


class SpringTabVerticalRenderer(object):
    def drawTabs(self, dc, width, tabs):
        x = 0
        y = 0
        for tab in tabs:
            h, w = tab.getSize(dc)
            border = tab.getBorder()
            dc.DrawRectangle(0, y, width, h + (2 * border))
            
            x = (width - w) / 2 + 1
            # If text is rotated 90 degrees counterclockwise, the rectangle
            # that contains it has its lower left corner at x, y
            dc.DrawRotatedText(tab.title, x, y + border + h, 90.0)
            y += h + 2 * border


class SpringTabs(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        
        self._tabs = []
        self._tab_renderer = SpringTabVerticalRenderer()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
    
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        
        size = self.GetClientSize()
        dc.SetFont(wx.NORMAL_FONT)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)
        
        dc.SetPen(wx.BLACK_PEN)
        self._tab_renderer.drawTabs(dc, size.x, self._tabs)


    def OnEraseBackground(self, event):
        # intentionally empty
        pass

    def OnSize(self, event):
        self.Refresh()
        event.Skip()

    def addTab(self, title, window):
        tab = SpringTabItem(title, window)
        self._tabs.append(tab)
        
        self.Refresh()





if __name__ == "__main__":
    app = wx.PySimpleApp()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(300,300))
    panel = wx.Panel(frm)
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    tabs = SpringTabs(panel)
    tabs.addTab("One", None)
    tabs.addTab("Two", None)
    tabs.addTab("Three", None)
    sizer.Add(tabs, 0, wx.EXPAND)
    text = wx.StaticText(panel, -1, "Just a placeholder here.  The real action is to the left!")
    sizer.Add(text, 1, wx.EXPAND)
    
    panel.SetAutoLayout(True)
    panel.SetSizer(sizer)
    #sizer.Fit(panel)
    #sizer.SetSizeHints(panel)
    panel.Layout()
    app.SetTopWindow(frm)
    frm.Show()
    app.MainLoop()
