# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral image processing filters

This file is a repository of actions that operate on the HSI mode.
"""

import os, struct, mmap, math
from cStringIO import StringIO

from peppy.hsi.common import *
from peppy.hsi.subcube import *
import peppy.hsi.colors as colors

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy


class RGBMapper(debugmixin):
    def scaleChunk(self, raw, minval, maxval, u1, u2, v1, v2, output):
        assert self.dprint("processing chunk [%d:%d, %d:%d]" % (u1, u2, v1, v2))
        if minval == maxval:
            output[u1:u2, v1:v2] = (raw[u1:u2, v1:v2] - minval).astype(numpy.uint8)
        else:
            #gray=((raw-minval)*(255.0/(maxval-minval))).astype(numpy.uint8)
            temp1 = raw[u1:u2, v1:v2] - minval
            temp2 = temp1 * (255.0/(maxval-minval))
            output[u1:u2, v1:v2] = temp2.astype(numpy.uint8)

    def getGray(self, raw, tile_size=256):
        minval=raw.min()
        maxval=raw.max()
        valrange=maxval-minval
        assert self.dprint("data: min=%s max=%s range=%s len(raw)=%d" % (str(minval),str(maxval),str(valrange), raw.size))
        gray = numpy.empty(raw.shape, dtype=numpy.uint8)
        v1 = 0
        v2 = raw.shape[1]
        u1 = 0
        assert self.dprint("raw size: %s" % (str(raw.shape)))
        while u1 < raw.shape[0]:
            u2 = u1 + tile_size
            if u2 > raw.shape[0]:
                u2 = raw.shape[0]
            self.scaleChunk(raw, minval, maxval, u1, u2, v1, v2, gray)
            u1 = u2

        return gray

    def getGrayMapping(self,raw):
        return self.getGray(raw)

    def getRGB(self, lines, samples, planes):
        rgb = numpy.zeros((lines, samples, 3),numpy.uint8)
        assert self.dprint("shapes: rgb=%s planes=%s" % (rgb.shape, planes[0].shape))
        count = len(planes)
        if count > 0:
            for i in range(count):
                rgb[:,:,i] = self.getGrayMapping(planes[i])
            for i in range(count,3,1):
                rgb[:,:,i] = rgb[:,:,0]
        #dprint(rgb[0,:,0])
        
        return rgb

class PaletteMapper(RGBMapper):
    def __init__(self, name=None):
        self.colormap_name = name
        if name:
            self.colormap = colors.getColormap(name)
        else:
            self.colormap = None
        
    def getRGB(self, lines, samples, planes):
        # This is designed for grayscale images only; if there is more than one
        # plane, the standard RGB method is used
        count = len(planes)
        if count > 1 or self.colormap is None:
            return RGBMapper.getRGB(lines, samples, planes)
        
        if count > 0:
            gray = self.getGrayMapping(planes[0])
            
            # Matplotlib returns alpha values in the colormap, so we only need
            # the first 3 bands
            rgba = self.colormap(gray, bytes=True)
            rgb = numpy.zeros((lines, samples, 3),numpy.uint8)
            for i in range(3):
                rgb[:,:,i] = rgba[:,:,i]
            #rgb = rgba[:,:,0:3]
        else:
            # blank image
            rgb = numpy.zeros((lines, samples, 3),numpy.uint8)
        assert self.dprint("shape: rgb=%s" % str(rgb.shape))
        return rgb


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


class ContrastFilter(GeneralFilter):
    def __init__(self, stretch=0.0):
        GeneralFilter.__init__(self)
        self.contraststretch = stretch # percentage
        self.bins = 256
   
    def setContrast(self,stretch):
        self.contraststretch = stretch

    def getPlane(self, raw):
        if self.contraststretch <= 0.0:
            return raw
        
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
        filtered = numpy.clip(raw, minscaled, maxscaled)
        return filtered


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
