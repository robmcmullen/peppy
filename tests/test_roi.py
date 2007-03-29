#!/usr/bin/env python
"""
Test the capabilities of HSI.Cube

"""
import os,os.path,sys,re,time,commands

from nose.tools import *

from peppy.trac.core import *
import peppy.hsi as hsi
import peppy.hsi.ENVI as ENVI

from cStringIO import StringIO
import numpy


from test_hsi import fakeCube

fakeFile="""ENVI
description = {
fake test cube}
samples = 5
lines = 4
bands = 3
header offset = 0
file type = ENVI standard
data type = 2
reflectance scale factor = 10000.000000
interleave = BIL
sensor type = AVIRIS
byte order = %d
bbl = {
 1, 1, 1
 }
wavelength = {
        369.850,        379.690,        389.530
     }
wavelength units = nm
fwhm = {
          9.610,          9.580,          9.550 }
""" % hsi.nativeByteOrder

fake = fakeCube('bsq', file=fakeFile)

class testROI(object):
    def setUp(self):
        self.roi = hsi.ROI('test')
        
    def testOne(self):
        points = [(1,1), (2,2), (3,3), (4,4)]
        for x,y in points:
            self.roi.addPoint(x,x,y)
        for i in self.roi.points:
            spectra = fake.getSpectra(i[1], i[0])
            print spectra
            eq_(len(spectra), fake.bands)
            eq_(spectra[0], 6)
            eq_(spectra[1], 26)
            eq_(spectra[2], 46)
            # only do the first spectra
            break

class testResample(object):
    def setUp(self):
        pass

    def test1(self):
        spectra1 = [5.0, 19.0, 2.0, 4.0, 5.0]
        lam1 = [1, 2, 3, 4, 5]
        spectra2 = [5.0, 19.0, 2.0, 4.0, 5.0]
        lam2 = [1, 2, 3, 4, 5]

        x, y1, y2 = hsi.resample(lam1, spectra1, lam2, spectra2)
        eq_(len(x),5)
        eq_(x[0],1)
        eq_(x[4],5)
        print x, y1, y2
        
    def test1a(self):
        spectra1 = [5.0, 19.0, 2.0, 4.0, 5.0]
        lam1 = [1, 2, 3, 4, 5]
        spectra2 = [2.0, 5.0, 19.0, 2.0, 4.0, 5.0, 20.0, 11.0]
        lam2 = [0, 1, 2, 3, 4, 5, 6, 7]

        x, y1, y2 = hsi.resample(lam1, spectra1, lam2, spectra2)
        eq_(len(x),5)
        eq_(x[0],1)
        eq_(x[4],5)
        print x, y1, y2
        
    def test2(self):
        spectra1 = [5.0, 19.0, 2.0, 4.0, 5.0]
        lam1 = [1, 2, 3, 4, 5]
        spectra2 = [5.0, 17.2, 3.3, 5.7]
        lam2 = [1.5, 2.5, 3.5, 4.5]

        x, y1, y2 = hsi.resample(lam1, spectra1, lam2, spectra2)
        eq_(len(x),3)
        eq_(x[0],2)
        eq_(x[2],4)
        print x, y1, y2
        
class testSAM(object):
    def setUp(self):
        pass

    def test1(self):
        spectra1 = [5.0, 19.0, 2.0, 4.0, 5.0]
        lam1 = [1, 2, 3, 4, 5]
        spectra2 = [5.0, 18.0, 2.0, 3.0, 5.0]
        lam2 = [1, 2, 3, 4, 5]

        ang = hsi.spectralAngle(lam1, spectra1, lam2, spectra2)
        print ang
        
