#-----------------------------------------------------------------------------
# Name:        controls.py
# Purpose:     miscellaneous wxPython controls
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Miscellaneous wx controls.

This file contains various wx controls that don't have any
dependencies on other parts of peppy.
"""

import os

import wx
from wx.lib import buttons
from wx.lib import imageutils

from iconstorage import *


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

        self.gauge = None
        self.gaugeWidth = 100
        self.overlays = []
        self.cancelled = False

        self.setWidths()

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
        if self.overlays:
            for widget, rect in self.overlays:
                widget.SetPosition((rect.x, rect.y))
                widget.SetSize((rect.width, rect.height))
        self.sizeChanged = False

    def startProgress(self, text, max=100, cancel=False):
        self.cancelled = False
        
        self.SetStatusText(text)

        dc=wx.ClientDC(self)
       
        gauge = wx.Gauge(self, -1, max)
        grect = self.GetFieldRect(0)
        grect.x = grect.width - self.gaugeWidth
        grect.width = self.gaugeWidth
        self.overlays.append((gauge, grect))
        self.gauge = gauge

        if cancel:
            text = _("Cancel")
            button = wx.Button(self, -1, text)
            self.Bind(wx.EVT_BUTTON, self.OnCancel, button)
            tw, th = dc.GetTextExtent(text)
            tw += 20 # add some padding to the text for button border
            crect = self.GetFieldRect(0)
            crect.x = crect.width - tw
            crect.width = tw
            grect.x -= tw
            self.overlays.append((button, crect))
            
        self.Reposition()

    def updateProgress(self, value):
        self.gauge.SetValue(value)

    def OnCancel(self, evt):
        self.cancelled = True
    
    def isCancelled(self):
        return self.cancelled

    def stopProgress(self, text="Completed."):
        for widget, rect in self.overlays:
            self.RemoveChild(widget)
            widget.Destroy()
        if self.cancelled:
            self.SetStatusText("Cancelled.")
        else:
            self.SetStatusText(text)
        self.overlays = []
        self.gauge = None
        
