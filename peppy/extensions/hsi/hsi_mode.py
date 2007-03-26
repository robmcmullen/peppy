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
#import wx.lib.plot
import peppy.lib.plotter as plotter

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.controls import *

import HSI
try:
    import GDAL
except ImportError:
    has_gdal = False
import ENVI # FIXME: this one last as a temporary hack because if
            # there are multiple files with the same root name but
            # different extensions and there is an ENVI header, simply
            # finding the ".hdr" file means that it will determine
            # that it is an envi file

import numpy

addIconsFromDirectory(os.path.dirname(__file__))


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

        h=histogram(raw,minval,maxval+1,self.bins)
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
            h=histogram(gray,0,256,256)
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
        
        self.crosshair=None
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftButtonEvent)
        self.Bind(wx.EVT_LEFT_UP,   self.OnLeftButtonEvent)
        self.Bind(wx.EVT_MOTION,    self.OnLeftButtonEvent)
        
    def convertEventCoords(self, ev, fixbounds=True):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        x = ev.GetX() + (xView * xDelta)
        y = ev.GetY() + (yView * yDelta)
        if fixbounds:
            if x<0: x=0
            elif x>=self.width: x=self.width-1
            if y<0: y=0
            elif y>=self.height: y=self.height-1
        return (x, y)

    def isInBounds(self, x, y):
        if self.bmp is None or x<0 or y<0 or x>=self.width or y>=self.height:
            return False
        return True

    def drawCrossHair(self, dc, x, y):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        x -= (xView * xDelta)
        y -= (yView * yDelta)
        dc.DrawLine(x,0,x,self.height)
        dc.DrawLine(0,y,self.width,y)

    def OnPaintHook(self, dc):
        if self.crosshair:
            dc.SetPen(wx.Pen(wx.RED))
            dc.SetLogicalFunction(wx.XOR)
            self.drawCrossHair(dc,*self.crosshair)

    def OnLeftButtonEvent(self, ev):
        if ev.LeftDown() or ev.Dragging():
            coords=self.convertEventCoords(ev)
            # print "left mouse button event at (%d,%d)" % coords
            if self.bmp:
                # draw crosshair (note: in event coords, not converted coords)
                dc=wx.ClientDC(self)
                dc.SetPen(wx.Pen(wx.RED))
                dc.SetLogicalFunction(wx.XOR)
                if self.crosshair:
                    self.drawCrossHair(dc,*self.crosshair)
                self.crosshair=coords
                self.drawCrossHair(dc,*self.crosshair)

                wx.PostEvent(self, HSIUpdateEvent())
        # elif ev.LeftUp():
        #     pass

    def addUpdateUIEvent(self, callback):
        self.Bind(EVT_HSI_UPDATE, callback)


class HyperspectralSTC(NonResidentSTC):
    def openMmap(self):
        dprint("filename = %s" % self.filename)
        comp_mgr = ComponentManager()
        loader = HSI.Loader(comp_mgr)
        urlinfo = URLInfo(self.filename)
        header = loader.identify(urlinfo)
        dprint("header = '%s'" % header)
        if header:
            dprint("Loading %s format cube" % header.format_name)
            h = header(self.filename)
            self.cube=h.getCube(self.filename)
            print self.cube



class PrevBand(SelectAction):
    name = "Prev Band"
    tooltip = "Previous Band"
    icon = 'hsi-band-prev.png'
    keyboard = "C-P"
    
    def action(self, pos=None):
        print "Previous band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.prevBand()

class NextBand(SelectAction):
    name = "Next Band"
    tooltip = "Next Band"
    icon = 'hsi-band-next.png'
    keyboard = "C-N"
    
    def action(self, pos=None):
        print "Next band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.nextBand()

class PrevCube(SelectAction):
    name = "Prev Cube"
    tooltip = "Previous data cube in dataset"
    icon = 'hsi-cube-prev.png'

    def isEnabled(self):
        return False

class NextCube(SelectAction):
    name = "Next Cube"
    tooltip = "Next data cube in dataset"
    icon = 'hsi-cube-next.png'

    def isEnabled(self):
        return False



class HSIMode(MajorMode):
    """Major mode for hyperspectral image analysis.

    ...
    """
    keyword='HSI'
    icon='hsi-cube.png'

    mmap_stc_class = HyperspectralSTC

    default_settings = {
        'minor_modes': 'Spectrum,X Profile,Y Profile',
        }
    
    def createEditWindow(self,parent):
        """
        Create the bitmap viewer that is the main window of this major
        mode.

        @param parent: parent window in which to create this window 
        """
        self.cube = self.buffer.stc.cube
        self.bands = self.cube.guessDisplayBands()
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
        self.frame.SetStatusText("x=%d y=%d" % self.editwin.crosshair, 1)
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()
        
    def OnUpdateUIHook(self, evt):
        dprint()
        minors = self._mgr.GetAllPanes()
        for minor in minors:
            if minor.name != "main":
                plotproxy = minor.window.proxies[0]
                plotproxy.update(*self.editwin.crosshair)
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


class HSIPlotMinorMode(MinorMode):
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

        proxy = self.plot_proxy(self.major.cubeband)
        self.plot.setProxy(proxy)
        

        
class HSISpectrumMinorMode(HSIPlotMinorMode):
    """Display a spectrum at the current crosshair point.
    """
    keyword = "Spectrum"
    plot_proxy = plotter.SpectrumPlotProxy
        
class HSIXProfileMinorMode(HSIPlotMinorMode):
    """Display the X profile at the current crosshair line.
    """
    keyword="X Profile"
    plot_proxy = plotter.XProfilePlotProxy
        
class HSIYProfileMinorMode(HSIPlotMinorMode):
    """Display the Y profile at the current crosshair line.
    """
    keyword="Y Profile"
    plot_proxy = plotter.YProfilePlotProxy
        

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
        comp_mgr = ComponentManager()
        loader = HSI.Loader(comp_mgr)
        info = URLInfo(url)
        try:
            header = loader.identify(info)
            return MajorModeMatch(HSIMode, exact=True)
        except TypeError:
            pass
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
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

