# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral image processing filters

This file is a repository of actions that operate on the HSI mode.
"""

import os, struct, mmap, math
from cStringIO import StringIO

import wx

from peppy.actions.minibuffer import *
from peppy.actions import *

from peppy.hsi.common import *
from peppy.hsi.subcube import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy


class RGBFilter(debugmixin):
    def __init__(self):
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

    def getGrayMapping(self,raw):
        return self.getGray(raw)

    def getRGB(self, lines, samples, planes):
        self.rgb = numpy.zeros((lines, samples, 3),numpy.uint8)
        assert self.dprint("shapes: rgb=%s planes=%s" % (self.rgb.shape, planes[0].shape))
        count = len(planes)
        if count > 0:
            for i in range(count):
                self.rgb[:,:,i] = self.getGrayMapping(planes[i])
            for i in range(count,3,1):
                self.rgb[:,:,i] = self.getGrayMapping(planes[0])
        #dprint(rgb[0,:,0])
        
        return self.rgb

class ContrastFilter(RGBFilter):
    def __init__(self, stretch=0.0):
        RGBFilter.__init__(self)
        self.contraststretch=stretch # percentage
        self.bins=256
   
    def setContrast(self,stretch):
        self.contraststretch=stretch

    def getGrayMapping(self,raw):
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
        scipy = scipy_module()
        if scipy:
            filtered = scipy.signal.medfilt2d(raw.astype(numpy.float32), self.kernel)
            return filtered
        return raw

class GaussianFilter(GeneralFilter):
    """Apply a gaussian filter to the band.

    A gaussian filter colvolves the image with a gaussian shape to blur the
    image
    """
    def __init__(self, radius=10, pos=0):
        GeneralFilter.__init__(self, pos=pos)

        # A gaussian is linearly independent, so the same filtering kernel is
        # used is both the X and Y directions
        # The full kernel size is the radius on either side of the pixel
        self.radius = radius
        self.diameter = (radius * 2)
        self.offset = self.diameter / 2.0
        self.stddev = 4.0
        self.kernel = numpy.array([self.gaussian(x) for x in range(0,self.diameter + 1)], numpy.float32)
        scale = numpy.sum(self.kernel)
        self.kernel /= scale
        self.dprint("scale=%f kernel=%s" % (scale, self.kernel))
   
    def gaussian(self, x):
        return 1.0/(math.sqrt(2*math.pi))/self.stddev * math.exp(-(math.pow(x-self.offset,2))/2.0/self.stddev/self.stddev)

    def getPlane(self,raw):
        """Compute the convolution using separable convolutions
        """
        filtered = numpy.zeros_like(raw)
        for line in range(raw.shape[0]):
            filtered[line,:] = numpy.convolve(raw[line,:], self.kernel, mode='same')
        for sample in range(raw.shape[1]):
            filtered[:, sample] = numpy.convolve(filtered[:,sample], self.kernel, mode='same')
        return filtered

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



class ContrastFilterAction(HSIActionMixin, RadioAction):
    name = "Contrast"
    tooltip = "Contrast adjustment method"
    default_menu = ("Filter", -300)

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.colorfilter
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
            filt = RGBFilter()
        elif index == 1:
            filt = ContrastFilter(0.1)
        elif index == 2:
            filt = ContrastFilter(0.2)
        else:
            self.setContrast(mode)
            return
        mode.colorfilter = filt
        mode.update()

    def processMinibuffer(self, minibuffer, mode, percentage):
        assert self.dprint("returned percentage = %f" % percentage)
        filt = ContrastFilter(percentage)
        mode.colorfilter = filt
        mode.update()
        
    def setContrast(self, mode):
        minibuffer = FloatMinibuffer(mode, self, label="Contrast [0.0 - 1.0]")
        mode.setMinibuffer(minibuffer)


class MedianFilterAction(HSIActionMixin, RadioAction):
    name = "Median Filter"
    tooltip = "Median filter"
    default_menu = ("Filter", 301)

    items = ['No median',
             'Median 3x1 pixel', 'Median 1x3 pixel', 'Median 3x3 pixel',
             'Median 5x1 pixel', 'Median 1x5 pixel', 'Median 5x5 pixel']

    def isEnabled(self):
        return bool(scipy_module())

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


class GaussianFilterAction(HSIActionMixin, RadioAction):
    """2D Gaussian blur filter
    
    """
    name = "Gaussian"
    default_menu = ("Filter", 305)

    items = ['No filter', '5 Pixel Kernel', '10 Pixel Kernel', 'User-defined']

    def getIndex(self):
        mode = self.mode
        filt = mode.filter
        assert self.dprint(filt)
        if isinstance(filt, GaussianFilter):
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
            filt = GaussianFilter(5, pos=index)
        elif index == 2:
            filt = GaussianFilter(10, pos=index)
        elif index == 3:
            minibuffer = IntMinibuffer(self.mode, self,
                                       label="Enter pixel radius:",
                                       initial = "10")
            self.mode.setMinibuffer(minibuffer)
        if filt:
            mode.filter = filt
            mode.update()

    def processMinibuffer(self, minibuffer, mode, value):
        dprint("Setting gaussian kernel to %s" % str(value))
        filt = GaussianFilter(value, pos=len(self.items) - 1)
        mode.filter = filt
        mode.update()


class ClippingFilterAction(HSIActionMixin, RadioAction):
    name = "Clipping Filter"
    tooltip = "Clip pixel values to limits"
    default_menu = ("Filter", -400)

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
    default_menu = ("Filter", -500)
    
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
