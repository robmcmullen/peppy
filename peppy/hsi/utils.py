# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Regions of Interest.

Regions of Interest are groups of pixels that are similar in some way,
grouped together either by the user manually picking out points and
saving them to a file, or through some classification process
performed on extracted data.
"""

import os, sys, math
from cStringIO import StringIO

from peppy.debug import *
from peppy.iofilter import *
from peppy.trac.core import *

import numpy


def getRangeIntersection(x1, x2, bbl1=None):
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
    new2 = []
    lam, s1, s2 = resample(lam1, spectra1, lam2, spectra2, bbl)
    print "resampled: lam=%s\ns1=%s\ns2=%s" % (lam, s1, s2)
    
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
    print "bot=%f top=%f tot=%f alpha=%f" % (bot, top, tot, alpha)

    return alpha

