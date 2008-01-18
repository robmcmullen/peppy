# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Interface to the hsi module to load cubes via GDAL.

GDAL supports a wide variety of cubes, all available through the same
GDAL abstract interface.  It seems somewhat slower than direct mmap
access, but in many cases raw access isn't available due to
compression.
"""

import os,os.path,sys,re,struct,stat
from cStringIO import StringIO

import cube

import gdal

import peppy.vfs as vfs

from peppy.debug import *

import numpy

# mapping of GDAL datatype numbers to numpy types.  There is no GDAL
# type corresponding to signed 8 bit integer, and there are no
# equivalents in numpy for the integer complex numbers of GDAL.
GDALDataType=[None, numpy.uint8,
              numpy.uint16, numpy.int16,
              numpy.uint32, numpy.int32,
              numpy.float32, numpy.float64,
              None, None,
              numpy.complex64, numpy.complex128]


class GDALDataset(cube.MetadataMixin):
    """
    Class representing the metadata associated with an image loaded
    through the GDAL interface.  This has the ability to populate an
    L{cube.Cube} with the parsed values from this text.
    """

    debug=True

    format_id="GDAL"
    format_name="GDAL"

    def __init__(self,filename=None,debug=False):
        self.url = None
        self.subsets=[]

        if filename:
            if isinstance(filename,cube.Cube):
                self.getCubeAttributes(filename)
            else:
                self.open(filename)
        
    def __str__(self):
        fs=StringIO()
        for subset in self.subsets:
            fs.write(str(subset))
        return fs.getvalue()

    @classmethod
    def identify(cls, urlinfo):
        if urlinfo.scheme == 'file':
            dprint("trying gdal.Open(%s)" % str(urlinfo.path))
            try:
                dataset=gdal.Open(str(urlinfo.path), gdal.GA_ReadOnly)
                if dataset:
                    dprint("found GDAL dataset")
                    return True
            except TypeError:
                dprint("type error opening GDAL.  Skipping")
        return False

    def setURL(self, url=None):
        if url:
            self.url = vfs.normalize(url)
        else:
            self.url = None

    def open(self, filename=None):
        """Open the header file, and if successful parse it."""
        if filename:
            self.setURL(filename)

        if self.url:
            dprint(self.url.path)
            try:
                dataset=gdal.Open(str(self.url.path), gdal.GA_ReadOnly)
                if dataset:
                    self.read(dataset)
                else:
                    eprint("Couldn't open %s\n" % self.url)
            except TypeError:
                dprint("type error opening GDAL.  Skipping")

    def save(self, url=None):
        if url:
            dprint("Save not implemented yet!\n")

    def read(self,dataset):
        subset={}
        subset['samples']=dataset.RasterXSize
        subset['lines']=dataset.RasterYSize
        subset['bands']=dataset.RasterCount

        # Can different bands within the same subset have different
        # data types?  In theory it looks possible.  But, for now,
        # assume everything has the same type as the first band.
        band=dataset.GetRasterBand(1)
        subset['data_type']=GDALDataType[band.DataType]
        dprint(subset)
        self.subsets.append(subset)

    def setCubeAttributes(self,cube):
        cube.samples=self.subsets[0]['samples']
        cube.lines=self.subsets[0]['lines']
        cube.bands=self.subsets[0]['bands']
        cube.data_type=self.subsets[0]['data_type']

        cube.subcubes=len(self.subsets)
        dprint("adjusted number of subcubes to %s" % cube.subcubes)
        cube.setURL(self.url)

    def getCubeAttributes(self,cube):
        # transfer attributes from cube to self
        pass
    
    def getCube(self,filename=None,index=0):
        if filename is None:
            filename = self.url
        cube=GDALCube(filename)
        dprint(cube)
        self.setCubeAttributes(cube)
        cube.verifyAttributes()
        cube.open()
        return cube

    def write(self,fh):
        pass


class GDALCube(cube.Cube):
    def __init__(self,filename=None):
        cube.Cube.__init__(self,filename)

        self.interleave='bsq'
        
        # If this is a hypertemporal image, each frame might have
        # different parameters (sizes, byte order, etc.)  This is a
        # list of Frame objects.
        self.frames=None

        self.framenum=0
        self.frame=None
        self.lastframe=None

        self.rgbbands=[0]

        self.dataset=None
        self.mmap=None
        self.raw=None
        self.slice=None

    def open(self,filename=None):
        if filename:
            self.setURL(filename)

        if self.url:
            if not self.dataset: # don't try to reopen if already open
                self.dataset=gdal.Open(str(self.url.path), gdal.GA_ReadOnly)
                if not self.dataset:
                    raise TypeError
                self.verifyAttributes()
                self.scanGDAL()
    
    def save(self,filename=None):
        if filename:
            self.setURL(filename)

        if self.url:
            pass

    def guessDisplayBands(self):
        """Guess the best bands to display a false-color RGB image
        using the wavelength info from the cube's metadata."""
        return self.rgbbands
        
    def scanGDAL(self):
        """Try to guess stuff from the GDAL metadata."""
        rgb=[-1,-1,-1]
        count=0
        for band in range(self.bands):
            b=self.dataset.GetRasterBand(band+1)
            color=b.GetRasterColorInterpretation()
            dprint("checking band %d; color interp=%d" % (band,color))
            if color==gdal.GCI_RedBand:
                rgb[0]=band
                count+=1
            elif color==gdal.GCI_GreenBand:
                rgb[1]=band
                count+=1
            elif color==gdal.GCI_BlueBand:
                rgb[2]=band
                count+=1
        if count>=3:
            self.rgbbands=rgb
        dprint(self.rgbbands)

    def getPixel(self,line,sample,band):
        bytes=self.dataset.ReadRaster(sample, line, 1, 1, band_list=[band+1])
        s=numpy.frombuffer(bytes, self.data_type)
        return s[0]

    def getBandRaw(self,band):
        """Get an array of (lines x samples) at the specified band"""
        # FIXME: load self.current to with the specified band
        b=self.dataset.GetRasterBand(band+1)
        bytes=b.ReadRaster(0,0,self.samples,self.lines)
        s=numpy.frombuffer(bytes, self.data_type)
        s=numpy.reshape(s,(self.lines,self.samples))
        return s

    def getSpectraRaw(self,line,sample):
        """Get the spectra at the given pixel"""
        datatype = self.dataset.GetRasterBand(1).DataType
        bytes=self.dataset.ReadRaster(sample, line, 1, 1, buf_type=datatype)
        s=numpy.frombuffer(bytes, self.data_type)
        return s

HyperspectralFileFormat.addDefaultHandler(GDALDataset)


if __name__ == "__main__":
    from optparse import OptionParser
    usage="usage: %prog [files...]"
    parser=OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    print options

    if args:
        for filename in args:
            GDALDataset.debug=True
            h=cube.loadHeader(filename)
            print h
            cube=h.getCube()
            print cube
            r=cube.getBand(0)
            print r
    else:
        print parser.usage
