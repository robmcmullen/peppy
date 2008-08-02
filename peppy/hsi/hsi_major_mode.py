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

from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.hsi.common import *
from peppy.hsi.subcube import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy
import wx.lib.plot as plot
import peppy.lib.plotter as plotter

# Some features require scipy, so set this flag to allow the features
# that require scipi to be enabled at runtime
try:
    # Import this way to prevent py2exe from automatically including scipy
    scipy = __import__('scipy')
    __import__('scipy.signal')
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

class BandFilter(debugmixin):
    def __init__(self):
        self.planes=[]
        self.rgb=None
        
    def getGray(self,raw):
        minval=raw.min()
        maxval=raw.max()
        valrange=maxval-minval
        assert self.dprint("data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange)))
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
            assert self.dprint("getRGB: band=%s" % str(band))
            self.planes.append(self.getPlane(filt.getPlane(band[1])))
            if progress: progress.Update(50+((count+1)*50)/len(cubeview.bands))
            count+=1
        self.rgb=numpy.zeros((cubeview.height, cubeview.width, 3),numpy.uint8)
        assert self.dprint("shapes: rgb=%s planes=%s" % (self.rgb.shape, self.planes[0].shape))
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
        assert self.dprint("data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange)))

        h,bins=numpy.histogram(raw,self.bins,range=(minval,maxval+1))
        assert self.dprint(h)
        assert self.dprint("h[%d]=%d" % (self.bins-1,h[self.bins-1]))
        #dprint(h)

        shape=raw.shape
        numpixels=raw.size
        lo=numpixels*self.contraststretch
        hi=numpixels*(1.0-self.contraststretch)
        assert self.dprint("lo=%d hi=%d" % (lo,hi))
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
        assert self.dprint("scaled: min=%d max=%d" % (minscaled,maxscaled))
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
            assert self.dprint("h[255]=%d" % h[255])
            # dprint(h)

        return gray

class GeneralFilter(debugmixin):
    def __init__(self, pos=0):
        self.pos = pos
        
    def getPlane(self,raw):
        return raw
    
    def getXProfile(self, y, raw):
        """Get the x profile at a constant y.
        
        Not all filters will be appropriate for use with profile plots, but if
        so, this is the hook to provide the modification.
        """
        return raw

    def getYProfile(self, x, raw):
        """Get the y profile at a constant x.
        
        Not all filters will be appropriate for use with profile plots, but if
        so, this is the hook to provide the modification.
        """
        return raw

class SubtractFilter(GeneralFilter):
    """Apply a subtraction filter to the band.

    This filter subtracts data from the band.  Usually this is used to subtract
    dark data out of the band so that you can see what's left.
    """
    def __init__(self, band):
        GeneralFilter.__init__(self)
        self.darks = band
        self.dtype = band.dtype
        #dprint("subtracted datatype = %s" % self.dtype)
   
    def filter(self, raw, darks):
        if self.dtype == numpy.uint8:
            filtered = raw.astype(numpy.int8) - darks.astype(numpy.int8)
        elif self.dtype == numpy.uint16:
            filtered = raw.astype(numpy.int16) - darks.astype(numpy.int16)
        elif self.dtype == numpy.uint32:
            filtered = raw.astype(numpy.int32) - darks.astype(numpy.int32)
        else:
            filtered = raw - darks
        return filtered
    
    def getPlane(self, raw):
        return self.filter(raw, self.darks)
    
    def getXProfile(self, y, raw):
        # bands are in array form as line, sample
        return self.filter(raw, self.darks[y,:])
    
    def getYProfile(self, x, raw):
        # bands are in array form as line, sample
        return self.filter(raw, self.darks[:,x])

class ClipFilter(GeneralFilter):
    """Apply a cliping filter to the band.

    A cliping filter restricts the range of the image to specified values.
    """
    def __init__(self, min_clip=0, max_clip=None, pos=0):
        GeneralFilter.__init__(self, pos=pos)
        self.min_clip = min_clip
        self.max_clip = max_clip
   
    def getPlane(self,raw):
        if self.min_clip is not None and self.max_clip is not None:
            clipped = raw.clip(self.min_clip, self.max_clip)
        elif self.min_clip is not None:
            clipped = numpy.where(raw < self.min_clip, self.min_clip, raw)
        elif self.max_clip is not None:
            clipped = numpy.where(raw > self.max_clip, self.max_clip, raw)
        else:
            clipped = raw
        return clipped
    
    def getXProfile(self, y, raw):
        return self.getPlane(raw)
    
    def getYProfile(self, x, raw):
        return self.getPlane(raw)

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

class ChainFilter(GeneralFilter):
    """Apply a sequence of filters to the band.
    """
    def __init__(self, pos=0, filters=None):
        GeneralFilter.__init__(self, pos=pos)
        if filters:
            self.filters = filters
        else:
            self.filters = []
   
    def getPlane(self,raw):
        for filter in self.filters():
            raw = filter.getPlane(raw)
        return raw
    
    def getXProfile(self, y, raw):
        for filter in self.filters():
            raw = filter.getXProfile(y, raw)
        return raw
    
    def getYProfile(self, x, raw):
        for filter in self.filters():
            raw = filter.getYProfile(x, raw)
        return raw


class CubeView(debugmixin):
    """Wrapper around a Cube object that provides a bitmap view.
    
    This class wraps a cube object and provides the interface needed by the
    bitmap viewing code to generate the appropriate bitmaps to view the
    selected bands in the cube.
    """
    name = "Image View"
    xProfileXAxisLabel = 'sample'
    yProfileXAxisLabel = 'line'
    imageDirectionLabel = "Band"
    prev_index_icon = 'icons/hsi-band-prev.png'
    next_index_icon = 'icons/hsi-band-next.png'

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
        self.swap = False

        # Delay loading real bitmap till requested.  Make an empty one
        # for now.
        self.bitmap=wx.EmptyBitmap(self.width, self.height)

    def initDisplayIndexes(self):
        if self.cube:
            self.indexes = self.cube.guessDisplayBands()
            if not self.display_rgb and len(self.indexes)>1:
                self.indexes = [self.indexes[0]]
            assert self.dprint("display indexes = %s" % str(self.bands))
            self.max_index = self.cube.bands - 1
        else:
            self.indexes = [0]
            self.max_index = 0
    
    def getBand(self, index):
        raw = self.cube.getBandInPlace(index)
        if self.swap:
            raw = raw.byteswap()
        return raw
    
    def loadBands(self, progress=None):
        if not self.cube: return

        self.bands=[]
        count=0
        emin=None
        emax=None
        for i in self.indexes:
            raw=self.getBand(i)
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
    
    def swapEndian(self, swap):
        """Swap the data if necessary"""
        if (swap != self.swap):
            newbands = []
            for index, raw, v1, v2 in self.bands:
                swapped = raw.byteswap()
                newbands.append((index, swapped, swapped.min(), swapped.max()))
            self.bands = newbands
            self.swap = swap

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
        if self.swap:
            profile.byteswap(True) # swap in place
        return profile
    
    def getBandName(self, band_index):
        """Return the band name given the index"""
        text = self.cube.getDescriptiveBandName(band_index)
        if text:
            text = ": %s" % text
        return u"Band %d%s" % (band_index + HSIMode.classprefs.band_number_offset,
                               text)
    
    def getBandLegend(self, band_index):
        """Return the band name given the index"""
        return u"Band %d" % (band_index + HSIMode.classprefs.band_number_offset)
    
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

    def getIndex(self, band, user=False):
        if user:
            # If the user entered this number, adjust for the user's display
            # offset
            band = band - HSIMode.classprefs.band_number_offset
        return band

    def gotoIndex(self, band, user=False):
        newbands=[self.getIndex(band, user)]
        return self.setIndexes(newbands)

    def getIndexes(self):
        return self.indexes

    def setIndexes(self, newbands):
        display=True
        # greyscale image only needs the first array value, rgb image
        # uses all 3
        assert self.dprint("bands=%s" % newbands)

        # first check the range
        for i in range(len(self.indexes)):
            if newbands[i] < 0 or newbands[i] > self.max_index:
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
        assert self.dprint("saving image to %s with type=%d" % (name,type))
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
    imageDirectionLabel = "Frame"
    prev_index_icon = 'icons/hsi-frame-prev.png'
    next_index_icon = 'icons/hsi-frame-next.png'

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
    
    def getBand(self, index):
        raw = self.cube.getFocalPlaneInPlace(index)
        if self.swap:
            raw = raw.byteswap()
        return raw

    def getDepthXAxisLabel(self):
        return 'line'

    def getDepthXAxisExtrema(self):
        return (0,self.cube.lines)

    def getDepthXAxis(self):
        return numpy.arange(1, self.cube.lines+1, 1)

    def getDepthProfile(self, x, y):
        """Get the profile into the monitor at the given x,y position"""
        profile = self.cube.getFocalPlaneDepthInPlace(x, y)
        if self.swap:
            profile = profile.byteswap()
        return profile

    def getBandLegend(self, band_index):
        """Return the band name given the index"""
        return u"Frame %d" % (band_index + HSIMode.classprefs.band_number_offset)
    

class HSIActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return isinstance(mode, HSIMode)

class PrevBand(HSIActionMixin, OnDemandActionNameMixin, SelectAction):
    name = "Prev Band"
    default_menu = ("View", -200)
    icon = 'icons/hsi-band-prev.png'
    key_bindings = {'default': "C-P"}
    
    def getMenuItemName(self):
        return _("Prev %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Go to previous %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def getToolbarIconName(self):
        return self.mode.cubeview.prev_index_icon
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the low limit
            if band < 1:
                return False
        # nope, still room to decrement all bands
        return True

    def action(self, index=-1, multiplier=1):
        #assert self.dprint("Previous band!!!")
        mode = self.mode
        if mode.cubeview.prevIndex():
            mode.update(refresh=False)

class NextBand(HSIActionMixin, OnDemandActionNameMixin, SelectAction):
    name = "Next Band"
    tooltip = "Next Band"
    default_menu = ("View", 201)
    icon = 'icons/hsi-band-next.png'
    key_bindings = {'default': "C-N"}
    
    def getMenuItemName(self):
        return _("Next %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Go to next %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def getToolbarIconName(self):
        return self.mode.cubeview.next_index_icon
    
    def isEnabled(self):
        for band in self.mode.cubeview.indexes:
            # check if any of the display bands is at the high limit
            if band >= self.mode.cubeview.max_index:
                return False
        # nope, still room to advance all bands
        return True

    def action(self, index=-1, multiplier=1):
        assert self.dprint("Next band!!!")
        mode = self.mode
        if mode.cubeview.nextIndex():
            mode.update(refresh=False)

class GotoBand(HSIActionMixin, OnDemandActionNameMixin, MinibufferAction):
    name = "Goto Band"
    default_menu = ("View", 202)
    
    key_bindings = {'default': 'M-G',}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Band:"

    def getMenuItemName(self):
        return _("Goto %s") % self.mode.cubeview.imageDirectionLabel
    
    def getMenuItemHelp(self, name):
        return _("Goto a specified %s in the cube") % self.mode.cubeview.imageDirectionLabel.lower()
    
    def processMinibuffer(self, minibuffer, mode, band):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        if mode.cubeview.gotoIndex(band, user=True):
            mode.update(refresh=False)

class BandSlider(HSIActionMixin, SliderAction):
    name = "Seek Band"
    default_menu = ("View", 203)
    
    slider_width = 200
    
    def isEnabled(self):
        return self.mode.cubeview.max_index > 1
    
    def updateToolOnDemand(self):
        """Override so we can set the tooltip depending on the view direction"""
        name = _("Seek %s") % self.mode.cubeview.imageDirectionLabel
        self.slider.SetToolTip(wx.ToolTip(name))
        SliderAction.updateToolOnDemand(self)
    
    def getSliderValues(self):
        return self.mode.cubeview.indexes[0], 0, self.mode.cubeview.max_index
    
    def OnSliderMove(self, evt):
        index = evt.GetPosition()
        text = self.mode.cubeview.getBandLegend(index)
        self.mode.setStatusText(text)
        if self.mode.immediate_slider_updates:
            if self.mode.cubeview.gotoIndex(index, user=False):
                self.mode.update()
    
    def action(self, index=-1, multiplier=1):
        #dprint("index=%d" % index)
        if self.mode.immediate_slider_updates and index == self.mode.cubeview.indexes[0]:
            # don't refresh the window if the index hasn't changed from the
            # last update
            return
        if self.mode.cubeview.gotoIndex(index, user=False):
            self.mode.update(refresh=False)

class BandSliderUpdates(HSIActionMixin, ToggleAction):
    """Refresh image during slider dragging"""
    name = "Refresh While Dragging Slider"
    default_menu = ("View", 209)

    def isChecked(self):
        return self.mode.immediate_slider_updates
    
    def action(self, index=-1, multiplier=1):
        self.mode.immediate_slider_updates = not self.mode.immediate_slider_updates


class ContrastFilterAction(HSIActionMixin, RadioAction):
    name = "Contrast"
    tooltip = "Contrast adjustment method"
    default_menu = ("View", -300)

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

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
            self.setContrast(mode)
            return
        mode.cubefilter = filt
        mode.update()

    def processMinibuffer(self, minibuffer, mode, percentage):
        assert self.dprint("returned percentage = %f" % percentage)
        filt = ContrastFilter(percentage)
        mode.cubefilter = filt
        mode.update()
        
    def setContrast(self, mode):
        minibuffer = FloatMinibuffer(mode, self, label="Contrast [0.0 - 1.0]")
        mode.setMinibuffer(minibuffer)
        
class MedianFilterAction(HSIActionMixin, RadioAction):
    name = "Median Filter"
    tooltip = "Median filter"
    default_menu = ("View", 301)

    items = ['No median',
             'Median 3x1 pixel', 'Median 1x3 pixel', 'Median 3x3 pixel',
             'Median 5x1 pixel', 'Median 1x5 pixel', 'Median 5x5 pixel']

    def isEnabled(self):
        return HAS_SCIPY

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, MedianFilter1D):
            return filt.pos
        return 0

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
        mode.update()

class ClippingFilterAction(HSIActionMixin, RadioAction):
    name = "Clipping Filter"
    tooltip = "Clip pixel values to limits"
    default_menu = ("View", 302)

    items = ['No Clipping',
             'Pixel > 0', '0 <= Pixel < 256', '0 <= Pixel < 1000',
             '0 <= Pixel < 10000',
             'User Defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, ClipFilter):
            return filt.pos
        return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        mode = self.mode
        filt = None
        if index == 0:
            filt = GeneralFilter(pos=0)
        elif index == 1:
            filt = ClipFilter(0, pos=index)
        elif index == 2:
            filt = ClipFilter(0, 256, pos=index)
        elif index == 3:
            filt = ClipFilter(0, 1000, pos=index)
        elif index == 4:
            filt = ClipFilter(0, 10000, pos=index)
        elif index == 5:
            minibuffer = IntRangeMinibuffer(self.mode, self,
                                            label="Enter clipping min, max:",
                                            initial = "%d, %d" % (0,1000))
            self.mode.setMinibuffer(minibuffer)
        if filt:
            mode.filter = filt
            mode.update()

    def processMinibuffer(self, minibuffer, mode, pair):
        dprint("Setting clipping to %s" % str(pair))
        filt = ClipFilter(pair[0], pair[1], pos=len(self.items) - 1)
        mode.filter = filt
        mode.update()

class SubtractBandAction(HSIActionMixin, MinibufferAction):
    name = "Band Subtraction Filter"
    tooltip = "Subtract a band from the rest of the bands"
    default_menu = ("View", 303)
    
    key_bindings = None
    minibuffer = IntMinibuffer
    minibuffer_label = "Subtract Band:"

    def processMinibuffer(self, minibuffer, mode, band_num):
        """
        Callback function used to set the stc to the correct line.
        """
        mode = self.mode
        band_num = mode.cubeview.getIndex(band_num, user=True)
        band = mode.cube.getBand(band_num)
        mode.filter = SubtractFilter(band)
        mode.update()


class SwapEndianAction(HSIActionMixin, ToggleAction):
    """Swap the endianness of the data"""
    name = "Swap Endian"
    default_menu = ("View", 309)

    def isChecked(self):
        return self.mode.swap_endian
    
    def action(self, index=-1, multiplier=1):
        self.mode.swap_endian = not self.mode.swap_endian
        self.mode.update()


class CubeViewAction(HSIActionMixin, RadioAction):
    name = "View Direction"
    default_menu = ("View", -600)

    items = [CubeView, FocalPlaneView]

    def getIndex(self):
        cls = self.mode.cubeview.__class__
        return self.items.index(cls)

    def getItems(self):
        return [c.name for c in self.items]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        cls = self.mode.cubeview.__class__
        current = self.items.index(cls)
        if current != index:
            self.mode.setViewer(self.items[index])
            self.mode.update()


class ShowPixelValues(HSIActionMixin, ToggleAction):
    name = "Show Pixel Values"
    default_menu = ("View", -900)

    def isChecked(self):
        return self.mode.show_value_at_cursor
    
    def action(self, index=-1, multiplier=1):
        self.mode.show_value_at_cursor = not self.mode.show_value_at_cursor


class TestSubset(HSIActionMixin, SelectAction):
    name = "Test HSI Spatial Subset"
    default_menu = ("&Help/Tests", 888)
    key_bindings = {'default': "C-T"}
    
    testcube = 1
    
    def getTempName(self):
        name = "dataset:test%d" % self.__class__.testcube
        self.__class__.testcube += 1
        return name
    
    def action(self, index=-1, multiplier=1):
        cube = self.mode.cube
        name = self.getTempName()
        fh = vfs.make_file(name)
        subcube = SubCube(cube)
        subcube.subset(0,cube.lines/2,0,cube.samples/2,0,cube.bands/2)
        fh.setCube(subcube)
        self.frame.open(name)


class SpatialSubset(HSIActionMixin, SelectAction):
    name = "Spatial Subset"
    default_menu = ("Edit", 800)
    
    testcube = 1
    
    def isEnabled(self):
        if self.mode.selector.__class__ == RubberBand:
            x, y, w, h = self.mode.selector.getSelectedBox()
            return w > 1 and h > 1
        return False
    
    def getTempName(self):
        name = "dataset:spatial_subset%d" % self.__class__.testcube
        self.__class__.testcube += 1
        return name
    
    def action(self, index=-1, multiplier=1):
        cube = self.mode.cube
        name = self.getTempName()
        fh = vfs.make_file(name)
        subcube = SubCube(cube)
        sample, line, ds, dl = self.mode.selector.getSelectedBox()
        subcube.subset(line, line+dl, sample, sample+ds, 0, cube.bands)
        fh.setCube(subcube)
        self.frame.open(name)


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
        self.cubeview = CubeView(None)
        self.cubefilter = BandFilter()
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
        for minor in self.wrapper.getActiveMinorModes():
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
        self.setStatusText("Building %dx%d bitmap..." % (self.cube.samples, self.cube.lines))
        self.cubeview.swapEndian(self.swap_endian)
        filter = self.filter
        self.cubeview.show(filter, self.cubefilter)
        self.setBitmap(self.cubeview.bitmap)
        self.frame.updateMenumap()
        if refresh:
            self.Update()
        self.updateInfo()
        self.idle_update_menu = True

    def getWelcomeMessage(self):
        return "%dx%dx%d %s image using %s loader" % (self.cube.samples, self.cube.lines, self.cube.bands, self.cube.interleave.upper(), self.dataset.getHandler().format_id)

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
        self.cubeview = viewcls(self.cube, self.classprefs.display_rgb)
        self.cubeview.swapEndian(self.swap_endian)
        for minor in self.wrapper.getActiveMinorModes():
            if hasattr(minor, 'proxies'):
                minor.setCube(self.cube)
                plotproxy = minor.proxies[0]
                plotproxy.setupAxes()

    def getPopupActions(self, evt, x, y):
        return [CubeViewAction, ShowPixelValues, BandSliderUpdates]
    
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


class ExportAsENVI(SelectAction):
    """Export the current datacube in ENVI BIL format
    """
    name = "as ENVI"
    default_menu = ("File/Export", -100)

    def action(self, index=-1, multiplier=1):
        filename = self.frame.showSaveAs("Save Image as ENVI",
                                         wildcard="BIL (*.bil)|*.bil|BIP (*.bip)|*.bip|BSQ (*.bsq)|*.bsq")
        if filename:
            root, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext in ['.bil', '.bip', '.bsq']:
                handler = HyperspectralFileFormat.getHandlerByName("ENVI")
                if handler:
                    try:
                        self.mode.showBusy(True)
                        self.mode.status_info.startProgress("Exporting to %s" % filename)
                        wx.GetApp().cooperativeYield()
                        handler.export(filename, self.mode.cube, progress=self.updateProgress)
                        self.mode.status_info.stopProgress("Saved %s" % filename)
                        wx.GetApp().cooperativeYield()
                    finally:
                        self.mode.showBusy(False)
                else:
                    self.mode.setStatusText("Can't find ENVI handler")
            else:
                self.frame.showErrorDialog("Unrecognized file format %s\n\nThe filename extension determines the\ninterleave format.  Use a filename extension of\n.bip, .bil, or .bsq" % filename)

    def updateProgress(self, value):
        self.mode.status_info.updateProgress(value)
        wx.GetApp().cooperativeYield()


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
            lo = lo / 2
            hi = lo * 3
        self.yaxis=(float(lo), float(hi))
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
