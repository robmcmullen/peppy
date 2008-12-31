# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral image analysis mode.

Major mode for hyperspectral image viewing and analysis.  Commonly
used in remote sensing applications, hyperspectral images have many
more layers than just red, green, and blue.  You can think of them as
a stack of grayscale images, one on top of the other, where each image
in the stack is looking at the same field of view, but at a different
wavelength of light.

Each image in the stack is called a band, and because each pixel at
the same row and column in the band refers to the same spot on the
ground, each pixel can be associated with a spectrum.  Because there
can be hundreds of bands in an image, the spectrum can be quite high
resolution.  Because of the large number of samples in the spectrum,
the spectrum can be used to identify the material(s) in the pixel.

The Federation of American Scientists has a good tutorial about remote
sensing at http://www.fas.org/irp/imint/docs/rst/index.html, and it
includes sections about hyperspectral imagery.

There are many hyperspectral imagers; most are airborne or mounted on
spacecraft.  NASA's AVIRIS sensor (http://aviris.jpl.nasa.gov/) is
very well known in the field of earth remote sensing.  There is some
free data at http://aviris.jpl.nasa.gov/html/aviris.freedata.html

A common image format is the ENVI format, which consists of two files:
a data file in a raw format, and a header file that describes the
format.  Hyperspectral images are very large, typically on the order
of hundreds of megabytes for a standard scene.  This means that most
of the time an image won't be read entirely into memory at once.  This
major mode is capable of viewing images larger than physical memory.
"""

import os, struct, mmap
from cStringIO import StringIO

import wx
import wx.stc as stc
import wx.lib.newevent

from peppy.major import *
from peppy.stcinterface import *

from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.hsi.common import *
from peppy.hsi.subcube import *
from peppy.hsi.filter import *
from peppy.hsi.view import *


class HSIMode(BitmapScroller, MajorMode):
    """Major mode for hyperspectral image analysis.

    ...
    """
    keyword='HSI'
    icon='icons/hsi-cube.png'

    stc_class = HyperspectralSTC

    default_classprefs = (
        StrParam('minor_modes', 'Depth Profile, Horizontal Profile, Vertical Profile'),
        IntParam('band_number_offset', 1, help="Start counting band numbers from this value"),
        BoolParam('display_rgb', False),
        BoolParam('use_cube_min_max', False, help="Use overall cube min/max for profile min/max"),
        BoolParam('immediate_slider_updates', True, help="Refresh the image as the band slider moves rather than after releasing the slider"),
        BoolParam('use_mmap', False, help="Use memory mapping for data access when possible"),
        )

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        BitmapScroller.__init__(self, parent)
        
        self.applySettings()

        self.dataset = self.buffer.stc
        self.cube = None
        self.cubeview = CubeView(self, None)
        self.colormapper = RGBMapper()
        self.swap_endian = False
        self.filter = GeneralFilter()
        
        self.show_value_at_cursor = True
        self.immediate_slider_updates = self.classprefs.immediate_slider_updates
    
    def addUpdateUIEvent(self, callback):
        self.Bind(EVT_CROSSHAIR_MOTION, callback)

    def getStatusBarWidths(self):
        """Get the HSI status bar
        """
        return [-1, 100, 170]
    
    def updateInfo(self, x=-1, y=-1):
        line, sample, band = self.cubeview.getCoords(x, y)
        if x >= 0:
            self.setStatusText("x=%d y=%d" % (x, y), 1)
            pix = self.cube.getPixel(line, sample, band)
            if self.show_value_at_cursor:
                pos = (self.cube.locationToFlat(line, sample, band) * self.cube.itemsize) + self.cube.data_offset
                self.setStatusText("value=%s hex=%s location=%d" % (pix, hex(pix), pos), 0)
        
        self.setStatusText(self.cubeview.getBandName(band), 2)

    def OnUpdateUI(self, evt):
        assert self.dprint("updating HSI user interface!")
        self.updateInfo(*evt.imageCoords)
        for minor in self.wrapper.getActiveMinorModes(True):
            if hasattr(minor, 'updateProxies'):
                minor.updateProxies(*evt.imageCoords)
        if evt is not None:
            evt.Skip()
    
    def applySettings(self):
        # Change memory mapping limits
        if self.classprefs.use_mmap:
            Cube.mmap_size_limit = -1
        else:
            Cube.mmap_size_limit = 1

    def update(self, refresh=True):
        self.setStatusText(self.cubeview.getWorkingMessage())
        self.cubeview.swapEndian(self.swap_endian)
        self.cubeview.setFilterOrder([self.filter])
        self.cubeview.show(self.colormapper)
        self.setImage(self.cubeview.image)
        self.frame.updateMenumap()
        if refresh:
            self.Update()
        self.updateInfo()
        self.idle_update_menu = True
    
    def getProperties(self):
        pairs = MajorMode.getProperties(self)
        msg = self.getWelcomeMessage()
        pairs.append(("Format", msg))
        self.setStatusText(msg)
        return pairs

    def getWelcomeMessage(self):
        if self.cube.byte_order == HSI.BigEndian:
            endian = "big endian"
        else:
            endian = "little endian"
        extra = self.cube.getExtraWelcomeMessage()
        if extra:
            extra = " (%s)" % extra
        else:
            extra = ""
        return "%dx%dx%d %s %s %s image using %s loader%s" % (self.cube.samples, self.cube.lines, self.cube.bands, self.cube.interleave.upper(), self.cube.data_type.__name__, endian, self.dataset.getHandler().format_id, extra)

    def setCube(self, index=0):
        self.dataset_index = index
        if self.cubeview is not None:
            viewcls = self.cubeview.__class__
        else:
            viewcls = CubeView
        self.cube = self.dataset.getCube(index=index)
        self.cube.registerProgress(self.status_info)
        self.setViewer(viewcls)
        #self.cube.open()
        assert self.dprint(self.cube)
    
    def setViewer(self, viewcls):
        self.cubeview = viewcls(self, self.cube, self.classprefs.display_rgb)
        self.cubeview.swapEndian(self.swap_endian)
        for minor in self.wrapper.getActiveMinorModes():
            if hasattr(minor, 'setCubeView'):
                minor.setCubeView(self.cubeview)

    def getPopupActions(self, evt, x, y):
        import peppy.hsi.hsi_menu
        import peppy.hsi.filter_menu
        import peppy.hsi.view
        return [
            peppy.hsi.view.CubeViewAction,
            peppy.hsi.filter_menu.ColormapAction,
            peppy.hsi.hsi_menu.ShowPixelValues,
            peppy.hsi.hsi_menu.BandSliderUpdates,
            peppy.hsi.hsi_menu.SpatialSubset,
            ]
    
    def showInitialPosition(self, url, options=None):
        if options is None:
            options = {}
        if url.query:
            options.update(url.query)
        self.dprint("loading cube data from %s, options=%s" % (str(self.buffer.url), options))
        self.cube = self.dataset.getCube(self.buffer.url, progress=self.status_info, options=options)
        if self.cube.lines > 10000 or self.cube.samples > 10000:
            self.zoom = 0.125
        else:
            self.zoom = 1.0
        assert self.dprint(self.cube)
        viewer = CubeView
        if 'view' in options:
            if options['view'] == 'focalplane':
                viewer = FocalPlaneView
        self.setViewer(viewer)
        self.dprint("loading bands...")
        self.cubeview.loadBands()
        self.update()
    
    def revertPostHook(self):
        self.zoom = 1.0
        self.crop = None
        self.showInitialPosition(self.buffer.url)
        self.status_info.setText(self.getWelcomeMessage())
