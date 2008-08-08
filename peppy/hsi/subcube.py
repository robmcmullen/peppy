# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Synthetic cubes made from subsets of other cubes

This wrapper allows datasets to be created from subsets of other cubes, so that
to the hyperspectral code it appears to be a new dataset.
"""

import os,os.path,sys,re,struct,stat
from cStringIO import StringIO

import peppy.hsi.common as HSI
import peppy.vfs as vfs
from peppy.debug import *
import numpy


class SubDataset(HSI.MetadataMixin):
    """Synthetic dataset representing a subset of another dataset
    """
    format_id="SubDataset"
    format_name="SubDataset"

    def __init__(self, cube):
        self.cube = cube
        
    def __str__(self):
        fs=StringIO()
        fs.write("Subset of cube %s" % self.cube)
        return fs.getvalue()

    @classmethod
    def identify(cls, url):
        return url.scheme == 'dataset'

    def save(self, url=None):
        if url:
            dprint("Save not implemented yet!\n")

    def getCube(self, filename=None, index=0, progress=None, options=None):
        self.dprint(filename)
        return self.cube

    def write(self,fh):
        pass


class SubCube(HSI.Cube):
    def __init__(self, parent=None):
        HSI.Cube.__init__(self)
        self.setParent(parent)

    def setParent(self, parent):
        self.parent = parent
        #self.parent.progress = None
        self.clearSubset()

        # date/time metadata
        self.imaging_date = parent.imaging_date
        self.file_date = parent.file_date

        self.interleave = parent.interleave
        self.byte_order = parent.byte_order
        self.data_bytes = 0 # will be calculated when subset is defined
        self.data_type = parent.data_type

        # wavelength units: 'nm' for nanometers, 'um' for micrometers,
        # None for unknown
        self.wavelength_units = parent.wavelength_units

        self.description = parent.description

        self.rgbbands=[0]
        
    def open(self, url=None):
        pass

    def save(self,filename=None):
        if filename:
            self.setURL(filename)

        if self.url:
            pass

    def clearSubset(self):
        self.lines = self.parent.lines
        self.l1 = 0
        self.l2 = self.lines
        
        self.samples = self.parent.samples
        self.s1 = 0
        self.s2 = self.samples
        
        self.bands = self.parent.bands
        self.b1 = 0
        self.b2 = self.bands
        
        self.data_type = None
        self.data_bytes = 0
        self.byte_order = HSI.nativeByteOrder
        
        self.wavelengths = self.parent.wavelengths[:]
        self.bbl = self.parent.bbl[:]
        self.fwhm = self.parent.fwhm[:]
        self.band_names = self.parent.band_names[:]

    def subset(self, l1, l2, s1, s2, b1, b2):
        """Subset the parent cube by line, sample, and band"""
        self.lines = l2 - l1
        self.l1 = l1
        self.l2 = l2
        
        self.samples = s2 - s1
        self.s1 = s1
        self.s2 = s2
        
        self.bands = b2 - b1
        self.b1 = b1
        self.b2 = b2
        
        self.initializeSizes()
        
        self.wavelengths = self.parent.wavelengths[self.b1:self.b2]
        self.bbl = self.parent.bbl[self.b1:self.b2]
        self.fwhm = self.parent.fwhm[self.b1:self.b2]
        self.band_names = self.parent.band_names[self.b1:self.b2]
        
    def getPixel(self, line, sample, band):
        """Get an individual pixel at the specified line, sample, & band"""
        return self.parent.getPixel(self.l1 + line, self.s1 + sample, self.b1 + band)

    def getBandRaw(self, band):
        """Get the slice of the data array (lines x samples) at the
        specified band.  This points to the actual in-memory array."""
        s=self.parent.getBandRaw(self.b1 + band)[self.l1:self.l2, self.s1:self.s2]
        return s

    def getFocalPlaneRaw(self, line):
        """Get the slice of the data array (bands x samples) at the specified
        line, which corresponds to a view of the data as the focal plane would
        see it.  This points to the actual in-memory array.
        """
        s=self.parent.getFocalPlaneRaw(self.l1 + line)[self.b1:self.b2, self.s1:self.s2]
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get the slice of the data array through the cube at the specified
        sample and band.  This points to the actual in-memory array.
        """
        s=self.parent.getFocalPlaneDepthRaw(self.s1 + sample, self.b1 + band)[self.l1:self.l2]
        return s

    def getSpectraRaw(self,line,sample):
        """Get the spectra at the given pixel.  Calculate the extrema
        as we go along."""
        spectra=self.parent.getSpectraRaw(self.l1 + line, self.s1 + sample)[self.b1:self.b2]
        return spectra

    def getLineOfSpectraCopy(self,line):
        """Get the all the spectra along the given line.  Calculate
        the extrema as we go along."""
        spectra=self.parent.getLineOfSpectraCopy(self.l1 + line)[self.s1:self.s2, self.b1:self.b2]
        return spectra

    def locationToFlat(self, line, sample, band):
        return -1

HSI.HyperspectralFileFormat.addDefaultHandler(SubDataset)


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
