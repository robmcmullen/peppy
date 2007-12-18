# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Size reporter minor mode based on the SizeReporterCtrl from the
wxPython AUI demos.  This is about as simple as a minor mode as you
can get.  No user interaction at all, just a window that is added to
the major mode's manager.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.menu import *


class SizeReporterMinorMode(MinorMode, wx.PyControl):
    """
    Utility control that always reports its client size.  If embedded
    in an AUI manager, it can also display information about the
    position of the window within the managed framework.

    (From the wxPython AUI_DockingWindowMgr.py demo.)
    """
    keyword="Size Reporter"

    @classmethod
    def worksWithMajorMode(self, mode):
        return True

    def __init__(self, major, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):

        wx.PyControl.__init__(self, parent, id, pos, size, wx.NO_BORDER)
            
        self._mgr = major.wrapper._mgr

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)


    def OnPaint(self, event):

        dc = wx.PaintDC(self)
        
        size = self.GetClientSize()
        s = ("Size: %d x %d")%(size.x, size.y)

        dc.SetFont(wx.NORMAL_FONT)
        w, height = dc.GetTextExtent(s)
        height = height + 3
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)
        dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2))
        
        if self._mgr:
        
            pi = self._mgr.GetPane(self)
            
            s = ("Layer: %d")%pi.dock_layer
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*1))
           
            s = ("Dock: %d Row: %d")%(pi.dock_direction, pi.dock_row)
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*2))
            
            s = ("Position: %d")%pi.dock_pos
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*3))
            
            s = ("Proportion: %d")%pi.dock_proportion
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*4))
        

    def OnEraseBackground(self, event):
        # intentionally empty
        pass        
    

    def OnSize(self, event):
        self.Refresh()
        event.Skip()


class SizeReporterPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield SizeReporterMinorMode
