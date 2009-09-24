# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Major mode for viewing images.  This mode leaves the image in its
native format, so only non-destructive operations are available.  This
set of operations would include affine transformations (rotations,
translations, reflections, skews, etc.), cropping, color map changes,
and potentially others; but not pixel-level operations.  This is
because the data is left in the buffer in the file format's native
byte structure.

In order to edit pixels the image would have to be decompressed into
raw pixels, which is a different purpose than this viewer.  Pixel
editing will be left to a different major mode.
"""

import os
from cStringIO import StringIO

import wx
import wx.stc
from wx.lib.evtmgr import eventManager
import wx.lib.newevent

from peppy.actions import *
from peppy.major import *
from peppy.lib.bitmapscroller import *
from peppy.stcinterface import *


class OpenImageViewer(SelectAction):
    """
    Test action to open a sample image file.
    """
    name = "&Open Image Viewer..."
    tooltip = "Open an Image Viewer"
    default_menu = "&Help/Samples"

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:red.png")

class ImageActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return issubclass(modecls, BitmapScroller)

class ZoomIn(ImageActionMixin, SelectAction):
    name = "Zoom In"
    tooltip = "Zoom in (magnify) image"
    default_menu = ("View", -800)
    icon = 'icons/zoom_in.png'
    keyboard = "="
    
    def action(self, index=-1, multiplier=1):
        self.mode.zoomIn()

class ZoomOut(ImageActionMixin, SelectAction):
    name = "Zoom Out"
    tooltip = "Zoom out (demagnify) image"
    default_menu = ("View", 801)
    icon = 'icons/zoom_out.png'
    keyboard = "-"
    
    def action(self, index=-1, multiplier=1):
        self.mode.zoomOut()

class RectangularSelect(ImageActionMixin, ToggleAction):
    name = "Select Rect"
    tooltip = "Select rectangular region."
    default_menu = ("Edit", -501)
    icon = 'icons/shape_square_rect_select.png'
    
    def isChecked(self):
        mode = self.frame.getActiveMajorMode()
        return mode.use_selector == RubberBand

    def action(self, index=-1, multiplier=1):
        mode = self.mode
        if mode.use_selector == RubberBand:
            mode.setSelector(Crosshair)
        else:
            mode.setSelector(RubberBand)


class ImageViewMode(BitmapScroller, STCInterface, MajorMode):
    """
    Major mode for viewing images.  Eventually this may contain more
    image manipulation commands like rotation, reflection, zooming,
    etc., but not pixel editing features.  Pixel editing features will
    mean that the image will have to be decompressed into raw pixels.
    This mode leaves the image in its native format.
    """
    keyword="ImageView"
    icon='icons/picture.png'

    default_classprefs = (
        StrParam('extensions', 'jpg jpeg gif bmp png ico', fullwidth=True),
        )

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        BitmapScroller.__init__(self, parent)
        self.update()
        
    def update(self):
        bytes = self.buffer.stc.GetBinaryData()
        #dprint(repr(bytes))
        fh = StringIO(bytes)

        # Can't use wx.ImageFromStream(fh), because a malformed image
        # causes python to crash.
        img = wx.EmptyImage()
        if img.LoadStream(fh):
            self.setImage(img)
        else:
            raise TypeError("Bad image -- either it really isn't an image, or wxPython doesn't support the image format.")

    def createListenersPostHook(self):
        eventManager.Bind(self.underlyingSTCChanged, wx.stc.EVT_STC_MODIFIED,
                          self.buffer.stc)

        # Thread stuff for the underlying change callback
        self.waiting=None

    def removeListenersPostHook(self):
        """
        Clean up the event manager hook that we needed to find out
        when the buffer had been changed by some other view of the
        buffer.
        """
        assert self.dprint("unregistering %s" % self.underlyingSTCChanged)
        eventManager.DeregisterListener(self.underlyingSTCChanged)        
        
    def underlyingSTCChanged(self,evt):
        """
        Update the image when it has been changed by another view of
        the data.

        @param evt: EVT_STC_MODIFIED event 
        """
        # Since we can never edit the image directly, we don't need to
        # short-circuit this callback like we do with hexedit mode.
        # Every change that we get here means that the image has
        # changed.

        # FIXME: don't actually perform the complete update right now
        # because it's probably too slow.  Queue it for later and put
        # it in a thread.
        # self.update()
        pass

    def CanCopy(self):
        return True

    def Copy(self):
        """Copy the image to the clipboard by overriding the STC's copy"""
        dprint()
        self.copyToClipboard()


class ImageViewPlugin(IPeppyPlugin, debugmixin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    def getMajorModes(self):
        yield ImageViewMode
    
    def getActions(self):
        return [OpenImageViewer, ZoomIn, ZoomOut, RectangularSelect]
