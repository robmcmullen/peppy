# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
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
from peppy.menu import *
from peppy.major import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.hsi.common import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy
import wx.lib.plot as plot
import peppy.lib.plotter as plotter

# Some features require scipy, so set this flag to allow the features
# that require scipi to be enabled at runtime
try:
    import scipy
    import scipy.signal
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

class BandFilter(object):
    def __init__(self):
        self.planes=[]
        self.rgb=None
        
    def getGray(self,raw):
        minval=raw.min()
        maxval=raw.max()
        valrange=maxval-minval
        dprint("data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange)))
        if valrange==0.0:
            gray=(raw-minval).astype(numpy.uint8)
        else:
            gray=((raw-minval)*(255.0/(maxval-minval))).astype(numpy.uint8)

        return gray

    def getPlane(self,raw):
        return self.getGray(raw)

    def getRGB(self, cubeview, filt, progress=None):
        if not cubeview.cube: return None
        
        self.planes=[]

        count=0
        for band in cubeview.bands:
            dprint("getRGB: band=%s" % str(band))
            self.planes.append(self.getPlane(filt.getPlane(band[1])))
            if progress: progress.Update(50+((count+1)*50)/len(cubeview.bands))
            count+=1
        self.rgb=numpy.zeros((cubeview.height, cubeview.width, 3),numpy.uint8)
        dprint("shapes: rgb=%s planes=%s" % (self.rgb.shape, self.planes[0].shape))
        if count>0:
            for i in range(count):
                self.rgb[:,:,i]=self.planes[i]
            for i in range(count,3,1):
                self.rgb[:,:,i]=self.planes[0]
        #dprint(rgb[0,:,0])
        
        return self.rgb

class ContrastFilter(BandFilter):
    def __init__(self, stretch=0.0):
        BandFilter.__init__(self)
        self.contraststretch=stretch # percentage
        self.bins=256
   
    def setContrast(self,stretch):
        self.contraststretch=stretch

    def getPlane(self,raw):
        if self.contraststretch<=0.0:
            return self.getGray(raw)
        
        minval=raw.min()
        maxval=raw.max()
        valrange=maxval-minval
        dprint("data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange)))

        h,bins=numpy.histogram(raw,self.bins,range=(minval,maxval+1))
        dprint(h)
        dprint("h[%d]=%d" % (self.bins-1,h[self.bins-1]))
        #dprint(h)

        shape=raw.shape
        numpixels=raw.size
        lo=numpixels*self.contraststretch
        hi=numpixels*(1.0-self.contraststretch)
        dprint("lo=%d hi=%d" % (lo,hi))
        count=0
        for i in range(self.bins):
            if count>=lo:
                break
            count+=h[i]
        minscaled=minval+valrange*i/self.bins
        count=numpixels
        for i in range(self.bins-1,-1,-1):
            if count<=hi:
                break;
            count-=h[i]
        maxscaled=minval+valrange*i/self.bins
        dprint("scaled: min=%d max=%d" % (minscaled,maxscaled))
        if minscaled==maxscaled:
            gray=numpy.zeros(raw.shape,numpy.uint8)
        else:
            gray=(raw-minscaled)*(255.0/(maxscaled-minscaled))
            # orig=(raw-minval)*(255.0/(maxval-minval))
            # dprint(gray[0,:])
            # dprint(orig[0,:])
            gray=numpy.clip(gray,0,255).astype(numpy.uint8)

            # histogram uses min <= val < max, so we need to use 256 as
            # the max
            h,bins = numpy.histogram(gray,256,range=(0,256))
            dprint("h[255]=%d" % h[255])
            # dprint(h)

        return gray

class GeneralFilter(object):
    def __init__(self, pos=0):
        self.pos = pos
        
    def getPlane(self,raw):
        return raw

class MedianFilter1D(GeneralFilter):
    """Apply a median filter to the band.

    A median filter is a simple filter that uses a sliding window in
    each dimension to smooth the data.  It tends to preserve edges,
    which is one of the reasons to use this filter as opposed to a
    smoothing function.
    """
    def __init__(self, kernel_sample=3, kernel_line=1, pos=0):
        GeneralFilter.__init__(self, pos=pos)

        # since a band is stored in the array as [line, sample], the
        # kernel must be described that way as well
        self.kernel = [kernel_line, kernel_sample]
   
    def getPlane(self,raw):
        if HAS_SCIPY:
            filtered = scipy.signal.medfilt2d(raw.astype(numpy.float32), self.kernel)
            return filtered
        return raw

class CubeView(object):
    """Wrapper around a Cube object that provides a bitmap view.
    
    This class wraps a cube object and provides the interface needed by the
    bitmap viewing code to generate the appropriate bitmaps to view the
    selected bands in the cube.
    """
    name = "Image View"
    xProfileXAxisLabel = 'sample'
    yProfileXAxisLabel = 'line'

    def __init__(self, cube, display_rgb=True):
        self.display_rgb = display_rgb
        self.setCube(cube)
    
    def setCube(self, cube):
        # list of tuples (band number, band) where band is an array as
        # returned from cube.getBand
        self.bands=[]

        # Min/max for this group of bands only.  The cube's extrema is
        # held in cube.spectraextrema and is updated as more bands are
        # read in
        self.extrema=(0,1)

        # simple list of arrays, one array for each color plane r, g, b
        self.rgb=None
        self.bitmap=None
        self.contraststretch=0.0 # percentage

        self.initBitmap(cube)
        self.initDisplayIndexes()

    def initBitmap(self, cube, width=None, height=None):
        self.cube = cube
        if cube:
            if width:
                self.width = width
                self.height = height
            else:
                self.width = cube.samples
                self.height = cube.lines
        else:
            self.width = 128
            self.height = 128

        # Delay loading real bitmap till requested.  Make an empty one
        # for now.
        self.bitmap=wx.EmptyBitmap(self.width, self.height)

    def initDisplayIndexes(self):
        if self.cube:
            self.indexes = self.cube.guessDisplayBands()
            if not self.display_rgb and len(self.indexes)>1:
                self.indexes = [self.indexes[0]]
            dprint("display indexes = %s" % str(self.bands))
            self.max_index = self.cube.bands - 1
        else:
            self.indexes = [0]
            self.max_index = 0

    def loadBands(self, progress=None):
        if not self.cube: return

        self.bands=[]
        count=0
        emin=None
        emax=None
        for i in self.indexes:
            raw=self.cube.getBandInPlace(i)
            minval=raw.min()
            maxval=raw.max()
            self.bands.append((i,raw,minval,maxval))
            count+=1
            if emin==None or minval<emin:
                emin=minval
            if emax==None or maxval>emax:
                emax=maxval
            if progress: progress.Update((count*50)/len(bands))
        self.extrema=(emin,emax)

    def getHorizontalProfiles(self, y):
        """Get the horizontal profiles at the given height"""
        if not self.cube: return

        profiles=[]
        for band in self.bands:
            profile=band[1][y,:]
            profiles.append(profile)
        return profiles

    def getVerticalProfiles(self, x):
        """Get the vertical profiles at the given width"""
        if not self.cube: return

        profiles=[]
        for band in self.bands:
            profile=band[1][:,x]
            profiles.append(profile)
        return profiles
    
    def getDepthXAxisLabel(self):
        if self.cube.wavelengths:
            label = self.cube.wavelength_units
        else:
            label='band'
        return label

    def getDepthXAxisExtrema(self):
        if self.cube.wavelengths:
            axis = (self.cube.wavelengths[0],
                    self.cube.wavelengths[-1])
        else:
            axis=(0,self.cube.bands)
        return axis

    def getDepthXAxis(self):
        if self.cube.wavelengths:
            values = self.cube.wavelengths
        else:
            values = numpy.arange(1, self.cube.bands+1, 1)
        return values

    def getDepthProfile(self, x, y):
        """Get the profile into the monitor at the given x,y position"""
        profile = self.cube.getSpectra(y,x)
        return profile

    def nextIndex(self):
        newbands=[]
        for i in range(len(self.indexes)):
            newbands.append(self.indexes[i]+1)
        return self.setIndexes(newbands)

    def prevIndex(self):
        newbands=[]
        for i in range(len(self.indexes)):
            newbands.append(self.indexes[i]-1)
        return self.setIndexes(newbands)

    def gotoIndex(self, band):
        newbands=[band]
        return self.setIndexes(newbands)

    def setIndexes(self, newbands):
        display=True
        # greyscale image only needs the first array value, rgb image
        # uses all 3
        dprint("bands=%s" % newbands)

        # first check the range
        for i in range(len(self.indexes)):
            if newbands[i]<0 or newbands[i]>=self.cube.bands:
                display=False
                break

        # if all bands are in range, change the settings and display
        if display:
            for i in range(len(self.indexes)):
                self.indexes[i]=newbands[i]
        return display

    def show(self, prefilter, colorfilter, progress=None):
        if not self.cube: return

        refresh=False
        if self.indexes:
            if len(self.indexes)!=len(self.bands):
                refresh=True
            else:
                for i in range(len(self.indexes)):
                    if self.indexes[i]!=self.bands[i][0]:
                        refresh=True
                        break
        
        if refresh or not self.bands:
            self.loadBands()
        
        self.rgb=colorfilter.getRGB(self, prefilter, progress)
        image=wx.ImageFromData(self.width, self.height, self.rgb.tostring())
        self.bitmap=wx.BitmapFromImage(image)
        # wx.StaticBitmap(self, -1, self.bitmap, (0,0), (self.cube.samples,self.cube.lines))
        # self.Refresh()
    
    def saveImage(self,name):
        # convert to image so that save file can automatically
        # determine type from the filename.
        image=wx.ImageFromBitmap(self.bitmap)
        type=getImageType(name)
        dprint("saving image to %s with type=%d" % (name,type))
        return image.SaveFile(name,type)

    def copyImageToClipboard(self):
        bmpdo = wx.BitmapDataObject(self.bitmap)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def getCoords(self, x, y):
        """Convert the coordinates from the display x, y to sample, line, band.
        
        In the standard cube view, x is samples, y is lines, and the band is
        the first band in the indexes list.
        """
        return (y, x, self.indexes[0])

class FocalPlaneView(CubeView):
    name = "Focal Plane View"
    xProfileXAxisLabel = 'sample'
    yProfileXAxisLabel = 'band'

    def initBitmap(self, cube):
        if cube:
            CubeView.initBitmap(self, cube, cube.samples, cube.bands)
        else:
            CubeView.initBitmap(self, cube)

    def initDisplayIndexes(self):
        self.indexes = [0]
        if self.cube:
            self.max_index = self.cube.lines - 1

    def getCoords(self, x, y):
        """In a focal plane view, x is samples and y is the band number.  The
        line is the first element in the indexes list.
        """
        return (self.indexes[0], x, y)
    
    def loadBands(self, progress=None):
        if not self.cube: return

        self.bands=[]
        count=0
        emin=None
        emax=None
        for i in self.indexes:
            raw=self.cube.getFocalPlaneInPlace(i)
            minval=raw.min()
            maxval=raw.max()
            self.bands.append((i,raw,minval,maxval))
            count+=1
            if emin==None or minval<emin:
                emin=minval
            if emax==None or maxval>emax:
                emax=maxval
            if progress: progress.Update((count*50)/len(self.bands))
        self.extrema=(emin,emax)

    def getDepthXAxisLabel(self):
        return 'line'

    def getDepthXAxisExtrema(self):
        return (0,self.cube.lines)

    def getDepthXAxis(self):
        return numpy.arange(1, self.cube.lines+1, 1)

    def getDepthProfile(self, x, y):
        """Get the profile into the monitor at the given x,y position"""
        profile = self.cube.getFocalPlaneDepthInPlace(x, y)
        return profile


class HSIActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return isinstance(mode, HSIMode)

class PrevBand(HSIActionMixin, SelectAction):
    name = "Prev Band"
    tooltip = "Previous Band"
    default_menu = ("View", -200)
    icon = 'icons/hsi-band-prev.png'
    key_bindings = {'default': "C-P"}
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the low limit
            if band < 1:
                return False
        # nope, still room to decrement all bands
        return True

    def action(self, index=-1, multiplier=1):
        dprint("Previous band!!!")
        mode = self.mode
        if mode.cubeview.prevIndex():
            mode.update()

class NextBand(HSIActionMixin, SelectAction):
    name = "Next Band"
    tooltip = "Next Band"
    default_menu = ("View", 201)
    icon = 'icons/hsi-band-next.png'
    key_bindings = {'default': "C-N"}
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the high limit
            if band > self.mode.cubeview.max_index:
                return False
        # nope, still room to advance all bands
        return True

    def action(self, index=-1, multiplier=1):
        dprint("Next band!!!")
        mode = self.mode
        if mode.cubeview.nextIndex():
            mode.update()

class GotoBand(HSIActionMixin, MinibufferAction):
    name = "Goto Band"
    tooltip = "Go to a particular band in the cube"
    default_menu = ("View", 202)
    
    key_bindings = {'default': 'M-G',}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Band:"

    def processMinibuffer(self, minibuffer, mode, band):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        if mode.cubeview.gotoIndex(band):
            mode.update()

class CubeAction(HSIActionMixin, SelectAction):
    def isEnabled(self):
        mode = self.mode
        index = mode.dataset_index
        num = mode.dataset.getNumCubes()
        if index>0:
            return True
        return False

class PrevCube(CubeAction):
    name = "Prev Cube"
    tooltip = "Previous data cube in dataset"
    default_menu = ("Dataset", -100)
    icon = 'icons/hsi-cube-prev.png'

    def action(self, index=-1, multiplier=1):
        dprint("Prev cube!!!")
        mode = self.mode
        mode.prevCube()

class NextCube(CubeAction):
    name = "Next Cube"
    tooltip = "Next data cube in dataset"
    default_menu = ("Dataset", 101)
    icon = 'icons/hsi-cube-next.png'

    def action(self, index=-1, multiplier=1):
        dprint("Next cube!!!")
        mode = self.mode
        mode.nextCube()

class SelectCube(HSIActionMixin, RadioAction):
    debuglevel = 0
    name = "Select Cube"
    tooltip = "Select a cube from the dataset"
    default_menu = ("Dataset", 102)
    icon = 'icons/hsi-cube.png'

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)
        # do nothing here: it's actually changed in action

    def getIndex(self):
        mode = self.mode
        return mode.dataset_index

    def getItems(self):
        mode = self.mode
        self.dprint("datasets = %s" % mode.dataset.getCubeNames())
        return mode.dataset.getCubeNames()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        mode.setCube(index)
        dprint("mode.dataset_index = %d" % mode.dataset_index)
        wx.CallAfter(mode.update)
        
class ContrastFilterAction(HSIActionMixin, RadioAction):
    debuglevel = 0
    name = "Contrast"
    tooltip = "Contrast adjustment method"
    default_menu = ("View", -300)
    icon = 'icons/hsi-cube-next.png'

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)
        # do nothing here: it's actually changed in action

    def getIndex(self):
        mode = self.mode
        filt = mode.cubefilter
        #dprint(filt)
        if hasattr(filt, 'contraststretch'):
            val = filt.contraststretch
            if val > 0.0001 and abs(val - 0.1) < 0.0001:
                return 1
            elif abs(val - 0.2) < 0.0001:
                return 2
            else:
                return 3
        else:
            return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        if index == 0:
            filt = BandFilter()
        elif index == 1:
            filt = ContrastFilter(0.1)
        elif index == 2:
            filt = ContrastFilter(0.2)
        else:
            wx.CallAfter(self.setContrast, mode)
            return
        mode.cubefilter = filt
        wx.CallAfter(mode.update)

    def processMinibuffer(self, minibuffer, mode, percentage):
        dprint("returned percentage = %f" % percentage)
        filt = ContrastFilter(percentage)
        mode.cubefilter = filt
        wx.CallAfter(mode.update)
        
    def setContrast(self, mode):
        minibuffer = FloatMinibuffer(mode, self, label="Contrast [0.0 - 1.0]")
        mode.setMinibuffer(minibuffer)
        
class MedianFilterAction(HSIActionMixin, RadioAction):
    debuglevel = 1
    name = "Median Filter"
    tooltip = "Median filter"
    default_menu = ("View", 301)

    items = ['No median',
             'Median 3x1 pixel', 'Median 1x3 pixel', 'Median 3x3 pixel',
             'Median 5x1 pixel', 'Median 1x5 pixel', 'Median 5x5 pixel']

    def isEnabled(self):
        return HAS_SCIPY

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)
        # do nothing here: it's actually changed in action

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        dprint(filt)
        return filt.pos

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = MedianFilter1D(3, 1, pos=index)
        elif index == 2:
            filt = MedianFilter1D(1, 3, pos=index)
        elif index == 3:
            filt = MedianFilter1D(3, 3, pos=index)
        elif index == 4:
            filt = MedianFilter1D(5, 1, pos=index)
        elif index == 5:
            filt = MedianFilter1D(1, 5, pos=index)
        elif index == 6:
            filt = MedianFilter1D(5, 5, pos=index)
        mode.filter = filt
        wx.CallAfter(mode.update)


class CubeViewAction(HSIActionMixin, RadioAction):
    debuglevel = 1
    name = "View Direction"
    tooltip = ""
    default_menu = ("View", -600)

    items = [CubeView, FocalPlaneView]

    def getIndex(self):
        cls = self.mode.cubeview.__class__
        dprint(cls)
        return self.items.index(cls)

    def getItems(self):
        return [c.name for c in self.items]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        cls = self.mode.cubeview.__class__
        current = self.items.index(cls)
        if current != index:
            self.mode.setViewer(self.items[index])
            wx.CallAfter(self.mode.update)


class HSIMode(BitmapScroller, MajorMode):
    """Major mode for hyperspectral image analysis.

    ...
    """
    keyword='HSI'
    icon='icons/hsi-cube.png'

    stc_class = HyperspectralSTC

    default_classprefs = (
        StrParam('minor_modes', 'Spectrum, X Profile, Y Profile'),
        BoolParam('display_rgb', False),
        )

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        BitmapScroller.__init__(self, parent)

        self.dataset = self.buffer.stc.dataset
        self.cubeview = None
        self.cubefilter = BandFilter()
        self.filter = GeneralFilter()
#        self.setCube(0)
        self.cube = self.dataset.getCube(self.buffer.url)
        dprint(self.cube)
        self.setViewer(CubeView)
        #self.cube.open()
        dprint(self.cube)

        self.update(False) # initial case will refresh automatically
        self.stc = self.buffer.stc

    def addUpdateUIEvent(self, callback):
        self.Bind(EVT_CROSSHAIR_MOTION, callback)

    def getStatusBar(self):
        """Get the HSI status bar
        """
        if self.statusbar is None:
            self.statusbar = PeppyStatusBar(self.frame, [-1, 100, 100, 100, 80])
            self.createStatusIcons()
        return self.statusbar

    def OnUpdateUI(self, evt):
        assert self.dprint("updating HSI user interface!")
        line, sample, band = self.cubeview.getCoords(*evt.imageCoords)
        self.frame.SetStatusText("x=%d y=%d" % (evt.imageCoords), 1)
        self.frame.SetStatusText("S%d L%d B%d" % (sample, line, band), 2)
        pix = self.cube.getPixel(line, sample, band)
        self.frame.SetStatusText("%s %s" % (pix, hex(pix)), 3)
        pos = (self.cube.locationToFlat(line, sample, band) * self.cube.itemsize) + self.cube.data_offset
        self.frame.SetStatusText("%s" % pos, 4)
        for minor in self.wrapper.minors:
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

    def update(self, refresh=True):
        self.cubeview.show(self.filter, self.cubefilter)
        self.setBitmap(self.cubeview.bitmap)
        if refresh:
            self.Refresh()
        self.idle_update_menu = True

    def setCube(self, index=0):
        self.dataset_index = index
        if self.cubeview is not None:
            viewcls = self.cubeview.__class__
        else:
            viewcls = CubeView
        self.cube = self.dataset.getCube(index=index)
        self.setViewer(viewcls)
        #self.cube.open()
        dprint(self.cube)
    
    def setViewer(self, viewcls):
        self.cubeview = viewcls(self.cube, self.classprefs.display_rgb)
        self.cubeview.loadBands()
        for minor in self.wrapper.minors:
            if hasattr(minor, 'proxies'):
                plotproxy = minor.proxies[0]
                plotproxy.setupAxes()

    def nextCube(self):
        index = self.dataset_index
        num = self.dataset.getNumCubes()
        if index < (num-1):
            index += 1
            self.setCube(index)
            dprint("self.dataset_index = %d" % self.dataset_index)
            wx.CallAfter(self.update)

    def prevCube(self):
        index = self.dataset_index
        if index > 0:
            index -= 1
            self.setCube(index)
            dprint("self.dataset_index = %d" % self.dataset_index)
            wx.CallAfter(self.update)


class HSIMinorModeMixin(MinorMode):
    @classmethod
    def worksWithMajorMode(self, mode):
        if mode.__class__ == HSIMode:
            return True
        return False

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
        self.setupAxes()
        self.setupTitle()
        self.setProxy(self)
        
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

        x=numpy.arange(1,cubeview.width+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.width,2))
            data[:,0]=x
            data[:,1]=values
            line=plot.PolyLine(data, legend= 'band #%d' % cubeview.bands[colorindex][0], colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        yaxis=cubeview.cube.getUpdatedExtrema()
        self.updateYAxis(yaxis)
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

        x=numpy.arange(1,cubeview.height+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.height,2))
            data[:,0]=x
            data[:,1]=values
            line=plot.PolyLine(data, legend= 'band #%d' % cubeview.bands[colorindex][0], colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        yaxis=cubeview.cube.getUpdatedExtrema()
        self.updateYAxis(yaxis)
        return lines
