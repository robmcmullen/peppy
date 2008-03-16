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

import os, weakref

import wx
from wx.lib import buttons
from wx.lib import imageutils
from wx.lib import stattext
from wx.lib.pubsub import Publisher

from peppy.lib.iconstorage import *

if not '_' in dir():
    _ = unicode


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


class ModularStatusBarInfo(object):
    def __init__(self, parent, widths=[-1, 150]):
        self.parent = parent
        self.widths = widths
        
        self.cancel_label = _("Cancel")
        self.text = [' ' for w in self.widths]
        self.reset()

    def reset(self):
        self.gauge_value = 0
        self.gauge_width = 100
        self.gauge_max = 100
        
        self.overlays = []
        self.active_controls = []
        
        self.show_cancel = False
        self.cancelled = False
        if self.parent.info == self:
            self.parent.setWidths()

    def addIcon(self, bmp, tooltip=None):
        b = self.parent.getIcon(bmp, tooltip)
        self.active_controls.append(b)
        if self.parent.info == self:
            self.parent.setWidths()
    
    def setText(self, text, field=0):
        self.text[field] = text
        if self.parent.info == self:
            self.parent.SetStatusText(text, field)

    def startProgress(self, text, max=100, cancel=False, message=None):
        self.in_progress = True
        self.gauge_value_max = max
        self.cancelled = False
        self.show_cancel = cancel
        
        self.setText(text)
        self.overlays = []
        self.overlays.append((self.parent.gauge, self.gauge_width))

        if self.show_cancel:
            dc=wx.ClientDC(self.parent)
            tw, th = dc.GetTextExtent(self.cancel_label)
            tw += 20 # add some padding to the text for button border
            self.overlays.append((self.parent.cancel, tw))

        if message:
            Publisher().subscribe(self.updateMessage, message)
            self.message = message
        
        self.parent.gauge.SetRange(self.gauge_value_max)
        self.updateProgress(0)
        if self.parent.info == self:
            self.parent.setWidths()

    def updateProgress(self, value):
        self.gauge_value = value
        if self.parent.info == self:
            if value < 0:
                self.parent.gauge.Pulse()
            else:
                self.parent.gauge.SetValue(self.gauge_value)
    
    def isCancelled(self):
        return self.cancelled
    
    def isInProgress(self):
        return bool(self.overlays)

    def stopProgress(self, text="Completed."):
        if self.cancelled:
            self.setText("Cancelled.")
        else:
            self.setText(text)
        self.overlays = []
        Publisher().unsubscribe(self.updateMessage)
        self.message = None
        if self.parent.info == self:
            self.parent.setWidths()
        
    def updateMessage(self, msg):
        value = msg.data
        wx.CallAfter(self.updateProgress, value)


class ModularStatusBar(wx.StatusBar):
    def __init__(self, parent, widths=[-1, 150]):
        wx.StatusBar.__init__(self, parent, -1)

        if wx.Platform == '__WXGTK__':
            self.spacing = 3
        else:
            self.spacing = 0
        self.controls = {}
        
        self.info = None
        self.default_info = ModularStatusBarInfo(self, widths)
        self.info = self.default_info

        self.gauge = wx.Gauge(self, -1, 100)
        self.gauge.Hide()
        self.cancel = wx.Button(self, -1, _("Cancel"))
        self.cancel.Hide()
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancel)
        
        self.setWidths()

        self.sizeChanged = False
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        parent.SetStatusBar(self)
        self.Show()
    
    def changeInfo(self, info=None):
        if info:
            self.info = info
        else:
            self.info = self.default_info
        self.setWidths()

    def setWidths(self):
        self.widths = [i for i in self.info.widths]
        for widget in self.info.active_controls:
            self.widths.append(widget.GetSizeTuple()[0] + 2*self.spacing)
        self.widths.append(16 + 2*self.spacing) # leave space for the resizer
        self.SetFieldsCount(len(self.widths))
        self.SetStatusWidths(self.widths)
        for i in range(len(self.widths)):
            if i < len(self.info.widths):
                self.SetStatusText(self.info.text[i], i)
            else:
                self.SetStatusText(' ', i)
        self.Reposition()
        
    def getIcon(self, bmp, tooltip=None):
        if isinstance(bmp,str):
            bmp = getIconBitmap(bmp)
        if bmp not in self.controls:
            b = StatusBarButton(self, -1, bmp, style=wx.BORDER_NONE, pos=(9000,9000))
            b.Hide()
            self.controls[bmp] = b
        btn = self.controls[bmp]
        if tooltip:
            btn.SetToolTipString(tooltip)
        return btn

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
        shown = {}
        if self.info.active_controls:
            field = len(self.info.widths)
            for widget in self.info.active_controls:
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
                shown[widget] = True
                
                field += 1
        for widget in self.controls.values():
            state = widget in shown
            widget.Show(state)
            
        shown = {}
        if self.info.overlays:
            rect = self.GetFieldRect(0)
            x = rect.width
            overlays = [a for a in self.info.overlays]
            overlays.reverse()
            shown = {}
            for widget, width in overlays:
                x -= width
                widget.SetPosition((x, rect.y))
                widget.SetSize((width, rect.height))
                #print("x=%d width=%d widget=%s" % (x, width, widget))
                shown[widget] = True
        for widget in [self.gauge, self.cancel]:
            state = widget in shown
            widget.Show(state)
        self.sizeChanged = False

    def OnCancel(self, evt):
        self.info.cancelled = True


class FontBrowseButton(wx.Panel):
    """Simple panel and button to choose and display a new font.
    
    Borrowed from the wxPython demo.
    """
    
    def __init__(self, parent, font=None):
        wx.Panel.__init__(self, parent, -1)

        btn = wx.Button(self, -1, "Select Font")
        self.Bind(wx.EVT_BUTTON, self.OnSelectFont, btn)

        self.sampleText = stattext.GenStaticText(self, -1, "Sample Text", size=(150,-1))
        self.sampleText.SetBackgroundColour(wx.WHITE)
        
        if font is None:
            self.curFont = self.sampleText.GetFont()
        else:
            self.curFont = font
        self.curClr = wx.BLACK
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn, 0, wx.EXPAND)
        sizer.Add(self.sampleText, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.UpdateUI()

    def UpdateUI(self):
        self.sampleText.SetFont(self.curFont)
        self.sampleText.SetForegroundColour(self.curClr)
        self.sampleText.SetLabel("%s %s" % (self.curFont.GetFaceName(),
                                            self.curFont.GetPointSize()))
#        self.ps.SetLabel(str(self.curFont.GetPointSize()))
#        self.family.SetLabel(self.curFont.GetFamilyString())
#        self.style.SetLabel(self.curFont.GetStyleString())
#        self.weight.SetLabel(self.curFont.GetWeightString())
#        self.face.SetLabel(self.curFont.GetFaceName())
#        self.nfi.SetLabel(self.curFont.GetNativeFontInfo().ToString())
        self.Layout()

    def OnSelectFont(self, evt):
        data = wx.FontData()
        data.EnableEffects(True)
        data.SetColour(self.curClr)         # set colour
        data.SetInitialFont(self.curFont)

        dlg = wx.FontDialog(self, data)
        
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            colour = data.GetColour()

#            print('You selected: "%s", %d points, color %s\n' %
#                               (font.GetFaceName(), font.GetPointSize(),
#                                colour.Get()))

            self.curFont = font
            self.curClr = colour
            self.UpdateUI()

        # Don't destroy the dialog until you get everything you need from the
        # dialog!
        dlg.Destroy()
        
    def getFont(self):
        return self.curFont
        
    def setFont(self, font):
        if font is not None:
            self.curFont = font
        self.UpdateUI()


if __name__ == "__main__":
    class TestFrame(wx.Frame):
        def __init__(self, parent):
            wx.Frame.__init__(self, parent, -1, "Status Bar Test", wx.DefaultPosition, wx.DefaultSize)
            self.statusbar = ModularStatusBar(self)
            
            sizer = wx.BoxSizer(wx.VERTICAL)
            
            font = FontBrowseButton(self)
            sizer.Add(font, 0, wx.EXPAND)
            
            button1 = wx.Button(self, -1, "Statusbar 1")
            button1.Bind(wx.EVT_BUTTON, self.setStatus1)
            sizer.Add(button1, 0, wx.EXPAND)
            self.status_info1 = self.statusbar.info
            self.status_info1.addIcon("icons/windows.png", "DOS/Windows line endings")
            self.status_info1.addIcon("icons/apple.png", "Old-style Apple line endings")
            self.status_info1.addIcon("icons/tux.png", "Unix line endings")
            self.status_info1.setText("Status Bar 1")
            
            button2 = wx.Button(self, -1, "Statusbar 2")
            button2.Bind(wx.EVT_BUTTON, self.setStatus2)
            sizer.Add(button2, 0, wx.EXPAND)
            self.status_info2 = ModularStatusBarInfo(self.statusbar, [50, -1])
            self.status_info2.setText("Status Bar 2")
            self.status_info2.setText("blah", 1)

            button3 = wx.Button(self, -1, "Statusbar 3")
            button3.Bind(wx.EVT_BUTTON, self.setStatus3)
            sizer.Add(button3, 0, wx.EXPAND)
            self.status_info3 = ModularStatusBarInfo(self.statusbar, [150, -1])
            self.status_info3.addIcon("icons/tux.png", "Unix line endings")
            self.status_info3.addIcon("icons/apple.png", "Old-style Apple line endings")
            self.status_info3.setText("Status Bar 3")
            self.status_info3.startProgress("Stuff!")
            self.count3 = 0

            button4 = wx.Button(self, -1, "Statusbar 4")
            button4.Bind(wx.EVT_BUTTON, self.setStatus4)
            sizer.Add(button4, 0, wx.EXPAND)
            self.status_info4 = ModularStatusBarInfo(self.statusbar, [-1])
            self.status_info4.addIcon("icons/apple.png", "Old-style Apple line endings")
            self.status_info4.setText("Status Bar 4")
            self.status_info4.startProgress("Stuff!", cancel=True)
            self.count4 = 0

            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.OnTimer)
            self.timer.Start(1000/10)

            self.SetAutoLayout(1)
            self.SetSizer(sizer)
            self.Show(1)
        
        def OnTimer(self, evt):
            self.count3 = (self.count3 + 1) % 100
            self.status_info3.updateProgress(self.count3)
            if self.status_info4.isInProgress():
                if self.status_info4.isCancelled():
                    self.status_info4.stopProgress()
                else:
                    self.count4 = (self.count4 + 3) % 100
                    self.status_info4.updateProgress(self.count4)
        
        def setStatus1(self, evt):
            print("status 1")
            self.statusbar.changeInfo(self.status_info1)
            evt.Skip()
            
        def setStatus2(self, evt):
            print("status 2")
            self.statusbar.changeInfo(self.status_info2)
            evt.Skip()

        def setStatus3(self, evt):
            print("status 3")
            self.statusbar.changeInfo(self.status_info3)
            evt.Skip()

        def setStatus4(self, evt):
            print("status 4")
            self.statusbar.changeInfo(self.status_info4)
            evt.Skip()

    app   = wx.PySimpleApp()
    frame = TestFrame(None)
    
    app.MainLoop()
