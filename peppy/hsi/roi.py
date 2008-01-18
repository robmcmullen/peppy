# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Regions of Interest.

Regions of Interest are groups of pixels that are similar in some way,
grouped together either by the user manually picking out points and
saving them to a file, or through some classification process
performed on extracted data.
"""

import os,os.path,sys,re,struct,stat
from cStringIO import StringIO

import peppy.vfs as vfs

from peppy.hsi.utils import *

from peppy.debug import *

import numpy

# Trac plugin for registering new HSI readers

##class IHyperspectralROIFormat(Interface):
##    def supportedROIFormats():
##        """Return a list of classes that this plugin defines.
##        """
   
class HyperspectralROIFormat(object):
    @staticmethod
    def identify(urlinfo):
        if not isinstance(urlinfo, URLInfo):
            urlinfo = URLInfo(urlinfo)
        comp_mgr = ComponentManager()
        register = HyperspectralROIFormat(comp_mgr)
        print "handlers: %s" % register.handlers
        for loader in register.handlers:
            for format in loader.supportedROIFormats():
                print "checking %s for %s format" % (urlinfo, format.format_name)
                if format.identify(urlinfo):
                    print "Identified %s format" % format.format_name
                    return format
        return None

    @staticmethod
    def load(urlinfo):
        if not isinstance(urlinfo, URLInfo):
            urlinfo = URLInfo(urlinfo)
        format = HyperspectralROIFormat.identify(urlinfo)
        if format:
            dprint("Loading %s format ROIs" % format.format_name)
            roi=format.load(urlinfo)
            print roi
            return roi
        return None

class ROISpectrum(object):
    def __init__(self, label, color, spectra, cube):
        self.label = label
        self.color = color
        self.wavelengths = cube.wavelengths
        self.bbl = cube.bbl
        self.spectra = spectra

    def compare(self, wavelengths, spectra):
        sam = spectralAngle(self.wavelengths, self.spectra,
                            wavelengths, spectra, self.bbl)
        dist = euclideanDistance(self.wavelengths, self.spectra,
                                 wavelengths, spectra, self.bbl)
        return (sam, dist)

class ROI(object):
    def __init__(self, name):
        self.name = name
        self.number = 0
        self.color = None
        self.points = []
        self.labels = []
        if name.endswith('avg'):
            self.average = True
        else:
            self.average = False

    def __str__(self):
        return "name=%s number=%d color=%s points=%s" % (self.name, self.number, str(self.color), str(self.points))

    def setColor(self, txt):
        if txt.startswith('{'):
            txt = txt[1:]
        if txt.endswith('}'):
            txt = txt[:-1]
        self.color = [(int(i)/float(255)) for i in txt.split(',')]

    def addPoint(self, id, x, y):
        self.labels.append(id)
        self.points.append((x, y))

    def getSpectra(self, cube):
        for i in self.points:
            print i
            spectra = cube.getSpectra(i[1],i[0])
            print spectra

    def getAllColumns(self, cube):
        cols = []
        for i in range(len(self.points)):
            label = '%s-%s' % (self.name, self.labels[i])
            spectra = cube.getSpectra(self.points[i][1],self.points[i][0])/10000.0
            col = ROISpectrum(label, self.color, spectra, cube)
            cols.append(col)
        #print cols
        return cols

    def getAverageOfColumns(self, cube):
        cols = []
        total = cube.getSpectra(self.points[0][1],self.points[0][0]).astype(numpy.float32)
        for i in range(1,len(self.points),1):
            total += cube.getSpectra(self.points[i][1],self.points[i][0])
        total /= len(self.points)
        total /= 10000.0
        label = '%s-%s-%s' % (self.name, self.labels[0], self.labels[-1])
        col = ROISpectrum(label, self.color, total, cube)
        cols.append(col)
        #print cols
        return cols

    def getColumns(self, cube):
        if self.average:
            return self.getAverageOfColumns(cube)
        else:
            return self.getAllColumns(cube)

class ROIFile(object):
    """Container for ROIs pertaining to a single cube.

    """
    
    def __init__(self, filename):
        self.filename = filename
        self.rois = []
        self.roimap = {}

    def __str__(self):
        fh = StringIO()
        for roi in self.rois:
            fh.write(str(roi) + os.linesep)
        return fh.getvalue()

    @classmethod
    def identify(cls, urlinfo):
        return False

    @classmethod
    def load(cls, urlinfo):
        return None
        
    def addROI(self, roi):
        self.rois.append(roi)
        self.roimap[roi.name] = roi

    def getROI(self, index):
        return self.rois[index]
