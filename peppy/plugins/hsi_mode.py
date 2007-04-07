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

from peppy.actions.minibuffer import FloatMinibuffer

import wx.lib.plot as plot
import peppy.lib.plotter as plotter

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.controls import *

from image_mode import ZoomIn, ZoomOut

from peppy.hsi import *

import numpy

class BandFilter(object):
    def __init__(self):
        self.planes=[]
        self.rgb=None
        
    def getGray(self,raw):
        minval=raw.min()
        maxval=raw.max()
        valrange=maxval-minval
        print "data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange))
        if valrange==0.0:
            gray=(raw-minval).astype(numpy.uint8)
        else:
            gray=((raw-minval)*(255.0/(maxval-minval))).astype(numpy.uint8)

        return gray

    def getPlane(self,raw):
        return self.getGray(raw)

    def getRGB(self,cubeband,progress=None):
        if not cubeband.cube: return None
        
        self.planes=[]

        count=0
        for band in cubeband.bands:
            print "getRGB: band=%s" % str(band)
            self.planes.append(self.getPlane(band[1]))
            if progress: progress.Update(50+((count+1)*50)/len(cubeband.bands))
            count+=1
        self.rgb=numpy.zeros((cubeband.cube.lines,cubeband.cube.samples,3),numpy.uint8)
        if count>0:
            for i in range(count):
                self.rgb[:,:,i]=self.planes[i]
            for i in range(count,3,1):
                self.rgb[:,:,i]=self.planes[0]
        #print rgb[0,:,0]
        
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
        print "data: min=%s max=%s range=%s" % (str(minval),str(maxval),str(valrange))

        h,bins=numpy.histogram(raw,self.bins,range=(minval,maxval+1))
        print h
        print "h[%d]=%d" % (self.bins-1,h[self.bins-1])
        #print h

        shape=raw.shape
        numpixels=raw.size
        lo=numpixels*self.contraststretch
        hi=numpixels*(1.0-self.contraststretch)
        print "lo=%d hi=%d" % (lo,hi)
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
        print "scaled: min=%d max=%d" % (minscaled,maxscaled)
        if minscaled==maxscaled:
            gray=numpy.zeros(raw.shape,numpy.uint8)
        else:
            gray=(raw-minscaled)*(255.0/(maxscaled-minscaled))
            # orig=(raw-minval)*(255.0/(maxval-minval))
            # print gray[0,:]
            # print orig[0,:]
            gray=numpy.clip(gray,0,255).astype(numpy.uint8)

            # histogram uses min <= val < max, so we need to use 256 as
            # the max
            h,bins = numpy.histogram(gray,256,range=(0,256))
            print "h[255]=%d" % h[255]
            # print h

        return gray


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

    def show(self,filter,bands=None,progress=None):
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
        
        self.rgb=filter.getRGB(self,progress)
        image=wx.ImageFromData(self.cube.samples,self.cube.lines,self.rgb.tostring())
        self.bitmap=wx.BitmapFromImage(image)
        # wx.StaticBitmap(self, -1, self.bitmap, (0,0), (self.cube.samples,self.cube.lines))
        # self.Refresh()
    
    def saveImage(self,name):
        # convert to image so that save file can automatically
        # determine type from the filename.
        image=wx.ImageFromBitmap(self.bitmap)
        type=getImageType(name)
        print "saving image to %s with type=%d" % (name,type)
        return image.SaveFile(name,type)

    def copyImageToClipboard(self):
        bmpdo = wx.BitmapDataObject(self.bitmap)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()
        

# This creates a new Event class and a EVT binder function
(HSIUpdateEvent, EVT_HSI_UPDATE) = wx.lib.newevent.NewEvent()

class CubeScroller(BitmapScroller):
    def __init__(self, parent, frame):
        BitmapScroller.__init__(self, parent)
        self.parent = parent
        self.frame = frame
        
    def OnPaintHook(self, evt, dc):
        if self.crosshair:
            dc.SetPen(wx.Pen(wx.RED, 1, wx.DOT))
            dc.SetLogicalFunction(wx.XOR)
##            dprint('x=%d, y=%d' % self.crosshair)
##            self.drawCrossHair(dc,*self.crosshair)

    def crosshairEventPostHook(self, ev=None):
        wx.PostEvent(self, HSIUpdateEvent())

    def addUpdateUIEvent(self, callback):
        self.Bind(EVT_HSI_UPDATE, callback)


class HyperspectralSTC(NonResidentSTC):
    def openMmap(self):
        dprint("filename = %s" % self.filename)
        urlinfo = URLInfo(self.filename)
        self.cube=HyperspectralFileFormat.load(urlinfo)


class SelectSubcube(ToggleAction):
    name = "Select Subcube"
    tooltip = "Select subcube spectrally."
    icon = 'icons/rectangular_select.png'
    
    def isChecked(self):
        mode = self.frame.getActiveMajorMode()
        return mode.editwin.getRubberBandState()

    def action(self, pos=None):
        print "Select mode!!!"
        mode = self.frame.getActiveMajorMode()
        mode.editwin.setRubberBand(not mode.editwin.getRubberBandState())

class PrevBand(SelectAction):
    name = "Prev Band"
    tooltip = "Previous Band"
    icon = 'icons/hsi-band-prev.png'
    keyboard = "C-P"
    
    def action(self, pos=None):
        print "Previous band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.prevBand()

class NextBand(SelectAction):
    name = "Next Band"
    tooltip = "Next Band"
    icon = 'icons/hsi-band-next.png'
    keyboard = "C-N"
    
    def action(self, pos=None):
        print "Next band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.nextBand()

class PrevCube(SelectAction):
    name = "Prev Cube"
    tooltip = "Previous data cube in dataset"
    icon = 'icons/hsi-cube-prev.png'

    def isEnabled(self):
        return False

class NextCube(SelectAction):
    name = "Next Cube"
    tooltip = "Next data cube in dataset"
    icon = 'icons/hsi-cube-next.png'

    def isEnabled(self):
        return False

class ContrastFilterAction(RadioAction):
    debuglevel = 1
    name = "Contrast"
    tooltip = "Contrast adjustment method"
    icon = 'icons/hsi-cube-next.png'

    items = ['No stretching', '1% Stretching', '2% Stretching', 'User-defined']

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)
        # do nothing here: it's actually changed in action

    def getIndex(self):
        mode = self.frame.getActiveMajorMode()
        filt = mode.cubefilter
        print filt
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

    def action(self, index=0, old=-1):
        assert self.dprint("index=%d" % index)
        mode = self.frame.getActiveMajorMode()
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

    def processMinibuffer(self, mode, percentage):
        dprint("returned percentage = %f" % percentage)
        filt = ContrastFilter(percentage)
        mode.cubefilter = filt
        wx.CallAfter(mode.update)
        
    def setContrast(self, mode):
        minibuffer = FloatMinibuffer(mode, self, label="Contrast [0.0 - 1.0]")
        mode.setMinibuffer(minibuffer)
        


class HSIMode(MajorMode):
    """Major mode for hyperspectral image analysis.

    ...
    """
    keyword='HSI'
    icon='icons/hsi-cube.png'

    mmap_stc_class = HyperspectralSTC

    default_settings = {
        'minor_modes': 'Spectrum,X Profile,Y Profile',
        'display_rgb': False,
        }
    
    def createEditWindow(self,parent):
        """
        Create the bitmap viewer that is the main window of this major
        mode.

        @param parent: parent window in which to create this window 
        """
        self.cube = self.buffer.stc.cube
        self.bands = self.cube.guessDisplayBands()
        if not self.settings.display_rgb and len(self.bands)>1:
            self.bands = [self.bands[0]]
        dprint("display bands = %s" % str(self.bands))
        self.cubeband = CubeBand(self.cube)
        self.cubefilter = BandFilter()
        win = CubeScroller(parent, self.frame)
        return win

    def createWindowPostHook(self):
        """
        Initialize the bitmap viewer with the image contained in the
        buffer.
        """
        self.cube.open()
        self.cubeband.loadBands(self.bands)
        self.cubeband.show(self.cubefilter, bands=self.bands)
        self.editwin.setBitmap(self.cubeband.bitmap)
        self.stc = self.buffer.stc

    def OnUpdateUI(self, evt):
        assert self.dprint("updating HSI user interface!")
        self.frame.SetStatusText("x=%d y=%d" % self.editwin.getCrosshairCoordsOnImage(), 1)
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()
        
    def OnUpdateUIHook(self, evt):
        minors = self._mgr.GetAllPanes()
        for minor in minors:
            if minor.name != "main":
                plotproxy = minor.window.proxies[0]
                plotproxy.update(*self.editwin.getCrosshairCoordsOnImage())
                plotproxy.updateListeners()

    def update(self):
        self.cubeband.show(self.cubefilter, bands=self.bands)
        self.editwin.setBitmap(self.cubeband.bitmap)
        self.editwin.Refresh()

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

    def setBand(self,newbands):
        display=True
        # greyscale image only needs the first array value, rgb image
        # uses all 3
        print "setBand: bands=%s" % newbands

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


class HSIPlotMinorMode(MinorMode, plotter.PlotProxy):
    """Abstract base class for x-y plot of cube data.

    This displays a plot using the plotter.MultiPlotter class.  The
    plot_proxy attribute specifies which type of plot proxy defined in
    the MultiPlotter class to use.  Also must specify a keyword that
    uniquely identifies the minor mode.
    """
    keyword = None
    default_settings={
        'best_width': 400,
        'best_height': 400,
        'min_width': 300,
        'min_height': 100,
        }
    plot_proxy = None

    def createWindows(self, parent):
        self.plot = plotter.MultiPlotter(parent, frame=self.major.frame)
        paneinfo = self.getDefaultPaneInfo(self.keyword)
        paneinfo.Right()
        self.major.addPane(self.plot, paneinfo)
        dprint(paneinfo)

        self.listeners=[]
        self.rgblookup=['red','green','blue']
        self.setupAxes()
        self.setupTitle()
        self.plot.setProxy(self)
        
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
        # print "SpectrumPlotProxy: (%d,%d)" % (x,y)

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
            # print "yaxis=%s" % self.yaxis
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
            # print "yaxis=%s" % self.yaxis
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
            # print "yaxis=%s" % self.yaxis
            self.updateListenerExtrema()
        return lines


class HSIPlugin(MajorModeMatcherBase,debugmixin):
    """HSI viewer plugin to register modes and user interface.
    """
    implements(IMajorModeMatcher)
    implements(IMinorModeProvider)
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    def possibleModes(self):
        yield HSIMode

    def scanFilename(self, url):
        info = URLInfo(url)
        format = HyperspectralFileFormat.identify(info)
        if format:
            dprint("found %s" % format)
            return MajorModeMatch(HSIMode, exact=True)
        return None
   
    def getMinorModes(self):
        for mode in [HSIXProfileMinorMode, HSIYProfileMinorMode, HSISpectrumMinorMode]:
            yield mode
    
    default_menu=(("HSI",None,Menu("Dataset").after("Major Mode")),
                  ("HSI","Dataset",MenuItem(PrevCube)),
                  ("HSI","Dataset",MenuItem(NextCube)),
                  ("HSI","Dataset",Separator("dataset")),
                  ("HSI","Dataset",MenuItem(PrevBand)),
                  ("HSI","Dataset",MenuItem(NextBand)),
                  ("HSI","Dataset",Separator("this dataset")),
                  ("HSI","Dataset",MenuItem(SelectSubcube)),
                  ("HSI","View",MenuItem(ContrastFilterAction).first()),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("HSI",None,Menu("Dataset").after("Major Mode")),
                   ("HSI","Dataset",MenuItem(PrevCube)),
                   ("HSI","Dataset",MenuItem(NextCube)),
                   ("HSI","Dataset",Separator("dataset")),
                   ("HSI","Dataset",MenuItem(PrevBand)),
                   ("HSI","Dataset",MenuItem(NextBand)),
                   ("HSI","Dataset",Separator("this dataset")),
                   ("HSI","Dataset",MenuItem(ZoomIn)),
                   ("HSI","Dataset",MenuItem(ZoomOut)),
                   ("HSI","Dataset",MenuItem(SelectSubcube)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

