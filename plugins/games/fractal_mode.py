# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Major mode for displaying the Mandelbrot fractal image.

I was reading L{Prime
Obsession<http://www.johnderbyshire.com/Books/Prime/page.html>} and it
prompted me to look into complex numbers again.  One of the interesting things
about the L{Mandelbrot set<http://en.wikipedia.org/wiki/Mandelbrot_set>} is
the simplicity of the equation behind the fractal image.

Adapted from the L{Mandelbrot example from the NumPy tutorial<http://www.scipy.org/Tentative_NumPy_Tutorial/Mandelbrot_Set_Example>}

"""

import os, random, time
from cStringIO import StringIO

import wx
import wx.stc

from peppy.debug import *
from peppy.actions import *
from peppy.major import *
from peppy.stcinterface import *
from peppy.lib.bitmapscroller import *

icondict = {
'fractal.png':
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\
\x00\x00\x00\x90\x91h6\x00\x00\x00\x03sBIT\x08\x08\x08\xdb\xe1O\xe0\x00\x00\
\x02qIDAT(\x91m\x8fKOSQ\x14\x85\xf7>\xe7\xdc\xde\xbe.\xe5\xd1\x82\x96\xda\
\xa0V\x05*\x054\xa8\x94\xa0\x80\xa0\x928qh\xe2\xd8\x81\xbfA\xe6\xc6\x1f\xe0\
\xc4\x91\x03\x13\x12\x07\x10\x13\x07F\x82qd\xa8\x1a\x14\x88h\x11\x95W\xa1\
\x94\xbeK\xb9\xed\xbd\xf7l\x07h\x8c\xc87^_\xd6Z\x88\xea]@\x06\xc0\t\x19"\x07\
`\xc482\x1b*v\xe1\xa9;w\xb3=\x9b5\x97^~\xa0\xbd\x02\xc8\nI\x83\x01rB\x01(\
\x10\x050\x01\\e\x8a\x13\x1d\x1aw{\xc2\x03\'\xcd\xb9\x07\xe1\xc6\xcfJ}\x03sh\
 \\\xc8\x14\x8eJ\x14Q\x00W\x80)\xc0m\xa88\x98\xbbv\xe4N\xa7\xcb\xe7\xf2z\xb2\
k3\xcf\xb8bo\xe9\x08g\xcc:O\xc0\xb7\x9b\xcc\tb\nr\x15\x85\nL \xe7hS\xb5f/\
\x14?\x15\xdf>\xfe\xb8\x14\'\xa2\x95\x9fO\xdc\xdaDG\xef\xa0\xd6z{j\xde\xce\
\xd19\xc4\\\xb5\xde\xaeV\xb0\xd9\xd5\xfaZ\xb0;\x87\x07Dl|lmu\x05\xfeP\xadV\
\x92\xab\xdf\x9bNEsy\xa7@\xd5\xc5\xdd5m=G=\x85\xd7\xcc(n9\x86\x12_\xc6\xb7\
\x93I\xf8\x17\xc30\n?\xa6LkT(\xf5\xbe\xf6\xa1\xd3u\xbbo\x9e?\xba/%\x05C\x13\
\xaaM\xc0a\x18\xcc\xa7\x17\xcb"4\xd8\xdabM\xc6&\x9fJI\x00\xb0\xfa\xed\xab"\
\x0e\x11\xec\xae\x9a<\xef\x03k\x87\x17JQ\x11\xea\rG\x02\xf1\xd84\x11\x05Cg\
\xbcM\x8d\x99T\xea\x80`\x1a\x95@\xb0!\x9d=\xc2\x89\xf5\xa6\xd7K\xde\xae\x8b\
\x9d\x91\x13\xed\xdd=\x18\xbe\xe7\x80\xdcF|\xf6\xff\x12\x7f0P4\xdb\x04\xe9\
\xbb\x16\x17\x8b\xef6\xcb\xe9f&\x82\x86\xb1}c\xe4zc\xec\xc5\x81\xdf\x8a\xa2\
\xd4\x1c\xbf*\xd2\xc4Q\\ \xd3,\'3f\xa1X-\x94H\xafn\xe6\x1d=\x83\x11(\xaed3\
\x99\xfd\xb4[\xd3\xba\xfb\xafi\x81\xe8\xe2LB\x904\x90\x08\xa4A\xc8\x81\ti\
\x1a\xa5u\x86}\x9d\xda\xa5\x87\xc3\xa3\xf9\xf8\xe4X r\xc5\xe6\x1f\x9d\x9d\
\x03u^RU\xe7(\xce\x13H$\x00\x92@\x16H)\xcd\xea\xf2Bjg\xbd\xecn>\xa6\xd1\x92\
\xff\xec\xe5\xe9W\xa4o$J\xeb\t0\xf78\xf2n\x04\x02\x90\x04\x84@\xbf5\xcb"\xcb\
\xda\xd9\xda\xf3\xf7\xdfZK7\xa4\x16\x96I/\x82\xa5\x9348\xf2\xae\xfd\xa1\x08\
\x04D\x7f5i\x92\x05\xba\xb4m\xbe\x8f\xcbr\x0e\xcc\n\x91\x81d\xfd\x02\xcc\x06\
%2\xb9\x1b\xbb\xdb\x00\x00\x00\x00IEND\xaeB`\x82' 
}
from peppy.lib.iconstorage import *
addIconsFromDict(icondict)


class ViewMandelbrot(SelectAction):
    """Start the Mandelbrot viewer
    """
    name = "Mandelbrot Set"
    tooltip = "View the Mandelbrot Set"
    default_menu = "Tools/Games"

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:fractal#mandelbrot")


class Fractal(debugmixin):
    """Base class for displaying fractals.
    
    """
    def __init__(self, width, height, iter=20):
        self.width = width
        self.height = height
        self.maxit = iter
        
        self.scale = 1.0
        self.center = (-0.6, 0)
        
        import numpy
        self.arr = numpy.empty((self.width, self.height, 3), numpy.uint8)
        self.bmp = None

    def getBitmap(self, progress=None):
        if self.bmp is None:
            self.calculate(progress)
            self.bmp = wx.BitmapFromBuffer(self.width, self.height, self.arr)
        return self.bmp

    def setView(self, x, y, scale):
        self.center = (x, y)
        self.scale = scale

    def calculate(self, progress=None):
        raise NotImplementedError


class MandelbrotSet(Fractal):
    """Mandelbrot set from the old Numeric examples.
    
    """
    def calculate(self, progress=None):
        # Don't import numpy until now, so that it won't be imported when the
        # application first starts.
        import numpy
        
        aspect = float(self.width) / self.height
        zoom = 1.0 * (self.scale / 8.0)
        if zoom < 1.0:
            zoom = 1.0
        w = 1.4 / zoom
        h = 1.4 / aspect / zoom
        #istart = -1.4
        #iend = 1.4
        #rstart = -2.0
        #rend = 0.8
        x1 = self.center[0] - w
        x2 = self.center[0] + w
        y1 = self.center[1] - h
        y2 = self.center[1] + h
        self.dprint("re: %f - %f, im: %f - %f" % (x1, x2, y1, y2))

        # Algorithm from the old Numeric tutorial
        xx = numpy.arange(x1, x2, (x2-x1)/self.width)
        yy = numpy.arange(y2, y1, (y1-y2)/self.height) * 1j
        q = numpy.ravel(xx+yy[:, numpy.newaxis])
        z = numpy.zeros(q.shape, numpy.complex)
        output = numpy.resize(numpy.array(0,), q.shape)
        if progress:
            progress.startProgress("Iterating...", self.maxit)
        start = time.time()
        for iter in range(self.maxit):
            if progress:
                progress.updateProgress(iter)
                wx.GetApp().cooperativeYield()
            z = z*z + q
            done = numpy.greater(abs(z), 2.0)
            q = numpy.where(done,0+0j, q)
            z = numpy.where(done,0+0j, z)
            output = numpy.where(done, iter, output)
        #dprint("arr=%s, output=%s" % (str(self.arr.shape), str(output.shape)))
        output = output.reshape(self.width, self.height) * (255 / iter)
        #dprint(output.shape)
        self.arr[:,:,0] = output
        self.arr[:,:,1] = output
        self.arr[:,:,2] = output
        if progress:
            progress.stopProgress("%d iterations in %f seconds" % (self.maxit, time.time() - start))


class MandelbrotSet2(Fractal):
    """Mandelbrot set from the newer numpy examples.
    
    This algorithm doesn't seem to be able to handle non-square aspect ratios
    """
    def calculate(self, progress=None):
        # Don't import numpy until now, so that it won't be imported when the
        # application first starts.
        import numpy
        
        aspect = float(self.width) / self.height
        zoom = 1.0 * (self.scale / 8.0)
        if zoom < 1.0:
            zoom = 1.0
        w = 1.4 / zoom
        h = 1.4 / aspect / zoom
        #istart = -1.4
        #iend = 1.4
        #rstart = -2.0
        #rend = 0.8
        rstart = self.center[0] - w
        rend = self.center[0] + w
        istart = self.center[1] - h
        iend = self.center[1] + h
        print("re: %f - %f, im: %f - %f" % (rstart, rend, istart, iend))
        # Algorithm from the NumPy tutorial
        #y,x = numpy.ogrid[ istart:iend:self.height*1j, rstart:rend:self.width*1j ]
        x,y = numpy.ogrid[ rstart:rend:self.width*1j, istart:iend:self.height*1j ]
        c = x+y*1j
        z = c
        #print z
        divtime = self.maxit + numpy.zeros(z.shape, dtype=int)
        #print divtime

        if progress:
            progress.startProgress("Iterating...", self.maxit)
        start = time.time()
        for i in xrange(self.maxit):
            if progress:
                progress.updateProgress(i)
                wx.GetApp().cooperativeYield()
            z  = z**2 + c
            diverge = z*numpy.conj(z) > 2**2            # who is diverging
            div_now = diverge & (divtime==self.maxit)  # who is diverging now
            divtime[div_now] = i                  # note when
            z[diverge] = 2                        # avoid diverging too much
        print self.arr.shape
        #divtime = divtime.transpose()
        self.arr[:,:,0] = divtime * 8
        self.arr[:,:,1] = divtime * 8
        self.arr[:,:,2] = divtime * 8
        if progress:
            progress.stopProgress("%d iterations in %f seconds" % (self.maxit, time.time() - start))


class FractalMode(BitmapScroller, MajorMode):
    """
    Major mode for viewing fractals.
    """
    debuglevel=0

    keyword="Fractal"
    icon='fractal.png'

    @classmethod
    def verifyProtocol(cls, url):
        if url.scheme == 'about' and (url.path == 'fractal' or str(url.path).startswith('fractal#')):
            return True
        return False

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        BitmapScroller.__init__(self, parent)
        self.fractal = None
    
    def showInitialPosition(self, user_url):
        """Calculate the initial display of the fractal
        
        This method is called once, at major mode creation time, to set up
        the first display of the fractal.  I put this here rather than in
        the __init__ method because it allows the user interface to be fully
        generated before calculating alll the iterations.
        
        Also, I'm currently using this to select which fractal is displayed by
        the fragment of the url.
        """
        x, y = self.GetClientSizeTuple()
        name = "mandelbrot"
        if '#' in str(user_url.path):
            name = str(user_url.path).split('#')[1]
        if name == "mandelbrot2":
            self.fractal = MandelbrotSet2(x, y, 32)
        else:
            self.fractal = MandelbrotSet(x, y, 32)
        progress = self.status_info
        self.setBitmap(self.fractal.getBitmap(progress))


class MandelbrotPlugin(IPeppyPlugin, debugmixin):
    """Peppy plugin that registers the Mandelbrot viewer and its actions.
    """
    def aboutFiles(self):
        return {"fractal": "-*- FractalMode -*-"}
    
    def getMajorModes(self):
        yield FractalMode
    
    def getActions(self):
        return [ViewMandelbrot]
