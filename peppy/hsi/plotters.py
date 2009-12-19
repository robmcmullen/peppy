# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Plotting minor modes for HSI major mode

"""

import os, struct, mmap
from cStringIO import StringIO

import wx

from peppy.actions.minibuffer import *
from peppy.actions import *
from peppy.minor import *

from peppy.hsi.common import *

# hsi mode and the plotting utilities require numpy, the check for which is
# handled by the major mode wrapper
import numpy
import wx.lib.plot as plot
import peppy.lib.plotter as plotter


class HSIMinorModeMixin(MinorMode):
    @classmethod
    def worksWithMajorMode(self, modecls):
        return modecls.keyword == "HSI"
    
    def setCubeView(self, cubeview):
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

    def __init__(self, parent, **kwargs):
        MinorMode.__init__(self, parent, **kwargs)
        plotter.MultiPlotter.__init__(self, parent, statusbarframe=self.mode.frame)

        self.listeners=[]
        self.rgblookup=['red','green','blue']
        self.setProxy(self)
        self.last_coords = (0,0)
    
    def isPlottableView(self, cubeview):
        return True
    
    def setCubeView(self, cubeview):
        if self.isPlottableView(cubeview):
            self.getPaneInfo().Show(True)
        else:
            self.getPaneInfo().Show(False)
        self.mode.updateAui()
        self.setupTitle()
        self.setupAxes(cubeview)
        
    def setupTitle(self):
        self.title=self.keyword

    def setupAxes(self, cubeview):
        dprint("Here instead of subclass")
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
    
    def updateProxies(self, *coords):
        plotproxy = self.proxies[0]
        plotproxy.updateLines(*coords)
        try:
            plotproxy.updateListeners()
        except Exception, e:
            import traceback
            dprint(traceback.format_exc())
        self.last_coords = coords
    
    def redisplayProxies(self):
        self.updateProxies(*self.last_coords)


class SpectrumXLabelAction(HSIActionMixin, RadioAction):
    """Change the X axis label of the spectrum plot""" 
    name = "X Axis Label"

    def getIndex(self):
        cubeview = self.mode.cubeview
        labels = cubeview.getAvailableXAxisLabels()
        minor = self.popup_options['minor_mode']
        current = minor.xlabel
        return labels.index(current)

    def getItems(self):
        cubeview = self.mode.cubeview
        labels = cubeview.getAvailableXAxisLabels()
        return labels

    def action(self, index=-1, multiplier=1):
        assert self.dprint("index=%d" % index)
        cubeview = self.mode.cubeview
        labels = cubeview.getAvailableXAxisLabels()
        label = labels[index]
        minor = self.popup_options['minor_mode']
        minor.setupAxes(cubeview, label)
        minor.redisplayProxies()


class HSISpectrumMinorMode(HSIPlotMinorMode):
    """Display a spectrum at the current crosshair point.
    """
    keyword = "Depth Profile"

    def getPopupActions(self, evt, x, y):
        return [
            SpectrumXLabelAction,
            ]

    def isPlottableView(self, cubeview):
        return cubeview.isDepthPlottable()

    def setupAxes(self, cubeview, label=None):
        labels = cubeview.getAvailableXAxisLabels()
        if label:
            self.xlabel = label
        else:
            self.xlabel = labels[0]
        self.xaxis = cubeview.getDepthXAxisExtrema(self.xlabel)
        
        # syncing over the whole cube takes too long, so we'll grow
        # the axis as it gets bigger.  Start with the extrema of the
        # current band so we aren't too far off.
        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.mode.cubeview
        # dprint("SpectrumPlotProxy: (%d,%d)" % (x,y))
        profile = cubeview.getDepthProfile(x, y)
        num = len(profile)
        
        data=numpy.zeros((num, 2))
        data[:,0] = cubeview.getDepthXAxis(self.xlabel)
        data[:,1] = profile
        yaxis=cubeview.cube.getUpdatedExtrema()
        self.updateYAxis(yaxis)
        line = plot.PolyLine(data, legend= '%d, %d' % (x, y), colour='blue')
        return [line]
    

class HSIXProfileMinorMode(HSIPlotMinorMode):
    """Display the X profile at the current crosshair line.
    """
    keyword="Horizontal Profile"
    
    def isPlottableView(self, cubeview):
        return cubeview.isHorizontalProfilePlottable()

    def setupAxes(self, cubeview):
        self.xlabel = cubeview.xProfileXAxisLabel
        self.xaxis=(0,cubeview.width)

        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.mode.cubeview
        profiles=cubeview.getHorizontalProfiles(y)

        abscissas = numpy.arange(1,cubeview.width+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.width,2))
            data[:,0] = abscissas
            data[:,1] = self.mode.filter.getXProfile(y, values)
            #line=plot.PolyLine(data, legend= 'band #%d' % cubeview.bands[colorindex][0], colour=self.rgblookup[colorindex])
            line=plot.PolyLine(data, legend=cubeview.getBandLegend(cubeview.bands[colorindex][0]), colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        if self.mode.classprefs.use_cube_min_max:
            yaxis=cubeview.cube.getUpdatedExtrema()
            self.updateYAxis(yaxis)
        else:
            self.sizeYAxis(lines)
        return lines
        
class HSIYProfileMinorMode(HSIPlotMinorMode):
    """Display the Y profile at the current crosshair line.
    """
    keyword="Vertical Profile"
    
    def isPlottableView(self, cubeview):
        return cubeview.isVerticalProfilePlottable()

    def setupAxes(self, cubeview):
        self.xlabel = cubeview.yProfileXAxisLabel
        self.xaxis=(0, cubeview.height)

        self.ylabel='value'
        self.yaxis=(float(cubeview.extrema[0]), float(cubeview.extrema[1]))
        
    def getLines(self, x, y):
        cubeview = self.mode.cubeview
        profiles=cubeview.getVerticalProfiles(x)

        abscissas = numpy.arange(1,cubeview.height+1,1)
        colorindex=0
        lines=[]
        for values in profiles:
            data=numpy.zeros((cubeview.height,2))
            data[:,0] = abscissas
            data[:,1] = self.mode.filter.getYProfile(x, values)
            line=plot.PolyLine(data, legend=cubeview.getBandLegend(cubeview.bands[colorindex][0]), colour=self.rgblookup[colorindex])
            lines.append(line)
            colorindex+=1
        if self.mode.classprefs.use_cube_min_max:
            yaxis=cubeview.cube.getUpdatedExtrema()
            self.updateYAxis(yaxis)
        else:
            self.sizeYAxis(lines)
        return lines
