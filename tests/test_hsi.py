#!/usr/bin/env python
"""
Test the capabilities of HSI.Cube

"""
import os,os.path,sys,re,time,commands

from nose.tools import *

from peppy.iofilter import *
from peppy.trac.core import *
import peppy.hsi as hsi
import peppy.hsi.ENVI as ENVI

from cStringIO import StringIO
import numpy

def localfile(name):
    path = os.path.join(os.path.dirname(__file__), name)
    return path

fakeNmFile="""ENVI
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
 1, 1, 0, 1
 }
wavelength = {
        369.850,        379.690,        389.530,        399.370
     }
wavelength units = nm
fwhm = {
          9.610,          9.580,          9.550,          9.530 }
""" % hsi.nativeByteOrder

fakeUmFile="""ENVI
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
 1, 1, 0, 1
 }
wavelength = {
        .369850,        .379690,        .389530,        .399370
     }
wavelength units = um
fwhm = {
        .009610,        .009580,          .009550,          .009530 }
""" % hsi.nativeByteOrder


def fakeCube(interleave,default=None, file=fakeNmFile):
    file=StringIO(file)
    h=ENVI.Header()
    h.read(file)
    h['interleave']=interleave
    cube=hsi.newCube(interleave)
    h.setCubeAttributes(cube)
    if default!=None:
        cube.raw=numpy.zeros((cube.samples*cube.lines*cube.bands),dtype=cube.data_type)
        cube.raw+=default
    else:
        cube.raw=numpy.array(numpy.arange(cube.samples*cube.lines*cube.bands),dtype=cube.data_type)
    cube.initialize()
    return cube
   
def loadCube(filename):
    h=ENVI.Header(filename)
    cube=h.getCube()
    cube.open()
    return cube


class fakeFooCube(object):
    def testFail(self):
        self.assertRaises(ValueError,cube.newCube,'foo')


class baseCube(object):
    def setUp(self):
        self.pixlist=[]
        self.spectralist=[]
        self.spectrallines=[]
        
    def testPixels(self):
        assert(self.cube.isDataLoaded())
        for line,sample,band,value in self.pixlist:
            eq_(self.cube.getPixel(line,sample,band),value)
            #print "%d,%d,%d: stored=%f  should be=%f" % (line,sample,band,float(self.cube.getPixel(line,sample,band)),float(value))
            eq_(self.cube.flatToLocation(self.cube.locationToFlat(line,sample,band)),(line,sample,band))
            
    def testSpectra(self):
        assert(self.cube.isDataLoaded())
        for line,sample,spectra in self.spectralist:
            eq_(self.cube.getSpectra(line,sample).tolist(),spectra)

    def testLinesOfSpectra(self):
        assert(self.cube.isDataLoaded())
        # verify lines of spectra by looking at all the pixel data
        # defined in pixlist, but getting the values using
        # getLineOfSpectra and comparing the pixel values that way.
        # Not terribly efficient since it may end up loading the same
        # band many times, but oh well.
        for line,sample,band,value in self.pixlist:
            lines=self.cube.getLineOfSpectraCopy(line)
            #print "band size=%s  sample=%d line=%d expected=%f val=%f" % (str(plane.shape),line,sample,value,plane[sample][line])
            eq_(lines.shape,(self.cube.samples,self.cube.bands))
            eq_(lines[sample][band],value)

    def testBands(self):
        assert(self.cube.isDataLoaded())
        # verify bands by looking at all the pixel data defined in
        # pixlist, but getting the band using getBand and comparing
        # the pixel values that way.  Not terribly efficient since it
        # may end up loading the same band many times, but oh well.
        for line,sample,band,value in self.pixlist:
            plane=self.cube.getBand(band)
            #print "band size=%s  sample=%d line=%d expected=%f val=%f" % (str(plane.shape),line,sample,value,plane[sample][line])
            eq_(plane.shape,(self.cube.lines,self.cube.samples))
            eq_(plane[line][sample],value)


class fakeBase(baseCube):
    def setUp(self,interleave):
        baseCube.setUp(self)
        self.cube=fakeCube(interleave)
        
    def testBandList_nm(self):
        bands=self.cube.getBandListByWavelength(382.0,units='nm')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(405.0,units='nm')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(305.0,units='nm')
        eq_(bands,[0])
        bands=self.cube.getBandListByWavelength(372.0,405.0,units='nm')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(200.0,1000.0,units='nm')
        eq_(bands,[0,1])
        
    def testBandList_um(self):
        bands=self.cube.getBandListByWavelength(.382,units='um')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(.405,units='um')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(.305,units='um')
        eq_(bands,[0])
        bands=self.cube.getBandListByWavelength(.372,.405,units='um')
        eq_(bands,[1])
        bands=self.cube.getBandListByWavelength(0.2,1.0,units='um')
        eq_(bands,[0,1])
        
    def testUnits(self):
        eq_(self.cube.wavelength_units,'nm')

    def testNewHeader(self):
        header=ENVI.Header(self.cube)
        eq_(header['data type'],'2')


class fakeUmBase(fakeBase):
    def setUp(self,interleave):
        # skip fakeBase and call its parent directly
        baseCube.setUp(self)
        self.cube=fakeCube(interleave,file=fakeUmFile)
    
    def testUnits(self):
        eq_(self.cube.wavelength_units,'um')



class testFakeBILCube(fakeBase):
    def setUp(self):
        super(testFakeBILCube,self).setUp('bil')
        self.pixlist=[
            (0,0,0, 0),
            (0,0,1, 5),
            (0,0,2, 10),
            (3,1,0, 46),
            (3,4,2, 59),
            (2,3,1, 38),
            ]
##        self.spectralist=[
##            (0,0, [0,5,10])
##            ]
        #print self.cube.raw

class testFakeUmBILCube(fakeUmBase):
    def setUp(self):
        super(testFakeUmBILCube,self).setUp('bil')
        self.pixlist=[
            (0,0,0, 0),
            (0,0,1, 5),
            (0,0,2, 10),
            (3,1,0, 46),
            (3,4,2, 59),
            (2,3,1, 38),
            ]
##        self.spectralist=[
##            (0,0, [0,5,10])
##            ]
        #print self.cube.raw

class testFakeBIPCube(fakeBase):
    def setUp(self):
        super(testFakeBIPCube,self).setUp('bip')
        self.pixlist=[
            (0,0,0, 0),
            (0,0,1, 1),
            (0,0,2, 2),
            (2,3,0, 39),
            (3,2,1, 52),
            (1,4,2, 29),
            ]
        #print self.cube.raw

class testFakeBSQCube(fakeBase):
    def setUp(self):
        super(testFakeBSQCube,self).setUp('bsq')
        self.pixlist=[
            (0,0,0, 0),
            (0,0,1, 20),
            (0,0,2, 40),
            (2,3,0, 13),
            (3,2,1, 37),
            (1,4,2, 49),
            ]
        #print self.cube.raw

class testFilenames(object):
    def testHeader1(self):
        filename = localfile('hsi/test1.bil')
        urls = ENVI.findHeaders(filename)
        header = URLInfo(localfile('hsi/test1.hdr'))
        eq_(urls[0].path, header.path)
        
    def testHeader2(self):
        filename = localfile('hsi/test2.bip')
        urls = ENVI.findHeaders(filename)
        header = URLInfo(localfile('hsi/test2.bip.hdr'))
        eq_(urls[0].path, header.path)
        
    def testIdentify1(self):
        filename = localfile('hsi/test1.bil')
        format = hsi.HyperspectralFileFormat.identify(filename)
        eq_(format.format_id, 'ENVI')
        
    def testIdentify2(self):
        filename = localfile('hsi/test2.bip')
        format = hsi.HyperspectralFileFormat.identify(filename)
        eq_(format.format_id, 'ENVI')
        
