# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Scrolling Bitmap viewer.

This control is designed to be a generic bitmap viewer that can scroll
to handle large images.
"""

import os

import wx
from wx.lib import imageutils

from rubberband import RubberBand

try:
    from peppy.debug import *
except:
    def dprint(txt):
        print txt

class BitmapScroller(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)

        self.img = None
        self.scaled_bmp = None
        self.width = 0
        self.height = 0
        self.zoom = 4.0

        self.save_cursor = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.rb = RubberBand(drawingSurface=self)
        self.rb.enabled = False
        
        self.crosshair = None
        self.crossbox = None
        self.crosshair_img_coords = None
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnLeftButtonEvent)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

    def zoomIn(self, zoom=2):
        self.zoom *= zoom
        self.scaleImage()
        
    def zoomOut(self, zoom=2):
        self.zoom /= zoom
        self.scaleImage()
        
    def scaleImage(self):
        if self.img is not None:
            w = self.img.GetWidth() * self.zoom
            h = self.img.GetHeight() * self.zoom
            if self.zoom != 1:
                self.scaled_bmp = wx.BitmapFromImage(self.img.Scale(w, h))
            else:
                self.scaled_bmp = wx.BitmapFromImage(self.img)
            self.width = self.scaled_bmp.GetWidth()
            self.height = self.scaled_bmp.GetHeight()           
        else:
            self.width = 10
            self.height = 10
        self.SetVirtualSize((self.width, self.height))
        rate = int(self.zoom)
        if rate < 1:
            rate = 1
        self.SetScrollRate(rate, rate)
        self.Refresh()
        
    def setImage(self, img=None, zoom=None):
        if img is not None:
            # change the bitmap if specified
            self.bmp = None
            self.img = img
        else:
            self.bmp = self.img = None

        if zoom is not None:
            self.zoom = zoom

        self.scaleImage()

    def setBitmap(self, bmp=None, zoom=None):
        if bmp is not None:
            img = bmp.ConvertToImage()
            self.setImage(img, zoom)
        else:
            self.setImage(None, zoom)

    def copyToClipboard(self):
        bmpdo = wx.BitmapDataObject(self.scaled_bmp)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def convertEventCoords(self, ev):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        x = ev.GetX() + (xView * xDelta)
        y = ev.GetY() + (yView * yDelta)
        return (x, y)

    def getImageCoords(self, x, y, fixbounds = True):
        """Convert scrolled window coordinates to image coordinates.

        Convert from the scrolled window coordinates (where (0,0) is
        the upper left corner when the window is scrolled to the
        top-leftmost position) to the corresponding point on the
        unzoomed, unrotated image.
        """
        x = int(x / self.zoom)
        y = int(y / self.zoom)
        if fixbounds:
            if x<0: x=0
            elif x>=self.img.GetWidth(): x=self.img.GetWidth()-1
            if y<0: y=0
            elif y>=self.img.GetHeight(): y=self.img.GetHeight()-1
        return (x, y)

    def isInBounds(self, x, y):
        if self.img is None or x<0 or y<0 or x>=self.width or y>=self.height:
            return False
        return True

    def isEventInClientArea(self, ev):
        size = self.GetClientSizeTuple()
        x = ev.GetX()
        y = ev.GetY()
        if x < 0 or x >= size[0] or y < 0 or y >= size[1]:
            return False
        return True

    ##### - Crosshair drawing and events

    def drawCrosshair(self, dc, x, y):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        xoff = xView * xDelta
        yoff = yView * yDelta
        x -= xoff
        y -= yoff
        dprint('x=%d, y=%d' % (x, y))
        if self.crossbox:
            dc.DrawRectangle(self.crossbox[0] - xoff, self.crossbox[1] - yoff,
                             self.crossbox[2], self.crossbox[3])
            dc.DrawLine(x, 0, x,
                        self.crossbox[1] - yoff)
            dc.DrawLine(x, self.crossbox[1] + self.crossbox[3] - yoff + 1,
                        x, self.height)
            dc.DrawLine(0, y,
                        self.crossbox[0] - xoff, y)
            dc.DrawLine(self.crossbox[0] + self.crossbox[2] - xoff + 1, y,
                        self.width, y)
        else:
            dc.DrawLine(x, 0, x, self.height)
            dc.DrawLine(0, y, self.width, y)

    def setCrosshairFromImageCoords(self, x, y):
        self.crosshair_img_coords = (x, y)
        offset = int(self.zoom / 2)
        x = int(x * self.zoom)
        y = int(y * self.zoom)
        self.crosshair = (x + offset, y + offset)
        if self.zoom >= 1:
            self.crossbox = (x-1, y-1, self.zoom + 2, self.zoom + 2)
        else:
            self.crossbox = None
        dprint("crosshair = %s, img = %s" % (self.crosshair, self.crosshair_img_coords))

    def getCrosshairDC(self, dc=None):
        if dc is None:
            dc=wx.ClientDC(self)
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetLogicalFunction(wx.XOR)
        return dc

    def handleCrosshairEvent(self, ev=None):
        # draw crosshair (note: in event coords, not converted coords)
        coords = self.convertEventCoords(ev)
        img_coords = self.getImageCoords(*coords)
        if img_coords != self.crosshair_img_coords:
            dc=self.getCrosshairDC()
            if self.crosshair:
                # erase old one
                self.drawCrosshair(dc,*self.crosshair)
            self.setCrosshairFromImageCoords(*img_coords)
            self.drawCrosshair(dc,*self.crosshair)
            self.crosshairEventPostHook(ev)
        dprint(coords)
        if self.isInBounds(*coords) and self.isEventInClientArea(ev):
            if self.save_cursor is None:
                self.save_cursor = self.GetCursor()
                self.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))
        else:
            if self.save_cursor is not None:
                self.SetCursor(self.save_cursor)
                self.save_cursor = None

    def crosshairEventPostHook(self, ev=None):
        pass

    def getCrosshairCoordsOnImage(self):
        return self.getImageCoords(*self.crosshair)

    ##### - Rubber band stuff
    
    def getRubberBandState(self):
        return self.rb.enabled

    def setRubberBand(self, state):
        if state != self.rb.enabled:
            self.rb.enabled = state
            if state:
                if self.crosshair:
                    dc=self.getCrosshairDC()
                    self.drawCrosshair(dc, *self.crosshair)
                    self.crosshair = None
            else:
                self.rb.reset()


    def OnLeftButtonEvent(self, ev):
        if self.img:
            if self.rb.enabled:
                self.rb._handleMouseEvents(ev)
            else:
                if ev.LeftDown() or ev.Dragging():
                    self.handleCrosshairEvent(ev)
                elif ev.LeftUp():
                    if self.crosshair:
                        dc=self.getCrosshairDC()
                        self.drawCrosshair(dc,*self.crosshair)
                        self.crosshair = None
                    if self.save_cursor:
                        self.SetCursor(self.save_cursor)
                        self.save_cursor = None
     

    def OnKillFocus(self, evt):
        if self.crosshair:
            dc=self.getCrosshairDC()
            self.drawCrosshair(dc,*self.crosshair)
            self.crosshair = None

    def OnPaint(self, evt):
        if self.scaled_bmp is not None:
            dc=wx.BufferedPaintDC(self, self.scaled_bmp, wx.BUFFER_VIRTUAL_AREA)
            # Note that the drawing actually happens when the dc goes
            # out of scope and is destroyed.
            self.OnPaintHook(evt, dc)
        evt.Skip()

    def OnPaintHook(self, evt, dc):
        """Hook to draw any additional items onto the saved bitmap.

        Note that any changes made to the dc will be reflected in the
        saved bitmap, so subsequent times calling this function will
        continue to add new data to the image.
        """
        pass
