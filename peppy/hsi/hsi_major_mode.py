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

from peppy.actions.minibuffer import *
from peppy.actions import *
from peppy.major import *
from peppy.stcinterface import *

from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.hsi.common import *
from peppy.hsi.subcube import *
from peppy.hsi.filter import *
from peppy.hsi.view import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy
import wx.lib.plot as plot
import peppy.lib.plotter as plotter


class HSIMode(BitmapScroller, MajorMode):
    """Major mode for hyperspectral image analysis.

    ...
    """
    keyword='HSI'
    icon='icons/hsi-cube.png'

    stc_class = HyperspectralSTC

    default_classprefs = (
        StrParam('minor_modes', 'Spectrum, X Profile, Y Profile'),
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
        self.colorfilter = RGBFilter()
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
            if hasattr(minor, 'proxies'):
                plotproxy = minor.proxies[0]
                plotproxy.updateLines(*evt.imageCoords)
                try:
                    plotproxy.updateListeners()
                except Exception, e:
                    import traceback
                    dprint(traceback.format_exc())
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
        self.cubeview.show(self.colorfilter)
        self.setBitmap(self.cubeview.bitmap)
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
        return "%dx%dx%d %s %s %s image using %s loader" % (self.cube.samples, self.cube.lines, self.cube.bands, self.cube.interleave.upper(), self.cube.data_type.__name__, endian, self.dataset.getHandler().format_id)

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
            if hasattr(minor, 'proxies'):
                minor.setCube(self.cube)
                plotproxy = minor.proxies[0]
                plotproxy.setupAxes()

    def getPopupActions(self, evt, x, y):
        import peppy.hsi.hsi_menu
        import peppy.hsi.view
        return [
            peppy.hsi.view.CubeViewAction,
            peppy.hsi.filter.ColormapAction,
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


class HSIMinorModeMixin(MinorMode):
    @classmethod
    def worksWithMajorMode(self, mode):
        if mode.__class__ == HSIMode:
            return True
        return False
    
    def setCube(self, cube):
        pass
    
    def paneInfoHook(self, paneinfo):
        # adjust the width of the minor mode windows if they are placed on the
        # top or bottom -- the default width is generally too wide and the
        # plots will overlap.
        if self.classprefs.side in ['top', 'bottom']:
            paneinfo.MinSize(wx.Size(self.classprefs.min_width/2,
                                     self.classprefs.min_height))


class HSIPlotMinorMode(HSIMinorModeMixin, plotter.MultiPlotter,
                       plotter.PlotProxy):
    """Abstract base class for x-y plot of cube data.

    This displays a plot using the plotter.MultiPlotter class.  The
    plot_proxy attribute specifies which type of plot proxy defined in
    the MultiPlotter class to use.  Also must specify a keyword that
    uniquely identifies the minor mode.
    """
    keyword = None
    default_classprefs = (
        IntParam('best_width', 400),
        IntParam('best_height', 400),
        IntParam('min_width', 300),
        IntParam('min_height', 100),
        )
    plot_proxy = None

    def __init__(self, major, parent):
        plotter.MultiPlotter.__init__(self, parent, statusbarframe=major.frame)

        self.major = major

        self.listeners=[]
        self.rgblookup=['red','green','blue']
        self.setProxy(self)
    
    def setCube(self, cube):
        self.setupTitle()
        self.setupAxes()
        
    def setupTitle(self):
        self.title=self.keyword

    def setupAxes(self):
        pass
    
    def updateYAxis(self, yaxis):
        #dprint(yaxis)
        if yaxis != self.yaxis:
            # make copy of list.  The list returned by
            # getUpdatedExtrema is modified in place, so the compare
            # will always return true if we don't copy it.
            
            # Note: the plot widget expects the extrema values to be in
            # floating point, which isn't necessarily the case with the
            # computed extrema values.  Cast them to float here to be sure.
            self.yaxis=(float(yaxis[0]), float(yaxis[1]))
            # dprint("yaxis=%s" % self.yaxis)
            self.updateListenerExtrema()
    
    def sizeYAxis(self, lines):
        """Calculate Y axis extrema based on the wx.lib.plot.Polyline objects
        
        If the overall cube extrema is not used to set up the Y axis scale,
        this routine can be used to calculate the extrema based on the lines
        that will be shown.
        """
        #dprint(lines[0].points[:,1])
        lo = min([min(line.points[:,1]) for line in lines])
        hi = max([max(line.points[:,1]) for line in lines])
        if lo == hi:
            if lo == 0.0:
                hi = 1.0
            else:
                lo = lo / 2
                hi = lo * 3
        self.yaxis=(float(lo), float(hi))
        #dprint("yaxis=%s" % str(self.yaxis))
        self.updateListenerExtrema()


class HSISpectrumMinorMode(HSIPlotMinorMode):
    """Display a spectrum at the current crosshair point.
    """
    keyword = "Spectrum"

    def setupAxes(self):
        cubeview = self.major.cubeview
        self.xlabel = cubeview.getDepthXAxisLabel()
        self.xaxis = cubeview.getDepthXAxisExtrema()
        
        # syncing over the whole cube takes too long, so we'll grow
        # the axis as it gets bigger.  Start with the extrema of the
        # current band so we aren't too far off.
        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.major.cubeview
        # dprint("SpectrumPlotProxy: (%d,%d)" % (x,y))
        profile = cubeview.getDepthProfile(x, y)
        num = len(profile)
        
        data=numpy.zeros((num, 2))
        data[:,0] = cubeview.getDepthXAxis()
        data[:,1] = profile
        yaxis=cubeview.cube.getUpdatedExtrema()
        self.updateYAxis(yaxis)
        line = plot.PolyLine(data, legend= '%d, %d' % (x, y), colour='blue')
        return [line]
    

class HSIXProfileMinorMode(HSIPlotMinorMode):
    """Display the X profile at the current crosshair line.
    """
    keyword="X Profile"
    
    def setupAxes(self):
        cubeview = self.major.cubeview
        self.xlabel = cubeview.xProfileXAxisLabel
        self.xaxis=(0,cubeview.width)

        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.major.cubeview
        profiles=cubeview.getHorizontalProfiles(y)

        abscissas = numpy.arange(1,cubeview.width+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.width,2))
            data[:,0] = abscissas
            data[:,1] = self.major.filter.getXProfile(y, values)
            #line=plot.PolyLine(data, legend= 'band #%d' % cubeview.bands[colorindex][0], colour=self.rgblookup[colorindex])
            line=plot.PolyLine(data, legend=cubeview.getBandLegend(cubeview.bands[colorindex][0]), colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        if self.major.classprefs.use_cube_min_max:
            yaxis=cubeview.cube.getUpdatedExtrema()
            self.updateYAxis(yaxis)
        else:
            self.sizeYAxis(lines)
        return lines
        
class HSIYProfileMinorMode(HSIPlotMinorMode):
    """Display the Y profile at the current crosshair line.
    """
    keyword="Y Profile"
    
    def setupAxes(self):
        cubeview = self.major.cubeview

        self.xlabel = cubeview.yProfileXAxisLabel
        self.xaxis=(0, cubeview.height)

        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.major.cubeview
        profiles=cubeview.getVerticalProfiles(x)

        abscissas = numpy.arange(1,cubeview.height+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.height,2))
            data[:,0] = abscissas
            data[:,1] = self.major.filter.getYProfile(x, values)
            line=plot.PolyLine(data, legend=cubeview.getBandLegend(cubeview.bands[colorindex][0]), colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        if self.major.classprefs.use_cube_min_max:
            yaxis=cubeview.cube.getUpdatedExtrema()
            self.updateYAxis(yaxis)
        else:
            self.sizeYAxis(lines)
        return lines
