# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Miscellaneous wx controls.

This file contains various wx controls that don't have any
dependencies on other parts of peppy.
"""

import os

import wx
from wx.lib import buttons
from wx.lib import imageutils

class BitmapScroller(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)

        self.bmp = None
        self.width = 0
        self.height = 0
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def setBitmap(self, bmp):
        self.bmp = bmp
        if bmp is not None:
            self.width = bmp.GetWidth()
            self.height = bmp.GetHeight()
        else:
            self.width = 10
            self.height = 10
        self.SetVirtualSize((self.width, self.height))
        self.SetScrollRate(1,1)
        self.Refresh()

    def copyToClipboard(self):
        bmpdo = wx.BitmapDataObject(self.bmp)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def OnPaint(self, evt):
        if self.bmp is not None:
            dc=wx.BufferedPaintDC(self, self.bmp, wx.BUFFER_VIRTUAL_AREA)
            # Note that the drawing actually happens when the dc goes
            # out of scope and is destroyed.
            self.OnPaintHook(dc)
        evt.Skip()

    def OnPaintHook(self, dc):
        pass


#----------------------------------------------------------------------

class StatusBarButton(wx.lib.buttons.GenBitmapButton):
    """A minimally sized bitmap button for use in the statusbar.

    This is a small-sized button for use in the status bar that
    doesn't have the usual button highlight or button-pressed cues.
    Trying to mimic the Mozilla statusbar buttons as much as possible.
    """
    labelDelta = 0

    def _GetLabelSize(self):
        """ used internally """
        if not self.bmpLabel:
            return -1, -1, False
        return self.bmpLabel.GetWidth(), self.bmpLabel.GetHeight(), False

    def DoGetBestSize(self):
        """
        Overridden base class virtual.  Determines the best size of the
        button based on the label and bezel size.
        """
        width, height, useMin = self._GetLabelSize()
        return (width, height)
    
    def GetBackgroundBrush(self, dc):
        return None
