# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Simple smiley face minor mode.

This is about as simple as a minor mode as you can get.  No user interaction
at all, just a window that hopefully adds a bit of fun to your day.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.menu import *


class SmileyFaceMinorMode(MinorMode, wx.PyControl):
    """Draws a smiley face centered in the window.
    
    This is a simple example of a minor mode that can be used as a template
    for a minor mode that draws graphics to the window.
    """
    # All minor modes need a unique keyword
    keyword="Smiley"
    
    # In addition to the classprefs listed in the MinorMode superclass,
    # you can define your own classprefs here.  You may also override any
    # classprefs in the parent, although be sure not to change the type or
    # the operations performed by the parent may fail if it is expecting
    # e.g. an integer and you change it to a string.
    default_classprefs = (
        IntParam('pen_width', 3, 'width of pen for drawing lines'),
        StrParam('pen_color', 'black', 'color of lines'),
        StrParam('background_color', 'white', 'background color of window'),
        StrParam('face_color', 'gold', 'color of smiley face'),
    )
    
    # This class method must be defined in all minor modes -- it verifies
    # that this minor mode can interact with the major mode.  Usually it
    # should check for some characteristics in the major mode or attributes
    # of the major mode.
    @classmethod
    def worksWithMajorMode(self, mode):
        # The smiley face has no dependencies on any major mode.  It works
        # with anything, so just return True here.
        return True

    def __init__(self, major, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        # This is just a simple PyControl, so call the superclass __init__
        wx.PyControl.__init__(self, parent, id, pos, size, wx.NO_BORDER)
        
        # and set up the event bindings.  All the work is done in the
        # OnPaint method
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        
        # Figure out the radius of the smiley, taking the pen width into
        # account so we don't go outside the bounds
        size = self.GetClientSize()
        if size.x > size.y:
            radius = size.y/2 - self.classprefs.pen_width
        else:
            radius = size.x/2 - self.classprefs.pen_width
        
        # Always draw the smiley centered in the window
        cx = size.x/2
        cy = size.y/2

        dc.SetBrush(wx.Brush(self.classprefs.face_color))
        dc.SetPen(wx.Pen(self.classprefs.pen_color, self.classprefs.pen_width))
        dc.DrawCircle(cx, cy, radius)
        
        # Choose the eye offsets and draw the vertical lines
        eye_dx = radius/4
        eye_dy = radius/3
        dc.DrawLine(cx - eye_dx, cy - 2*eye_dy, cx - eye_dx, cy - eye_dy)
        dc.DrawLine(cx + eye_dx, cy - 2*eye_dy, cx + eye_dx, cy - eye_dy)
        
        # Draw the smile as an ellipse, slightly offset from center
        radsmile = radius*3/5
        dc.DrawEllipticArc(cx - radsmile, cy, 2 * radsmile, radsmile, 0.0, -180.0)
        
    def OnEraseBackground(self, evt):
        dc = evt.GetDC()
        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.SetBackground(wx.Brush(self.classprefs.background_color))
        dc.Clear()

    def OnSize(self, evt):
        self.Refresh()
        evt.Skip()


class SmileyFacePlugin(IPeppyPlugin):
    """The plugin object for the Smiley minor mode.
    
    The plugin object describes the additional functionality that is provided
    by this code.  There are a variety of interface methods provided by the
    superclass IPeppyPlugin, and only the interfaces actually used by the
    plugin need to be defined here.  All others default to no-ops.
    """
    def getMinorModes(self):
        # All we have is the one minor mode defined by the plugin, so
        # return it here.
        yield SmileyFaceMinorMode
