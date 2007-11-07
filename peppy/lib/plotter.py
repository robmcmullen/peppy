#-----------------------------------------------------------------------------
# Name:        plotter.py
# Purpose:     Plotting utilities on top of wx.lib.plot
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Plotting utilities on top of wx.lib.plot
"""

import os,sys,re,random

import wx
import wx.lib.plot as plot

import numpy

try:
    from peppy.debug import *
except:
    # stubs so things that use peppy.debug can operate without peppy
    def dprint(txt=""):
        #print txt
        return True

    class debugmixin(object):
        def dprint(self, txt):
            #print txt
            return True


class PlotProxy(object):
    """Proxy object that represents a bunch of lines to be plotted in
    a MultiPlotter.
    """
    def __init__(self):
        self.title='title'
        self.xlabel='xlabel'
        self.ylabel='ylabel'
        self.xaxis=[0,100]
        self.yaxis=[0,100]

        self.lines=[]

        # listeners are MultiPlotters that are looking at this data
        self.listeners=[]

    def getLines(self, *args):
        """Users should override this to return a list of
        plot.Polyline instances that represent the data to be plotted.

        The x and y values are optional and are dependent on the user
        application to have passed them in through updateLines.
        """
        return []

    def updateLines(self, *args):
        """Called by other objects to reset the internal state of the
        PlotProxy.

        Coordinates x and y can optionally be specified in case the
        user proxy needs to do something on a user click of those
        coordinates.
        """
        # dprint("PlotProxy: update (%d,%d)" % (x,y))
        self.lines=self.getLines(*args)

    def addListener(self, plotter):
        """Add a MultiPlotter as a listener.

        It's possible that more than one MultiPlotter will be
        interested in the same data.  This keeps track of which
        plotter is interested and updates them when the data changes.
        """
        self.listeners.append(plotter)
        # dprint("%s: listeners=%s" % (__name__,self.listeners))

    def getListeners(self):
        """Returns the list of MultiPlotter listeners"""
        return self.listeners
    
    def updateListeners(self,skip=[]):
        """Force any listeners to update their plots"""
        for listener in self.listeners:
            if listener in skip:
                # dprint("skipping listener: %s" % str(listener))
                continue
            else:
                # dprint("updating listener: %s" % str(listener))
                # dprint("  shown: %s" % listener.IsShown())
                listener.update()

    def updateListenerExtrema(self):
        """Update the extrema of any listeners"""
        for listener in self.listeners:
            listener.updateExtrema()


class MultiPlotter(plot.PlotCanvas, debugmixin):
    """Plot control that can handle multiple PlotProxy objects
    """
    
    def __init__(self, parent, id=-1, proxy=None, grid=True, legend=True, fullscale=True, statusbarframe=None):
        plot.PlotCanvas.__init__(self, parent, id)

        self.proxies=[]
        self.setProxy(proxy)
        self.graph=None
        self.xfullscale=fullscale
        self.yfullscale=fullscale
        self.xaxis=None
        self.yaxis=None
        self._gridEnabled=grid
        self._legendEnabled=legend
        self._titleEnabled=False
        self._snapToValues=True
        self._gridColour=wx.Colour(150,150,150)

        if statusbarframe is not None:
            self._statusbarframe = statusbarframe
        elif hasattr(parent, 'SetStatusText'):
            self._statusbarframe = parent
            
        self.SetPointLabelFunc(self.drawPointLabel)
        # self.SetEnablePointLabel(True)
        self.last_PointLabel = None

    def setup(self):
        self.xaxis=self.getXAxis()
        self.yaxis=self.getYAxis()

    def resetDefaults(self):
        """Just to reset the fonts back to the PlotCanvas defaults"""
        self.SetFont(wx.Font(10,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_NORMAL))
        self.SetFontSizeAxis(10)
        self.SetFontSizeLegend(7)
        self.SetXSpec('auto')
        self.SetYSpec('auto')

    def setProxy(self, proxy, clear=True):
        """Adds the PlotProxy, clearing the previous list of proxies
        by default.

        Unless clear is False, this will reset the list of proxies to
        only contain the specified PlotProxy object.
        """
        if clear:
            # FIXME: remove self from existing proxy listeners
            self.proxies=[]
        self.addProxy(proxy)

    def addProxy(self, proxy):
        """Add the PlotProxy to the current list of proxies.
        """
        if proxy is not None:
            if type(proxy) in [list,tuple]:
                for p in proxy:
                    self.proxies.append(p)
                    p.addListener(self)
            else:
                self.proxies.append(proxy)
                proxy.addListener(self)
            self.setup()

    def getExtrema(self,extrema):
        """From a list of (min,max) pairs, return the overall min and
        max from the list.
        """
        lo=min([a for a,b in extrema])
        hi=max([b for a,b in extrema])
        # dprint("extrema: (%d,%d)" % (lo,hi))
        return (lo,hi)

    def getXAxis(self):
        if self.xfullscale:
            extrema=[proxy.xaxis for proxy in self.proxies]
            axis=self.getExtrema(extrema)
        else:
            axis=None
        return axis

    def getYAxis(self):
        if self.yfullscale:
            extrema=[proxy.yaxis for proxy in self.proxies]
            axis=self.getExtrema(extrema)
        else:
            axis=None
        return axis

    def setYAxis(self,values):
        self.yfullscale=False
        self.yaxis=values

    def updateExtrema(self):
        self.xaxis=self.getXAxis()
        self.yaxis=self.getYAxis()

    def update(self):
        """Force the control to recreate its list of lines and redraw
        itself.
        """
        #dprint("Found %d proxies" % len(self.proxies))
        if len(self.proxies)==0: return
        
        lines=[]
        for proxy in self.proxies:
            lines.extend(proxy.lines)

        first=self.proxies[0]
        self.graph=plot.PlotGraphics(lines, first.title,
                                     first.xlabel, first.ylabel)
        self.show()
        

    def show(self):
        self.resetDefaults()
        if self.graph:
            self.Draw(self.graph,self.xaxis,self.yaxis)

    def findNearest(self, x, y):
        """Find the nearest point to the cursor.

        Instead of using a euclidian distance calculation, use a
        faster method by first limiting the points to those closest to
        the cursor in the x direction.  Then, chose the one closest in
        the y direction.
        """
        # first, find closest point in each line to the x coordinate
        nearlist=[]
        graphics, xAxis, yAxis= self.last_draw
        for curveNum,o in enumerate(graphics):
            shape=o.points.shape
            dx=abs(x-o.points[0,0])
            index=0
            line=o
            for i in range(1,shape[0]):
                newdx=abs(x-o.points[i,0])
                # dprint("index=%d dx=%.4f newdx=%.4f" % (i,dx,newdx))
                if newdx<dx:
                    index=i
                    line=o
                    dx=newdx
            nearlist.append({'line':line,'index':index,'dx':dx,'legend':o.getLegend()})

        # now that we have a list of best matches from each line in
        # terms of the x coordinate, check each line's y distance to
        # find the nearest.
        if len(nearlist)>1:
            nearest=nearlist[0]
            dy=abs(y-nearest['line'].points[nearest['index'],1])
            # dprint("checking line #0: index=%d dy=%.4f" % (near['index'],dy))
            for i in range(1,len(nearlist)):
                newnear=nearlist[i]
                newdy=abs(y-newnear['line'].points[newnear['index'],1])
                # dprint("checking line #%d: index=%d dy=%.4f" % (i,newnear['index'],newdy))
                if newdy<dy:
                    nearest=newnear
                    dy=newdy
                    # dprint("  line #%d is closer" % (index))
                    
            # dprint("best match: index=%d dx=%.4f dy=%.4f" % (near['index'],near['dx'],dy))
        else:
            nearest=nearlist[0]
        nearest['pointXY']=(nearest['line'].points[nearest['index'],0],
                            nearest['line'].points[nearest['index'],1])
        (x,y)=self.PositionUserToScreen(nearest['pointXY'])
        # dprint(x,y)
        nearest['scaledXY']=(x,y)

            
        return nearest

    def OnMotion(self, evt):
        """Show the crosshair if the left button is down."""
        
        if self._snapToValues and evt.LeftIsDown():
            x,y=self.GetXY(evt)
            nearest=self.findNearest(x,y)
            self.UpdatePointLabel(nearest)
        plot.PlotCanvas.OnMotion(self, evt)

    def OnMouseLeftDown(self, evt):
        """Start the crosshair display on left button press."""
        if self._snapToValues:
            x,y=self.GetXY(evt)
            nearest=self.findNearest(x,y)
            self.UpdatePointLabel(nearest)
        plot.PlotCanvas.OnMouseLeftDown(self, evt)

    def OnMouseLeftUp(self, evt):
        """Stop the crosshair display"""
        if self._snapToValues:
            self.OnLeave(evt)
        plot.PlotCanvas.OnMouseLeftDown(self, evt)

    def drawPointLabel(self, dc, nearest):
        ptx, pty = nearest["scaledXY"] #scaled x,y of closest point
        #dprint("drawing value at (%d,%d)" % (ptx,pty))

        # FIXME: what to do when we are zoomed and the point is out of
        # the viewing area?  Currently, we aren't clipping so points
        # off the axis are still highlighted
        dc.SetPen(wx.Pen(wx.BLACK))
        dc.SetBrush(wx.Brush( wx.WHITE, wx.TRANSPARENT ) )
        dc.SetLogicalFunction(wx.INVERT)
        dc.CrossHair(ptx,pty)
        dc.DrawRectangle( ptx-3,pty-3,7,7)
        dc.SetLogicalFunction(wx.COPY)
        
        x,y = nearest["pointXY"] # data values
        if self._statusbarframe:
            self._statusbarframe.SetStatusText("%s: x = %.4f, y = %.4f" % (nearest['legend'],x,y))


if __name__ == "__main__":
    class TestPlotProxy(PlotProxy):
        def __init__(self, legend):
            PlotProxy.__init__(self)
            self.legend = legend
            self.title='Test'
            self.xlabel='x'
            self.ylabel='y'
            self.xaxis=(0,500)
            self.yaxis=(0,500)

        def getLines(self, x, y):
            # dprint("TestPlotProxy: (%d,%d)" % (x,y))
            data=numpy.zeros((500,2))
            data[:,0]=numpy.arange(500)
            y = range(500)
            random.shuffle(y)
            data[:,1]=numpy.array(y)
            line = plot.PolyLine(data, legend=self.legend, colour='orange')
            return [line]

    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='MultiPlotter and PlotProxy Test', size=(500,500))
    frame.CreateStatusBar()
    sizer = wx.BoxSizer(wx.VERTICAL)
    
    # Add a static multiplotter
    staticplot = MultiPlotter(frame)
    sizer.Add(staticplot,  1, wx.EXPAND | wx.ALL, 5)

    # Add some proxies
    t1 = TestPlotProxy('static')
    staticplot.addProxy(t1)
    t1.updateLines(0,0)
    staticplot.update()

    # Add a dynamic plotter
    dynplot = MultiPlotter(frame)
    sizer.Add(dynplot,  1, wx.EXPAND | wx.ALL, 5)
    line = TestPlotProxy('dynamic')
    line.updateLines(0,0)
    dynplot.addProxy(line)
    dynplot.update()

    def OnNotify():
        line.updateLines(0, 0)
        line.updateListeners()
        timer.Start(timeout)
    
    timeout = 50
    timer = wx.PyTimer(OnNotify)
    timer.Start(timeout)

    def OnClose(evt):
        timer.Stop()
        app.ExitMainLoop()
    frame.Bind(wx.EVT_CLOSE,OnClose)
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
