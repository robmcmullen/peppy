# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
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

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.lib.bitmapscroller import *
from peppy.stcinterface import *


class OpenImageViewer(SelectAction):
    """
    Test action to open a sample image file.
    """
    name = "&Open Image Viewer..."
    tooltip = "Open an Image Viewer"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        assert self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:red.png")

class ZoomIn(SelectAction):
    name = "Zoom In"
    tooltip = "Zoom in (magnify) image"
    icon = 'icons/zoom_in.png'
    keyboard = "="
    
    def action(self, pos=None):
        dprint()
        mode = self.frame.getActiveMajorMode()
        mode.editwin.zoomIn()

class ZoomOut(SelectAction):
    name = "Zoom Out"
    tooltip = "Zoom out (demagnify) image"
    icon = 'icons/zoom_out.png'
    keyboard = "-"
    
    def action(self, pos=None):
        dprint()
        mode = self.frame.getActiveMajorMode()
        mode.editwin.zoomOut()

class RectangularSelect(ToggleAction):
    name = "Select Rect"
    tooltip = "Select rectangular region."
    icon = 'icons/rectangular_select.png'
    
    def isChecked(self):
        mode = self.frame.getActiveMajorMode()
        return mode.editwin.use_selector == RubberBand

    def action(self, pos=None):
        print "Select mode!!!"
        mode = self.frame.getActiveMajorMode()
        if mode.editwin.use_selector == RubberBand:
            mode.editwin.setSelector(Crosshair)
        else:
            mode.editwin.setSelector(RubberBand)

class BitmapView(BitmapScroller):
    """
    Simple bitmap viewer that loads an image from the data in an STC.
    """
    def __init__(self, parent, frame, stc):
        BitmapScroller.__init__(self, parent)
        self.frame = frame
        self.stc = stc
        
    def update(self):
        fh = StringIO(self.stc.GetBinaryData(0,self.stc.GetTextLength()))

        # Can't use wx.ImageFromStream(fh), because a malformed image
        # causes python to crash.
        img = wx.EmptyImage()
        if img.LoadStream(fh):
            self.setImage(img)
        else:
            self.setImage(None)
            self.frame.SetStatusText("Invalid image")


class ImageSTCWrapper(STCProxy):
    def __init__(self, stc, win):
        self.stc = stc
        self.win = win
        
    def CanEdit(self):
        return False

    def CanCopy(self):
        return True

    def Copy(self):
        self.win.copyToClipboard()

    def CanCut(self):
        return False

    def CanPaste(self):
        return False

    def CanUndo(self):
        return False

    def CanRedo(self):
        return False

class ImageViewMode(MajorMode):
    """
    Major mode for viewing images.  Eventually this may contain more
    image manipulation commands like rotation, reflection, zooming,
    etc., but not pixel editing features.  Pixel editing features will
    mean that the image will have to be decompressed into raw pixels.
    This mode leaves the image in its native format.
    """
    
    keyword='ImageView'
    icon='icons/picture.png'
    regex="\.(jpg|jpeg|gif|bmp|png|ico)"

    debuglevel=0

    def createEditWindow(self,parent):
        """
        Create the bitmap viewer that is the main window of this major
        mode.

        @param parent: parent window in which to create this window 
        """
        assert self.dprint()

        win=BitmapView(parent,self.frame,self.buffer.stc)        
        #win=wx.Window(parent, -1)

        eventManager.Bind(self.underlyingSTCChanged,wx.stc.EVT_STC_MODIFIED,self.buffer.stc)

        # Thread stuff for the underlying change callback
        self.waiting=None

        return win

    def createWindowPostHook(self):
        """
        Initialize the bitmap viewer with the image contained in the
        buffer.
        """
        self.stc = ImageSTCWrapper(self.buffer.stc, self.editwin)
        self.editwin.update()

    def deleteWindowPostHook(self):
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
        # self.editwin.update()
        pass



class ImageViewPlugin(MajorModeMatcherBase,debugmixin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    implements(IMajorModeMatcher)
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    def possibleModes(self):
        yield ImageViewMode
    
    default_menu=((None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(OpenImageViewer)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("ImageView",None,Menu("Image").after("Major Mode")),
                   ("ImageView","Image",MenuItem(ZoomIn)),
                   ("ImageView","Image",MenuItem(ZoomOut)),
                   ("ImageView","Image",MenuItem(RectangularSelect)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)
