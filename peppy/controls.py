# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Miscellaneous wx controls.

This file contains various wx controls that don't have any
dependencies on other parts of peppy.
"""

import os

import wx
import wx.stc as stc

class BitmapScroller(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)

        self.bmp = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def setBitmap(self, bmp):
        self.bmp = bmp
        if bmp is not None:
            self.SetVirtualSize((bmp.GetWidth(), bmp.GetHeight()))
        else:
            self.SetVirtualSize(10,10)
        self.SetScrollRate(1,1)
        self.Refresh()

    def OnPaint(self, evt):
        if self.bmp is not None:
            dc=wx.BufferedPaintDC(self, self.bmp, wx.BUFFER_VIRTUAL_AREA)
            # Note that the drawing actually happens when the dc goes
            # out of scope and is destroyed.
        evt.Skip()
