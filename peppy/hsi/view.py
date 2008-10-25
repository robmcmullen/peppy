# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Hyperspectral bitmap viewers

These classes provide the means to generate the bitmap given the view direction
-- currently the view can be either looking at the typical image view looking
at samples x lines, or the focal plane view: looking at samples x bands.
"""

import os, struct, mmap
from cStringIO import StringIO

import wx
from wx.lib.pubsub import Publisher
from peppy.actions import *

from peppy.debug import *
from peppy.hsi.common import *

import numpy



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

    def __init__(self, mode, cube, display_rgb=True):
        self.mode = mode
        self.display_rgb = display_rgb
        self.cube = None
        self.setCube(cube)
    
    def setCube(self, cube):
        # list of tuples (band number, band) where band is an array as
        # returned from cube.getBand
        self.bands=[]
        
        # list of arrays containing filtered data, one step before turning into
        # RGB that can be displayed on the screen
        self.planes = []

        # Min/max for this group of bands only.  The cube's extrema is
        # held in cube.spectraextrema and is updated as more bands are
        # read in
        self.extrema=(0,1)

        # simple list of arrays, one array for each color plane r, g, b
        self.image = None
        self.contraststretch=0.0 # percentage

        self.initBitmap(cube)
        self.initDisplayIndexes()

    def initBitmap(self, cube=None, width=None, height=None):
        if cube:
            self.cube = cube
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
        self.image = wx.EmptyImage(self.width, self.height)

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
    
    def getWorkingMessage(self):
        return "Building %dx%d bitmap..." % (self.cube.samples, self.cube.lines)
    
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
    
    def getAvailableXAxisLabels(self):
        labels = ['band']
        if self.cube.wavelengths:
            labels.append(self.cube.wavelength_units)
        return labels
    
    def getDepthXAxisExtrema(self, label='band'):
        if self.cube.wavelengths and label == self.cube.wavelength_units:
            axis = (self.cube.wavelengths[0],
                    self.cube.wavelengths[-1])
        else:
            axis=(0,self.cube.bands)
        return axis

    def getDepthXAxis(self, label='band'):
        if self.cube.wavelengths and label == self.cube.wavelength_units:
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
        return u"Band %d%s" % (band_index + self.mode.classprefs.band_number_offset,
                               text)
    
    def getBandLegend(self, band_index):
        """Return the band name given the index"""
        return u"Band %d" % (band_index + self.mode.classprefs.band_number_offset)
    
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
            band = band - self.mode.classprefs.band_number_offset
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

    def setFilterOrder(self, filters):
        self.filters = filters[:]

    def processFilters(self, progress):
        """Process a chain of L{GeneralFilters} for each displayed band
        
        """
        self.planes = []
        for band in self.bands:
            assert self.dprint("getRGB: band=%s" % str(band))
            plane = band[1]
            for filt in self.filters:
                plane = filt.getPlane(plane)
            self.planes.append(plane)
            if progress: progress.Update(50+((count+1)*50)/len(self.bands))

    def getCurrentPlanes(self):
        return self.planes

    def show(self, colormapper, progress=None):
        if not self.cube: return

        try:
            # remove old image for memory management purposes
            del self.image
            self.image = None
            
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
            
            self.processFilters(progress)
            rgb = colormapper.getRGB(self.height, self.width, self.planes)
            
            # image uses the rgb data and doesn't create a new copy
            self.image = wx.ImageFromBuffer(self.width, self.height, rgb)
            # self.Refresh()
        except Exception, e:
            import traceback
            dprint(traceback.format_exc())
            Publisher().sendMessage('peppy.log.error', traceback.format_exc())
            
            # recreate empty image if necessary
            self.initBitmap()

    
    def saveImage(self,name):
        # convert to image so that save file can automatically
        # determine type from the filename.
        type=getImageType(name)
        assert self.dprint("saving image to %s with type=%d" % (name,type))
        return self.image.SaveFile(name,type)

    def copyImageToClipboard(self):
        bitmap = wx.BitmapFromImage(self.image)
        bmpdo = wx.BitmapDataObject(bitmap)
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

    def getWorkingMessage(self):
        return "Building %dx%d bitmap..." % (self.cube.samples, self.cube.bands)
    
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

    def getAvailableXAxisLabels(self):
        labels = ['line']
        return labels

    def getDepthXAxisExtrema(self, label='line'):
        return (0,self.cube.lines)

    def getDepthXAxis(self, label='line'):
        return numpy.arange(1, self.cube.lines+1, 1)

    def getDepthProfile(self, x, y):
        """Get the profile into the monitor at the given x,y position"""
        profile = self.cube.getFocalPlaneDepthInPlace(x, y)
        if self.swap:
            profile = profile.byteswap()
        return profile

    def getBandLegend(self, band_index):
        """Return the band name given the index"""
        return u"Frame %d" % (band_index + self.mode.classprefs.band_number_offset)


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
