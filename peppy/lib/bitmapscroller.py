# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Scrolling Bitmap viewer.

This control is designed to be a generic bitmap viewer that can scroll
to handle large images.

Coordinate systems:

Event coords are in terms of 
"""

import os

import wx
from wx.lib import imageutils

try:
    from peppy.debug import *
except:
    def dprint(txt):
        print txt


class MouseSelector(object):
    def __init__(self, scroller):
        self.scroller = scroller
        self.world_coords = None
        self.last_img_coords = None
        self.blank_cursor = False
        
    def startEvent(self, ev):
        coords = self.scroller.convertEventCoords(ev)
        img_coords = self.scroller.getImageCoords(*coords)
        self.setWorldCoordsFromImageCoords(*img_coords)
        self.draw()
        self.handleEventPostHook(ev)
        dprint("ev: (%d,%d), coords: (%d,%d)" % (ev.GetX(), ev.GetY(), coords[0], coords[1]))
        if self.blank_cursor:
            self.scroller.blankCursor(ev, coords)
        
    def handleEvent(self, ev):
        # draw crosshair (note: in event coords, not converted coords)
        coords = self.scroller.convertEventCoords(ev)
        img_coords = self.scroller.getImageCoords(*coords)
        if img_coords != self.last_img_coords:
            self.erase()
            self.setWorldCoordsFromImageCoords(*img_coords)
            self.draw()
            self.handleEventPostHook(ev)
        dprint("ev: (%d,%d), coords: (%d,%d)" % (ev.GetX(), ev.GetY(), coords[0], coords[1]))
        if self.blank_cursor:
            self.scroller.blankCursor(ev, coords)

    def handleEventPostHook(self, ev=None):
        pass

    def finishEvent(self, ev):
        self.erase()

    def draw(self):
        if self.world_coords:
            dc=self.getXORDC()
            self.drawSelector(dc)

    def recalc(self):
        self.setWorldCoordsFromImageCoords(*self.last_img_coords)

    def erase(self):
        self.draw()
        self.world_coords = None
    
    def getXORDC(self, dc=None):
        if dc is None:
            dc=wx.ClientDC(self.scroller)
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetLogicalFunction(wx.XOR)
        return dc

    def getViewOffset(self):
        xView, yView = self.scroller.GetViewStart()
        xDelta, yDelta = self.scroller.GetScrollPixelsPerUnit()
        xoff = xView * xDelta
        yoff = yView * yDelta
        return -xoff, -yoff
    
    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        zoom = self.scroller.zoom
        offset = int(zoom / 2)
        x = int(x * zoom)
        y = int(y * zoom)
        self.world_coords = (x + offset, y + offset)

class Crosshair(MouseSelector):
    def __init__(self, scroller):
        MouseSelector.__init__(self, scroller)
        self.blank_cursor = True

        self.crossbox = None
        
    def drawSelector(self, dc):
        xoff, yoff = self.getViewOffset()
        x = self.world_coords[0] + xoff
        y = self.world_coords[1] + yoff
        if self.crossbox:
            dc.DrawRectangle(self.crossbox[0] + xoff, self.crossbox[1] + yoff,
                             self.crossbox[2], self.crossbox[3])
            dc.DrawLine(x, 0, x,
                        self.crossbox[1] + yoff)
            dc.DrawLine(x, self.crossbox[1] + self.crossbox[3] + yoff + 1,
                        x, self.scroller.height)
            dc.DrawLine(0, y,
                        self.crossbox[0] + xoff, y)
            dc.DrawLine(self.crossbox[0] + self.crossbox[2] + xoff + 1, y,
                        self.scroller.width, y)
        else:
            dc.DrawLine(x, 0, x, self.scroller.height)
            dc.DrawLine(0, y, self.scroller.width, y)

    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        zoom = self.scroller.zoom
        offset = int(zoom / 2)
        x = int(x * zoom)
        y = int(y * zoom)
        self.world_coords = (x + offset, y + offset)
        if self.scroller.zoom >= 1:
            self.crossbox = (x-1, y-1, zoom + 2, zoom + 2)
        else:
            self.crossbox = None
        dprint("crosshair = %s, img = %s" % (self.world_coords, self.last_img_coords))


class RubberBand(MouseSelector):
    def __init__(self, scroller):
        MouseSelector.__init__(self, scroller)
        self.start_world_coords = None

    def getXORDC(self, dc=None):
        if dc is None:
            dc=wx.ClientDC(self.scroller)
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetLogicalFunction(wx.XOR)
        return dc

    def drawSelector(self, dc):
        xoff, yoff = self.getViewOffset()
        x = self.start_world_coords[0] + xoff
        y = self.start_world_coords[1] + yoff
        w = self.world_coords[0] - self.start_world_coords[0]
        h = self.world_coords[1] - self.start_world_coords[1]

        # adjust pixel offsets so that the rubber band surrounds
        # zoomed pixels without covering up any part of the selected
        # pixels
        if w > 0:
            x -= 1
            w += 2
        if h > 0:
            y -= 1
            h += 2
        dprint("start=%s current=%s  xywh=%s" % (self.start_world_coords,
                                                 self.world_coords, (x,y,w,h)))
        dc.DrawRectangle(x, y, w, h)

    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        zoom = self.scroller.zoom
        x = int(x * zoom)
        y = int(y * zoom)
        if self.start_world_coords is None:
            self.start_world_coords = (x, y)
        else:
            if x >= self.start_world_coords[0]:
                x += zoom
            if y >= self.start_world_coords[1]:
                y += zoom

        # Always point to the pixel itself, or if it's zoomed the
        # expanded pixel's upper left corner.  Taking care of
        # outlining the pixels is done in drawSelector
        self.world_coords = (x, y)
                


class BitmapScroller(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)

        # Settings
        self.background_color = wx.Colour(160, 160, 160)
        self.use_checkerboard = True
        self.checkerboard_box_size = 8
        self.checkerboard_color = wx.Colour(96, 96, 96)
        self.max_zoom = 16.0
        self.min_zoom = 0.0625

        # internal storage
        self.img = None
        self.scaled_bmp = None
        self.width = 0
        self.height = 0
        self.zoom = 4.0

        self.save_cursor = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.use_selector = RubberBand
        self.selector = None
        self.last_img_coords = None
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnLeftButtonEvent)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

    def zoomIn(self, zoom=2):
        self.zoom *= zoom
        if self.zoom > self.max_zoom:
            self.zoom = self.max_zoom
        self.scaleImage()
        
    def zoomOut(self, zoom=2):
        self.zoom /= zoom
        if self.zoom < self.min_zoom:
            self.zoom = self.min_zoom
        self.scaleImage()

    def clearBackground(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.background_color))
        dc.Clear()

    def checkerboardBackground(self, dc, w, h):
        # draw checkerboard for transparent background
        box = self.checkerboard_box_size
        y = 0
        while y < h:
            #dprint("y=%d, y/box=%d" % (y, (y/box)%2))
            x = box * ((y/box)%2)
            while x < w:
                dc.SetPen(wx.Pen(self.checkerboard_color))
                dc.SetBrush(wx.Brush(self.checkerboard_color))
                dc.DrawRectangle(x, y, box, box)
                #dprint("draw: xywh=%s" % ((x, y, box, box),))
                x += box*2
            y += box

    def drawBackground(self, dc, w, h):
        self.clearBackground(dc, w, h)
        if self.use_checkerboard:
            self.checkerboardBackground(dc, w, h)
            
    def scaleImage(self):
        if self.img is not None:
            w = int(self.img.GetWidth() * self.zoom)
            h = int(self.img.GetHeight() * self.zoom)
            dc = wx.MemoryDC()
            self.scaled_bmp = wx.EmptyBitmap(w, h)
            dc.SelectObject(self.scaled_bmp)
            self.drawBackground(dc, w, h)
            dc.DrawBitmap(wx.BitmapFromImage(self.img.Scale(w, h)), 0,0, True)
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

    def blankCursor(self, ev, coords=None):
        if coords is None:
            coords = self.convertEventCoords(ev)

        if self.isInBounds(*coords) and self.isEventInClientArea(ev):
            if self.save_cursor is None:
                self.save_cursor = self.GetCursor()
                self.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))
        else:
            if self.save_cursor is not None:
                self.SetCursor(self.save_cursor)
                self.save_cursor = None

    def getSelectorCoordsOnImage(self):
        if self.selector:
            return self.getImageCoords(*self.selector.pos)
        return None
    
    #### - Automatic scrolling

    def autoScroll(self, ev):
        x = ev.GetX()
        y = ev.GetY()
        size = self.GetClientSizeTuple()
        if x < 0:
            dx = x
        elif x > size[0]:
            dx = x - size[0]
        else:
            dx = 0
        if y < 0:
            dy = y
        elif y > size[1]:
            dy = y - size[1]
        else:
            dy = 0
        wx.CallAfter(self.autoScrollCallback, dx, dy)

    def autoScrollCallback(self, dx, dy):
        spx = self.GetScrollPos(wx.HORIZONTAL)
        spy = self.GetScrollPos(wx.VERTICAL)
        if self.selector:
            self.selector.erase()
        self.Scroll(spx+dx, spy+dy)
        if self.selector:
            self.selector.recalc()
            self.selector.draw()

    def setSelector(self, selector):
        if self.selector:
            self.selector = None
        if self.save_cursor:
            self.SetCursor(self.save_cursor)
            self.save_cursor = None
        self.use_selector = selector

    def OnLeftButtonEvent(self, ev):
        if self.img:
            if ev.LeftDown():
                assert self.selector is None
                self.selector = self.use_selector(self)
                self.selector.startEvent(ev)
            elif ev.Dragging():
                if self.selector:
                    self.selector.handleEvent(ev)
                if not self.isEventInClientArea(ev):
                    self.autoScroll(ev)
            elif ev.LeftUp():
                if self.selector:
                    self.selector.finishEvent(ev)
                    self.selector = None
                if self.save_cursor:
                    self.SetCursor(self.save_cursor)
                    self.save_cursor = None
     

    def OnKillFocus(self, evt):
        if self.selector:
            self.selector.erase()
            self.selector = None

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
