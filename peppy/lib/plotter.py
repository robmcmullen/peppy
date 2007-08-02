# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Plotting utilities on top of wx.lib.plot
"""

import os,sys,re,random

from peppy.debug import *

import wx
import wx.lib.plot as plot

import numpy

try:
    from peppy.debug import *
except:
    # stubs so things that use peppy.debug can operate without peppy
    def dprint(txt=""):
        #print txt
        pass

    class debugmixin(object):
        def dprint(self, txt):
            pass


class PlotProxy(object):
    def __init__(self):
        self.title='title'
        self.xlabel='xlabel'
        self.ylabel='ylabel'
        self.xaxis=[0,100]
        self.yaxis=[0,100]
        self.rgblookup=['red','green','blue']

        self.lines=[]

        # listeners are MultiPlotters that are looking at this data
        self.listeners=[]

    def getLines(self, x, y):
        return []

    def update(self, x, y):
        # print "PlotProxy: update (%d,%d)" % (x,y)
        self.lines=self.getLines(x,y)

    def addListener(self, plotter):
        self.listeners.append(plotter)
        # print "%s: listeners=%s" % (__name__,self.listeners)

    def getListeners(self):
        return self.listeners
    
    def updateListeners(self,skip=[]):
        for listener in self.listeners:
            if listener in skip:
                # print "skipping listener: %s" % str(listener)
                continue
            else:
                # print "updating listener: %s" % str(listener)
                # print "  shown: %s" % listener.IsShown()
                listener.update()

    def updateListenerExtrema(self):
        for listener in self.listeners:
            listener.updateExtrema()


class TestPlotProxy(PlotProxy):
    def __init__(self):
        PlotProxy.__init__(self)
        
        self.title='Test'
        self.xlabel='x'
        self.ylabel='y'
        self.xaxis=(0,10)
        self.yaxis=(0,10)
        
    def getLines(self, x, y):
        # print "TestPlotProxy: (%d,%d)" % (x,y)
        data=numpy.zeros((10,2))
        data[:,0]=numpy.arange(10)
        y = range(10)
        random.shuffle(y)
        data[:,1]=numpy.array(y)
        line = plot.PolyLine(data, legend= 'random', colour='orange')
        return [line]


class MultiPlotter(plot.PlotCanvas, debugmixin):
    def __init__(self, parent, id=-1, proxy=None, grid=True, legend=True, fullscale=True, frame=None):
        plot.PlotCanvas.__init__(self, parent, id)

        self.proxies=[]
        self.setProxy(proxy)
        self.rgblookup=['red','green','blue']
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

        self._frame = frame
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
        if clear:
            # FIXME: remove self from existing proxy listeners
            self.proxies=[]
        self.addProxy(proxy)

    def addProxy(self, proxy):
        if proxy is not None:
            if type(proxy) in [list,tuple]:
                for p in proxy:
                    self.proxies.append(p)
                    p.addListener(self)
            else:
                self.proxies.append(proxy)
                proxy.addListener(self)
            self.setup()

    # From a list of (min,max) pairs, return the overall min and max
    # from the list
    def getExtrema(self,extrema):
        lo=min([a for a,b in extrema])
        hi=max([b for a,b in extrema])
        # print "extrema: (%d,%d)" % (lo,hi)
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
        dprint("Found %d proxies" % len(self.proxies))
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
                # print "index=%d dx=%.4f newdx=%.4f" % (i,dx,newdx)
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
            # print "checking line #0: index=%d dy=%.4f" % (near['index'],dy)
            for i in range(1,len(nearlist)):
                newnear=nearlist[i]
                newdy=abs(y-newnear['line'].points[newnear['index'],1])
                # print "checking line #%d: index=%d dy=%.4f" % (i,newnear['index'],newdy)
                if newdy<dy:
                    nearest=newnear
                    dy=newdy
                    # print "  line #%d is closer" % (index)
                    
            # print "best match: index=%d dx=%.4f dy=%.4f" % (near['index'],near['dx'],dy)
        else:
            nearest=nearlist[0]
        nearest['pointXY']=(nearest['line'].points[nearest['index'],0],
                            nearest['line'].points[nearest['index'],1])
        (x,y)=self.PositionUserToScreen(nearest['pointXY'])
        # print x,y
        nearest['scaledXY']=(x,y)

            
        return nearest

    def OnMotion(self, evt):
        if self._snapToValues and evt.LeftIsDown():
            x,y=self.GetXY(evt)
            nearest=self.findNearest(x,y)
            self.UpdatePointLabel(nearest)
        plot.PlotCanvas.OnMotion(self, evt)

    def OnMouseLeftDown(self, evt):
        if self._snapToValues:
            x,y=self.GetXY(evt)
            nearest=self.findNearest(x,y)
            self.UpdatePointLabel(nearest)
        plot.PlotCanvas.OnMouseLeftDown(self, evt)

    def OnMouseLeftUp(self, evt):
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
        if self._frame:
            self._frame.SetStatusText("%s: x = %.4f, y = %.4f" % (nearest['legend'],x,y))


if __name__ == "__main__":
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='MultiPlotter and PlotProxy Test', size=(500,500))
    
    # Add a multiplotter
    plotter = MultiPlotter(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(plotter,  1, wx.EXPAND | wx.ALL, 5)

    # Add some proxies
    t1 = TestPlotProxy()
    plotter.addProxy(t1)
    t1.update(0,0)
    plotter.update()
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
