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

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.bitmapscroller import *

from peppy.plugins.image_mode import ZoomIn, ZoomOut, RectangularSelect

from peppy.hsi import *

# hsi mode requires numpy, the check for which is handled by the major
# mode wrapper
import numpy

# plotting requires NumPy, so only import these if NumPy is
# around, otherwise the failure loading this module kills peppy.
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

    def getRGB(self, cubeband, filt, progress=None):
        if not cubeband.cube: return None
        
        self.planes=[]

        count=0
        for band in cubeband.bands:
            dprint("getRGB: band=%s" % str(band))
            self.planes.append(self.getPlane(filt.getPlane(band[1])))
            if progress: progress.Update(50+((count+1)*50)/len(cubeband.bands))
            count+=1
        self.rgb=numpy.zeros((cubeband.cube.lines,cubeband.cube.samples,3),numpy.uint8)
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

class CubeBand(object):
    def __init__(self, cube):
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

        self.cube=cube
        if self.cube:
            self.width=cube.samples
            self.height=cube.lines
        else:
            self.width=128
            self.height=128

        # Delay loading real bitmap till requested.  Make an empty one
        # for now.
        self.bitmap=wx.EmptyBitmap(self.width,self.height)
            
       
    def loadBands(self,bands,progress=None):
        if not self.cube: return

        self.bands=[]
        count=0
        if isinstance(bands,tuple) or isinstance(bands,list):
            emin=None
            emax=None
            for i in bands:
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
            
        elif isinstance(bands,int):
            raw=self.cube.getBandInPlace(bands)
            minval=raw.min()
            maxval=raw.max()
            self.bands.append((bands,raw,minval,maxval))
            if progress: progress.Update(100)
            self.extrema=(minval,maxval)

    # Get a list of horizontal profiles at the given line number
    def getHorizontalProfiles(self,line):
        if not self.cube: return

        profiles=[]
        for band in self.bands:
            profile=band[1][line,:]
            profiles.append(profile)
        return profiles

    def getVerticalProfiles(self,sample):
        if not self.cube: return

        profiles=[]
        for band in self.bands:
            profile=band[1][:,sample]
            profiles.append(profile)
        return profiles

    def show(self, prefilter, colorfilter, bands=None,progress=None):
        if not self.cube: return

        refresh=False
        if bands:
            if len(bands)!=len(self.bands):
                refresh=True
            else:
                for i in range(len(bands)):
                    if bands[i]!=self.bands[i][0]:
                        refresh=True
                        break
        
        if refresh or not self.bands:
            self.loadBands(bands)
        
        self.rgb=colorfilter.getRGB(self, prefilter, progress)
        image=wx.ImageFromData(self.cube.samples,self.cube.lines,self.rgb.tostring())
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
        

class CubeScroller(BitmapScroller):
    def __init__(self, parent, frame):
        BitmapScroller.__init__(self, parent)
        self.parent = parent
        self.frame = frame

    def addUpdateUIEvent(self, callback):
        self.Bind(EVT_CROSSHAIR_MOTION, callback)


class HyperspectralSTC(NonResidentSTC):
    def open(self, url, message=None):
        self.dataset=HyperspectralFileFormat.load(url)
        
    def Destroy(self):
        self.dataset = None


class SpatialSelect(RectangularSelect):
    name = _("Spatial Select")
    tooltip = _("Select subcube spatially.")
    
    
class BandEnabledMixin(object):
    def isEnabled(self):
        mode = self.mode
        for band in mode.bands:
            # check if any of the display bands is at the low limit
            if band < 1:
                return False
        # nope, still room to decrement all bands
        return True

class BandAction(BandEnabledMixin, SelectAction):
    pass

class PrevBand(BandAction):
    name = _("Prev Band")
    tooltip = _("Previous Band")
    icon = 'icons/hsi-band-prev.png'
    keyboard = "C-P"
    
    def action(self, index=-1, multiplier=1):
        dprint("Previous band!!!")
        mode = self.mode
        mode.prevBand()

class NextBand(BandAction):
    name = _("Next Band")
    tooltip = _("Next Band")
    icon = 'icons/hsi-band-next.png'
    keyboard = "C-N"
    
    def action(self, index=-1, multiplier=1):
        dprint("Next band!!!")
        mode = self.mode
        mode.nextBand()

class GotoBand(BandEnabledMixin, MinibufferAction):
    name = _("Goto Band")
    tooltip = _("Go to a particular band in the cube")
    
    key_bindings = {'default': 'M-G',}
    minibuffer = IntMinibuffer
    minibuffer_label = _("Goto Band:")

    def processMinibuffer(self, minibuffer, mode, band):
        """
        Callback function used to set the stc to the correct line.
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        #dprint("goto line = %d" % line)
        mode.gotoBand(band)

class CubeAction(SelectAction):
    def isEnabled(self):
        mode = self.mode
        index = mode.dataset_index
        num = mode.dataset.getNumCubes()
        if index>0:
            return True
        return False

class PrevCube(CubeAction):
    name = _("Prev Cube")
    tooltip = _("Previous data cube in dataset")
    icon = 'icons/hsi-cube-prev.png'

    def action(self, index=-1, multiplier=1):
        dprint("Prev cube!!!")
        mode = self.mode
        mode.prevCube()

class NextCube(CubeAction):
    name = _("Next Cube")
    tooltip = _("Next data cube in dataset")
    icon = 'icons/hsi-cube-next.png'

    def action(self, index=-1, multiplier=1):
        dprint("Next cube!!!")
        mode = self.mode
        mode.nextCube()

class SelectCube(RadioAction):
    debuglevel = 1
    name = _("Select Cube")
    tooltip = _("Select a cube from the dataset")
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
        
class ContrastFilterAction(RadioAction):
    debuglevel = 1
    name = _("Contrast")
    tooltip = _("Contrast adjustment method")
    icon = 'icons/hsi-cube-next.png'

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)
        # do nothing here: it's actually changed in action

    def getIndex(self):
        mode = self.mode
        filt = mode.cubefilter
        dprint(filt)
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
        
class MedianFilterAction(RadioAction):
    debuglevel = 1
    name = _("Median Filter")
    tooltip = _("Median filter")
    icon = 'icons/hsi-cube-next.png'

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
        


class HSIMode(MajorMode):
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

    @classmethod
    def attemptOpen(cls, url):
        format = HyperspectralFileFormat.identify(url)
        if format:
            dprint("found %s" % format)
            return True
        return False
    
    def createEditWindow(self,parent):
        """
        Create the bitmap viewer that is the main window of this major
        mode.

        @param parent: parent window in which to create this window 
        """
        self.dataset = self.buffer.stc.dataset
        self.setCube(0)
        win = CubeScroller(parent, self.frame)
        return win

    def createWindowPostHook(self):
        """
        Initialize the bitmap viewer with the image contained in the
        buffer.
        """
        self.update(False) # initial case will refresh automatically
        self.stc = self.buffer.stc

    def OnUpdateUI(self, evt):
        assert self.dprint("updating HSI user interface!")
        self.frame.SetStatusText("x=%d y=%d" % evt.imageCoords, 1)
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()
        
    def OnUpdateUIHook(self, evt):
        for minor in self.minors:
            if hasattr(minor, 'proxies'):
                plotproxy = minor.proxies[0]
                plotproxy.updateLines(*evt.imageCoords)
                plotproxy.updateListeners()

    def update(self, refresh=True):
        self.cubeband.show(self.filter, self.cubefilter, bands=self.bands)
        self.editwin.setBitmap(self.cubeband.bitmap)
        if refresh:
            self.editwin.Refresh()
        self.idle_update_menu = True

    def setCube(self, index=0):
        self.dataset_index = index
        self.cube = self.dataset.getCube(index=index)
        self.bands = self.cube.guessDisplayBands()
        if not self.classprefs.display_rgb and len(self.bands)>1:
            self.bands = [self.bands[0]]
        dprint("display bands = %s" % str(self.bands))
        self.cubeband = CubeBand(self.cube)
        self.cubefilter = BandFilter()
        self.filter = GeneralFilter()
        #self.cube.open()
        dprint(self.cube)
        self.cubeband.loadBands(self.bands)

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

    def nextBand(self):
        newbands=[]
        for i in range(len(self.bands)):
            newbands.append(self.bands[i]+1)
        return self.setBand(newbands)

    def prevBand(self):
        newbands=[]
        for i in range(len(self.bands)):
            newbands.append(self.bands[i]-1)
        return self.setBand(newbands)

    def gotoBand(self, band):
        newbands=[band]
        return self.setBand(newbands)

    def setBand(self,newbands):
        display=True
        # greyscale image only needs the first array value, rgb image
        # uses all 3
        dprint("setBand: bands=%s" % newbands)

        # first check the range
        for i in range(len(self.bands)):
            if newbands[i]<0 or newbands[i]>=self.cube.bands:
                display=False
                break

        # if all bands are in range, change the settings and display
        if display:
            for i in range(len(self.bands)):
                self.bands[i]=newbands[i]
            self.update()
        return display


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
    
class HSISpectrumMinorMode(HSIPlotMinorMode):
    """Display a spectrum at the current crosshair point.
    """
    keyword = "Spectrum"

    def setupAxes(self):
        cubeband = self.major.cubeband
        if cubeband.cube.wavelengths:
            self.xlabel = cubeband.cube.wavelength_units
            self.xaxis = (cubeband.cube.wavelengths[0],
                          cubeband.cube.wavelengths[-1])
        else:
            self.xlabel='band'
            self.xaxis=(0,cubeband.cube.bands)
        
        # syncing over the whole cube takes too long, so we'll grow
        # the axis as it gets bigger.  Start with the extrema of the
        # current band so we aren't too far off.
        self.ylabel='value'
        self.yaxis=cubeband.extrema
        
    def getLines(self, x, y):
        cubeband = self.major.cubeband
        # dprint("SpectrumPlotProxy: (%d,%d)" % (x,y))

        data=numpy.zeros((cubeband.cube.bands,2))
        if cubeband.cube.wavelengths:
            data[:,0]=cubeband.cube.wavelengths
        else:
            data[:,0]=numpy.arange(1,cubeband.cube.bands+1,1)
        data[:,1] = cubeband.cube.getSpectra(y,x)
        yaxis=cubeband.cube.getUpdatedExtrema()
        if yaxis != self.yaxis:
            # make copy of list.  The list returned by
            # getUpdatedExtrema is modified in place, so the compare
            # will always return true if we don't copy it.
            self.yaxis=yaxis[:]
            # dprint("yaxis=%s" % self.yaxis)
            self.updateListenerExtrema()
        line = plot.PolyLine(data, legend= '%d, %d' % (x, y), colour='blue')
        return [line]
    

        
class HSIXProfileMinorMode(HSIPlotMinorMode):
    """Display the X profile at the current crosshair line.
    """
    keyword="X Profile"
    
    def setupAxes(self):
        cubeband = self.major.cubeband

        self.xlabel='sample'
        self.xaxis=(0,cubeband.cube.samples)

        self.ylabel='value'
        self.yaxis=cubeband.extrema
        
    def getLines(self, x, y):
        cubeband = self.major.cubeband
        profiles=cubeband.getHorizontalProfiles(y)

        x=numpy.arange(1,cubeband.cube.samples+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeband.cube.samples,2))
            data[:,0]=x
            data[:,1]=values
            line=plot.PolyLine(data, legend= 'band #%d' % cubeband.bands[colorindex][0], colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        yaxis=cubeband.cube.getUpdatedExtrema()
        if yaxis != self.yaxis:
            # make copy of list.  The list returned by
            # getUpdatedExtrema is modified in place, so the compare
            # will always return true if we don't copy it.
            self.yaxis=yaxis[:]
            # dprint("yaxis=%s" % self.yaxis)
            self.updateListenerExtrema()
        return lines
        
class HSIYProfileMinorMode(HSIPlotMinorMode):
    """Display the Y profile at the current crosshair line.
    """
    keyword="Y Profile"
    
    def setupAxes(self):
        cubeband = self.major.cubeband

        self.xlabel='line'
        self.xaxis=(0,cubeband.cube.lines)

        self.ylabel='value'
        self.yaxis=cubeband.extrema
        
    def getLines(self, x, y):
        cubeband = self.major.cubeband
        profiles=cubeband.getVerticalProfiles(x)

        x=numpy.arange(1,cubeband.cube.lines+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeband.cube.lines,2))
            data[:,0]=x
            data[:,1]=values
            line=plot.PolyLine(data, legend= 'band #%d' % cubeband.bands[colorindex][0], colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        yaxis=cubeband.cube.getUpdatedExtrema()
        if yaxis != self.yaxis:
            # make copy of list.  The list returned by
            # getUpdatedExtrema is modified in place, so the compare
            # will always return true if we don't copy it.
            self.yaxis=yaxis[:]
            # dprint("yaxis=%s" % self.yaxis)
            self.updateListenerExtrema()
        return lines


class HSIPlugin(IPeppyPlugin):
    """HSI viewer plugin to register modes and user interface.
    """

    def getMajorModes(self):
        yield HSIMode

    def getMinorModes(self):
        for mode in [HSIXProfileMinorMode, HSIYProfileMinorMode, HSISpectrumMinorMode]:
            yield mode
    
    default_menu=(("HSI",None,Menu(_("Dataset")).after("Major Mode")),
                  ("HSI",_("Dataset"),MenuItem(PrevCube)),
                  ("HSI",_("Dataset"),MenuItem(NextCube)),
                  ("HSI",_("Dataset"),MenuItem(SelectCube)),
                  ("HSI",_("Dataset"),Separator("dataset")),
                  ("HSI",_("Dataset"),MenuItem(PrevBand)),
                  ("HSI",_("Dataset"),MenuItem(NextBand)),
                  ("HSI",_("Dataset"),MenuItem(GotoBand)),
                  ("HSI",_("Dataset"),Separator("this dataset")),
                  ("HSI",_("Dataset"),MenuItem(SpatialSelect)),
                  ("HSI",_("View"),MenuItem(ContrastFilterAction)),
                  ("HSI",_("View"),MenuItem(MedianFilterAction)),
                  ("HSI",_("View"),Separator("after filters")),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("HSI",None,Menu(_("Dataset")).after("Major Mode")),
                   ("HSI",_("Dataset"),MenuItem(PrevCube)),
                   ("HSI",_("Dataset"),MenuItem(NextCube)),
                   ("HSI",_("Dataset"),Separator("dataset")),
                   ("HSI",_("Dataset"),MenuItem(PrevBand)),
                   ("HSI",_("Dataset"),MenuItem(NextBand)),
                   ("HSI",_("Dataset"),Separator("this dataset")),
                   ("HSI",_("Dataset"),MenuItem(ZoomOut)),
                   ("HSI",_("Dataset"),MenuItem(ZoomIn)),
                   ("HSI",_("Dataset"),MenuItem(SpatialSelect)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

