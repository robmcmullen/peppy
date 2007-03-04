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

from iconstorage import *

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


class PeppyStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)

        self.default_widths = [-1,100]
        if wx.Platform == '__WXGTK__':
            self.spacing = 3
        else:
            self.spacing = 0
        self.controls = []
        self.setWidths()

##        self.addIcon("icons/windows.png")
        
        self.sizeChanged = False
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def setWidths(self):
        self.widths = [i for i in self.default_widths]
        for widget in self.controls:
            self.widths.append(widget.GetSizeTuple()[0] + 2*self.spacing)
        self.widths.append(16 + 2*self.spacing) # leave space for the resizer
        self.SetFieldsCount(len(self.widths))
        self.SetStatusWidths(self.widths)
        self.Reposition()
        
    def reset(self):
        for widget in self.controls:
            self.RemoveChild(widget)
            widget.Destroy()
        self.controls = []
        self.setWidths()

    def addIcon(self, bmp, tooltip=None):
        if isinstance(bmp,str):
            bmp = getIconBitmap(bmp)
        b = StatusBarButton(self, -1, bmp, style=wx.BORDER_NONE)
        if tooltip:
            b.SetToolTipString(tooltip)
        self.controls.append(b)
        self.setWidths()

    def OnSize(self, evt):
        self.Reposition()  # for normal size events

        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.
        self.sizeChanged = True


    def OnIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()

    # reposition the checkbox
    def Reposition(self):
        if self.controls:
            field = len(self.default_widths)
            for widget in self.controls:
                rect = self.GetFieldRect(field)
                #dprint(rect)
                size = widget.GetSize()
                #dprint(size)
                xoffset = (rect.width - size.width)/2
                yoffset = (rect.height - size.height)/2
                #dprint((xoffset, yoffset))
                widget.SetPosition((rect.x + xoffset,
                                  rect.y + yoffset + self.spacing))
                #widget.SetSize((rect.width-4, rect.height-4))
                
                field += 1
        self.sizeChanged = False
