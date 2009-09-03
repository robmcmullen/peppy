# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utilities used to create a simulated reflectance cube

"""
import os, os.path, sys

from peppy.debug import *
import peppy.vfs as vfs
import peppy.hsi.common as HSI
import peppy.hsi.ENVI as ENVI
from peppy.hsi.spectra import *

import numpy

class SimulatedCube(debugmixin):
    def __init__(self, lines, samples, bands, datatype=numpy.float32, scale=1000):
        self.cube = HSI.createCube('bip', lines, samples, bands, datatype)
        self.output_interleave = 'bil'
        self.scale = scale
        self.spectra = {}
    
    def save(self, url):
        dprint("Saving to %s" % url)
        fh = vfs.open_write(url)
        self.cube.writeRawData(fh, options={'interleave': self.output_interleave})
        enviheader = ENVI.Header()
        enviheader.getCubeAttributes(self.cube)
        enviheader['interleave'] = self.output_interleave
        pathname = str(url) + ".hdr"
        enviheader.save(pathname)
    
    def addSpectralLibrary(self, url, scale=1000):
        sli = Spectra.loadSpectraFromSpectralLibrary(url, scale)
        for spectra in sli:
            if spectra.name in self.spectra:
                wprint("%d already exists in spectra list" % spectra.name)
            else:
                self.spectra[spectra.name] = spectra
        #dprint([str(s) for s in self.spectra.values()])
    
    def setSpectralLibraryScale(self, scale=1000):
        """Set the scale factor for all spectra
        
        """
        for spectra in self.spectra.values():
            spectra.scale = scale
    
    def clearSpectralLibrary(self):
        self.spectra = {}
    
    def getSpectra(self, name):
        try:
            spectra = self.spectra[name]
        except:
            eprint("Unknown spectra name %s" % name)
            return None
        if self.cube.wavelengths and (self.cube.bands != len(spectra.wavelengths) or self.cube.wavelengths != spectra.wavelengths):
            wprint("Resampling %d spectra wavelengths to match data cube's %d wavelengths" % (len(spectra.wavelengths), self.cube.bands))
            spectra = self.resampleSpectra(spectra)
        return spectra
    
    def resampleSpectra(self, spectra):
        #dprint(spectra.wavelengths)
        #dprint(self.cube.wavelengths)
        values = HSI.resampleSingle(self.cube.wavelengths,
                                    spectra.wavelengths, spectra.values, self.cube.bbl)
        #dprint(values)
        #dprint("Number of values: %d" % len(values))
        s = Spectra()
        s.wavelengths = self.cube.wavelengths[:]
        s.fwhm = self.cube.fwhm[:]
        s.values = values
        s.scale = spectra.scale
        return s
    
    def getScaledValues(self, spectra):
        """Return the spectral values properly scaled for the output cube
        
        The output values depends on the scale factor used to define 100%
        reflectance in the spectral definition, and the scale factor used to
        define 100% reflectance in the output cube.
        
        @return: list of values in a float32 array
        """
        values = numpy.array(spectra.values, dtype=numpy.float32)
        #dprint("raw: %s" % str(values))
        values /= spectra.scale
        #dprint("reflectance: %s" % str(values))
        values *= self.scale
        #dprint("scaled to output: %s" % str(values))
        return values
    
    def setWavelengthsFromSpectra(self, spectra):
        """Set the wavelength parameters based on the given spectra
        
        """
        self.cube.wavelengths = spectra.wavelengths[:]
        self.cube.bbl = spectra.bbl[:]
        self.cube.fwhm = spectra.fwhm[:]
    
    def setBackground(self, name):
        spectra = self.getSpectra(name)
        if spectra:
            if not self.cube.wavelengths:
                self.setWavelengthsFromSpectra(spectra)
                
            data = self.cube.getNumpyArray()
            values = self.getScaledValues(spectra)
            #dprint(values)
            #dprint(data.shape)
            #dprint(values.shape)
            # This assignment only works when the cube is in BIP order, because
            # that is when the in-memory order puts bands as the last axis.  I
            # can't find a way to set the middle axis to an array.  So, it only
            # works when the data is set up as (lines, samples, bands) in memory
            # rather than (lines, bands, samples) for instance.
            data[:,:,:] = values
    
    def setSquare(self, name, sample, line, size):
        """Define a square of the named spectra
        
        @param name: name of spectra previous loaded by a spectral library
        
        @param sample: center pixel sample location
        
        @param line: center pixel line location
        
        @param size: number of pixels across the square.  Must be odd.
        """
        spectra = self.getSpectra(name)
        if spectra:
            data = self.cube.getNumpyArray()
            values = self.getScaledValues(spectra)
            half = size / 2
            s1 = max(sample - half, 0)
            s2 = min(sample + half, self.cube.samples - 1) + 1
            l1 = max(line - half, 0)
            l2 = min(line + half, self.cube.lines - 1) + 1
            #dprint(values)
            #dprint(data.shape)
            #dprint(values.shape)
            # This assignment only works when the cube is in BIP order, because
            # that is when the in-memory order puts bands as the last axis.  I
            # can't find a way to set the middle axis to an array.  So, it only
            # works when the data is set up as (lines, samples, bands) in memory
            # rather than (lines, bands, samples) for instance.
            data[l1:l2,s1:s2,:] = values

