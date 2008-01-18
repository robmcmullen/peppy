# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""HSI Utilities.

These are utility functions that are in common use by the
hyperspectral classes.  These functions shouldn't have external
dependencies on any other classes in the hsi package.
"""

import os, sys, math
from cStringIO import StringIO

from peppy.debug import *

import numpy

import cube
try:
    import _utils
except ImportError:
    _utils = None

# number of meters per unit
units_scale={
'nm':1.0e-9,
'um':1.0e-6,
'mm':1.0e-3,
'm':1.0,
}

def normalizeUnits(txt):
    """Return standard units label for the given label.

    Given a text string, return the standard (usually SI)
    abbreviation.  Currently just supports lengths.

    Returns None if label not known.
    """
    units=txt.lower()
    if units[0:4]=='nano' or units[0:2]=='nm':
        return 'nm'
    elif units[0:5]=='micro' or units[0:2]=='um':
        return 'um'
    return None


def getRangeIntersection(x1, x2, bbl1=None):
    """Computes the common range of sampling points.

    Given two lists of sampling points, determine the subset of the
    range of the first set such that the endpoints are guaranteed to
    be within the range of the second set of sampling points.

    @param x1: list of sampling points to subset
    @param x2: list of sampling points of other set
    @param bbl1: optional bad band list of x1 (0 = bad, 1 = good)

    @returns: tuple (index1, index2) specifying indexes that give the
    range within 1st sampling set.  Note the indexes are in the python
    idiom where index2 is actually one beyond the last good value so
    you can do a slice like x1[index1:index2] and get the actual list.
    """
    i1start = 0
    i1end = len(x1)
    while x1[i1start] < x2[0] and i1start < i1end:
        i1start += 1
    while x1[i1end-1] > x2[-1] and i1start < i1end:
        i1end -= 1
    if bbl1 is not None:
        while bbl1[i1start] == 0 and i1start < i1end:
            i1start += 1
        while bbl1[i1end-1] == 0 and i1start < i1end:
            i1end -= 1
    return (i1start, i1end)


def resample(x1, y1, x2, y2, bbl1=None):
    """Resample using linear interpolation.

    Given two sets of data, resample the second set to match the first
    set's x values and range.

    @returns tuple (sampling, data1, data2)
    """
    xout = []
    y1out = []
    y2out = []

    # only operate on the intersection of the ranges
    i1start, i1end = getRangeIntersection(x1, x2, bbl1)

    # find first value of 2nd set less than intersection
    i2 = 0
    while i2<len(x2)-1 and x2[i2+1] < x1[i1start]:
        i2 += 1

    x2left = x2[i2]
    x2right = x2[i2+1]
    for i in range(i1start, i1end):
        xinterp = x1[i]
        while xinterp > x2right:
            x2left = x2right
            i2 += 1
            x2right = x2[i2+1]
        yinterp = (xinterp - x2left)/(x2right - x2left)*(y2[i2+1] - y2[i2]) + y2[i2]
        xout.append(xinterp)
        y1out.append(y1[i])
        y2out.append(yinterp)
    return (xout, y1out, y2out)
        
def spectralAngle(lam1, spectra1, lam2, spectra2, bbl=None):
    """Determine spectral angle between two vectors.

    Computes the spectral angle between the common range of two
    vectors, resampling the second one to conform to the first's
    sampling points if necessary.

    @returns angle in degrees
    """
    new2 = []
    lam, s1, s2 = resample(lam1, spectra1, lam2, spectra2, bbl)
    #print "resampled: lam=%s\ns1=%s\ns2=%s" % (lam, s1, s2)
    
    tot = 0.0
    bot1 = 0.0
    bot2 = 0.0
    top = 0.0
    for i in range(len(lam)):
        y1 = s1[i]
        y2 = s2[i]
        bot1 += y1*y1
        bot2 += y2*y2
        top += y1*y2
    bot = math.sqrt(bot1) * math.sqrt(bot2)
    if bot != 0.0:
        tot = top/bot
    if tot > 1.0:
        tot = 1.0
    alpha = math.acos(tot)*180.0/math.pi
    print "spectral angle=%f: bot=%f top=%f tot=%f" % (alpha, bot, top, tot)

    return alpha

def euclideanDistance(lam1, spectra1, lam2, spectra2, bbl=None):
    """Determine Euclidean distance between two vectors.

    Compute Euclidean distance between the common range of two
    vectors, resampling the second one to conform to the first's
    sampling points.

    @returns distance (units are ???)
    """
    new2 = []
    lam, s1, s2 = resample(lam1, spectra1, lam2, spectra2, bbl)
    #print "resampled: lam=%s\ns1=%s\ns2=%s" % (lam, s1, s2)
    
    dist = 0.0
    for i in range(len(lam)):
        delta = s1[i] - s2[i]
        dist += delta*delta
    dist = math.sqrt(dist)
    print "euclidean distance = %f" % dist
    return dist


class Histogram(object):
    def __init__(self,cube,nbins=500,bbl=None):
        self.cube=cube
        self.width=cube.bands
        self.nbins=nbins
        self.pixelsperband=cube.samples*cube.lines

        # NOTE!  This type must remain numpy.int32, or otherwise the C code
        # must be changed.
        self.data=numpy.zeros((self.width,self.nbins),dtype=numpy.int32)
        self.maxvalue=numpy.zeros((self.width,),dtype=numpy.int32)
        self.maxdiff=numpy.zeros((self.width,),dtype=numpy.int32)

        self.accumulation=None

        self.thresholds=[50,100,200,500]

        if bbl:
            self.bbl=bbl
        else:
            self.bbl=self.cube.getBadBandList()
        # print "Histogram: self.bbl=%s" % self.bbl
        

    def info(self):
        lastbin=[]
        for band in range(self.width):
            if not self.bbl[band]:
                lastbin.append('bad')
                self.maxdiff[band]=0
            else:
                last=0
                for bin in range(0,self.nbins):
                    if self.data[band][bin]>0:
                        last=bin
                lastbin.append(last)
            if self.maxvalue[band]==0:
                self.maxvalue[band]=1
                
        print "last bin with non-zero value:"
        print lastbin
        print "max values in band:"
        print self.maxvalue
        print "max differences in each band:"
        print self.maxdiff
        print "max percentage difference:"
        print numpy.array2string((self.maxdiff*1000/self.maxvalue)/10.0,
                        precision=2,suppress_small=1)
        
        

    def calcAccumulation(self,numcolors=20):
        self.info()
        
        self.accumulation=numpy.zeros((self.width,numcolors),dtype=numpy.int32)

        temp=numpy.zeros((self.nbins,),dtype=numpy.int32)

        validpixels=0
        pixelsbelowthreshold=[0]*len(self.thresholds)

        for band in range(self.width):
            if not self.bbl[band]: continue # only operate on valid bands
            
            accum=self.pixelsperband
            validpixels+=accum

            # create temp, a monotonically decreasing list where the
            # first index contains all the pixels, and each subsequent
            # bin subtracts the histogram value for that bin
            for bin in range(0,self.nbins):
                temp[bin]=accum
                num=self.data[band][bin]
                for i in range(len(self.thresholds)):
                    if bin<=self.thresholds[i]:
                        pixelsbelowthreshold[i]+=num
                accum-=num
            
            # print temp

            # Now turn the temp list into an color index based array
            # (so that it can eventually be plotted) by downsampling
            # the ranges of numbers into buckets.  So, if there are 20
            # colors to be plotted and there are 1000 pixels per band,
            # then accumulations between 1000 & 951 get index 0, 950 &
            # 901 get index 1, etc.
            lastheight=numcolors-1
            currentheight=0
            lastindex=0
            for bin in range(self.nbins):
                index=int(float(((self.pixelsperband-temp[bin])*numcolors)/self.pixelsperband))
                if index>=numcolors: index=numcolors-1
                
                #if index>currentheight:
                
                self.accumulation[band][index]=bin

            height=0
            for index in range(numcolors):
                curr=self.accumulation[band][index]
                if curr>0:
                    self.accumulation[band][index]-=height
                    height=curr

        print "Total pixels from good bands=%d" % validpixels
##        if (hist.isTemperature()) {
##            double gain=hist.getTemperatureGain();
##            threshold = new int[] {10,20,50,100,200,500};
            
##            for (int i=0; i<threshold.length; i++) {
##                System.out.printf("  Threshold %.3f Kelvin: valid=%d  percentage=%f%n",
##                    (threshold[i]/10000.0*gain),pixelsBelowThreshold[i],
##                    (pixelsBelowThreshold[i]*100.0/totalPixelsInValidBands));
##            }
##        }
        for i in range(len(self.thresholds)):
            print "  Threshold %f reflectance units: valid=%d  percentage=%f" % ((self.thresholds[i]*1.0),pixelsbelowthreshold[i],(pixelsbelowthreshold[i]*100.0/validpixels))



class CubeCompare(object):

    def __init__(self,c1,c2):
        if c1.bands!=c2.bands or c1.lines!=c2.lines or c1.samples!=c2.samples:
            raise ValueError("Cubes don't have same dimensions")
        
        self.cube1=c1
        self.cube2=c2
        self.histogram=None
        self.hashPrintCount=100000
        self.bbl=self.cube1.getBadBandList(self.cube2)
        # print "CubeCompare: bbl=%s" % self.bbl
        
    def getHistogramByFlatPython(self,nbins=500):
        f1=self.cube1.getFlatView()
        #print f1
        f2=self.cube2.getFlatView()
        bandBoundary=self.cube1.getBandBoundary()
        
        if self.cube1.interleave != self.cube2.interleave:
            diff=True
        else:
            diff=False

        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data
        i1=0
        i2=0
        count=0
        band=0
        progress=0
        try:
            while True:
                val=f1[i1]-f2[i2]
                bin=abs(val)
                if bin>=nbins: bin=nbins-1
                h[band][bin]+=1
                count+=1
                if count>=bandBoundary:
                    count=0
                    band+=1
                    if band>=self.cube1.bands: band=0
                progress+=1
                if progress>1000:
                    #print "#",
                    print "i1=%d i2=%d diff=%s" % (i1,i2,str(diff))
                    progress=0
                i1+=1
                if diff:
                    s,l,b=self.cube1.flatToLocation(i1)
                    i2=self.cube2.locationToFlat(s,l,b)
                else:
                    i2+=1
                    
        except IndexError:
            pass
        return self.histogram
    
    def getHistogramByBand(self,nbins=500):
        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data

        for i1 in range(self.cube1.bands):
            band1=self.cube1.getBand(i1)
            band2=self.cube2.getBand(i1)
            count=(self.cube1.samples*self.cube1.lines)
            band=abs(band1-band2)
            mx=band.max()
            mn=band.min()
            print "band %d: local min/max=(%d,%d) " % (i1,mn,mx)
##            for samp in range(self.cube1.samples):
##                for line in range(self.cube1.lines):
##                    val=band1[samp,line]-band2[samp,line]
##                    bin=abs(val)
##                    if bin>=nbins: bin=nbins-1
##                    h[band][bin]+=1
##
##            print "band %d" % (band)
        return self.histogram
    
    def getHistogramByFlatChunk(self,nbins=500):
        f1=self.cube1.getFlatView()
        f2=self.cube2.getFlatView()
        bandBoundary=self.cube1.getBandBoundary()
        
        if self.cube1.interleave != self.cube2.interleave:
            diff=True
        else:
            diff=False

        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data

        chunksize=100000

        count=0
        band=0
        for i1 in range(0,f1.size(),chunksize):
            i2=i1+chunksize
            if i2>f1.size(): i2=f1.size()
            c1=f1[i1:i2]
            c2=f2[i1:i2]
            #bins=abs(c1-c2)
            #mx=bins.max()
            #mn=bins.min()

            for val in c1-c2:
                bin=abs(val)
                if bin>=nbins: bin=nbins-1
                h[band][bin]+=1
                count+=1
                if count>=bandBoundary:
                    count=0
                    band+=1
                    if band>=self.cube1.bands: band=0
                    
            print "chunk %d " % (i1)
##            for samp in range(self.cube1.samples):
##                for line in range(self.cube1.lines):
##                    val=band1[samp,line]-band2[samp,line]
##                    bin=abs(val)
##                    if bin>=nbins: bin=nbins-1
##                    h[band][bin]+=1
##
##            print "band %d" % (band)
        return self.histogram
    
    def getHistogramByFlat(self,nbins=500):
        f1=self.cube1.getFlatView()
        f2=self.cube2.getFlatView()

        bandBoundary=self.cube1.getBandBoundary()
        
        if self.cube1.interleave != self.cube2.interleave:
            diff=True
        else:
            diff=False

        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data

        print "Calling _utils.CubeHistogram..."
        _utils.CubeHistogram(self.cube1,self.cube2,self.histogram)

        
        chunksize=100000

        count=0
        band=0
        i1=0
        progress=0
        for val in f1-f2:
            bin=abs(val)
            if bin>=nbins: bin=nbins-1
            h[band][bin]+=1
            count+=1
            if count>=bandBoundary:
                count=0
                band+=1
                if band>=self.cube1.bands: band=0

            i1+=1
            progress+=1
            if progress>100000:
                #print "#",
                print "processed %d" % (i1)
                progress=0

        return self.histogram
    
    def getHistogramFast(self,nbins=500):
        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data

        print "Calling _utils.CubeHistogram..."
        _utils.CubeHistogram(self.cube1,self.cube2,self.histogram)

        return self.histogram

    def getHistogram(self, nbins=500):
        if _utils is not None:
            return self.getHistogramFast(nbins)
        return self.getHistogramByBand(nbins)
    
    def getExtrema(self):
        """Really just a test function to see how long it takes to
        seek all the way through one file."""
        
        f1=self.cube1.getFlatView()
        print f1
        i1=0
        progress=0
        minval=100000
        maxval=0
        try:
            while True:
                val=f1[i1]
                if (val>maxval): maxval=val
                if (val<minval): minval=val
                progress+=1
                if progress>1000:
                    #print "#",
                    print "i1=%d " % (i1)
                    progress=0
                i1+=1
                    
        except IndexError:
            pass
        return (minval,maxval)
    
    def getExtremaChunk(self):
        """Really just a test function to see how long it takes to
        seek all the way through one file."""

        minval=100000
        maxval=0
        
        for i1 in range(self.cube1.bands):
            band=self.cube1.getBand(i1)
            mx=band.max()
            mn=band.min()
            if (mx>maxval): maxval=mx
            if (mn<minval): minval=mn
            print "band %d: local min/max=(%d,%d)  accumulated min/max=(%d,%d)" % (i1,mn,mx,minval,maxval)
            
        return (minval,maxval)
