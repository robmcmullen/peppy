# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Reading and writing raw HSI cubes.

This class supports reading HSI data cubes (that are stored in raw,
uncompressed formats) using memory mapped file access.
"""

import os,sys,re,random, glob
from cStringIO import StringIO
from datetime import datetime

import numpy
import utils

import peppy.vfs as vfs

from peppy.debug import *


# ENVI standard byte order: 0=little endian, 1=big endian
LittleEndian=0
BigEndian=1
if sys.byteorder=='little':
    nativeByteOrder=LittleEndian
else:
    nativeByteOrder=BigEndian
byteordertext=['<','>']


class MetadataMixin(debugmixin):
    """Generic mixin interface for Cube metadata.

    This will be subclassed by various formats like ENVI and GDAL to
    load the metadata from files and to provide a method to load the
    cube data.
    """

    format_name="unknown"
    extensions=[]

    @classmethod
    def identify(cls, fh, filename=None):
        """Scan through the file-like object to identify if it is a
        valid instance of the type that the subclass is expecting to
        load."""
        return False
    
    @classmethod
    def canExport(cls):
        return False
    
    @classmethod
    def export(cls, fh, cube, options, url):
        """Create a new file with the given cube.
        
        @param fh: file-like object to which the data should be written
        @param cube: HSI.Cube object to be saved
        @param options: dict containing name value pairs that can override the cube data to provide for data conversion on output (e.g. change the interleave from BIP to BIL)
        @param url: url of the file-like object
        """
        pass

    def formatName(self):
        return self.format_name

    def fileExtensions(self):
        return self.extensions
    
    def open(self,filename=None):
        pass

    def save(self,filename=None):
        pass
    
    def getCube(self, filename=None, index=None, progress=None, options=None):
        """Return a cube instance that represents the data pointed to
        by the metadata."""
        return None

    def getCubeNames(self):
        """Return names of cubes contained within this file.

        Return a list of names that identify the cubes contained
        within this file.
        """
        return []

    def getNumCubes(self):
        return len(self.getCubeNames())
    
    def __str__(self):
        fs=StringIO()
        order=self.keys()
        if self.debug: dprint("keys in object: %s" % order)
        order.sort()
        for key in order:
            val=self[key]
            fs.write("%s = %s%s" % (key,val,os.linesep))
        return fs.getvalue()


class CubeReader(debugmixin):
    """Abstract class for reading raw data from an HSI cube"""
    def save(self, url):
        """Save the data to another file"""
        raise NotImplementedError
        
    def getPixel(self, line, sample, band):
        """Get a single pixel value"""
        raise NotImplementedError

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        raise NotImplementedError

    def getSpectraRaw(self, line, sample):
        """Get the spectra (bands) at the given pixel"""
        raise NotImplementedError

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) at the given line"""
        raise NotImplementedError

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of (lines) at the given sample and band"""
        raise NotImplementedError

    def getLineOfSpectraCopy(self, line):
        """Get the spectra (samples x bands) along the given line"""
        # Default implementation is to use the transpose of getFocalPlaneRaw,
        # but it's possible that this could be overridden to provide a more
        # optimized version
        s = self.getFocalPlaneRaw().T
        return s.copy()

    def locationToFlat(self,line,sample,band):
        """Convert location (line,sample,band) to flat index"""
        raise NotImplementedError
    
    def getBytesFromArray(self, band, swap=False):
        """Get raw bytes from the band, swapping endian state if desired
        
        @param band: array of bytes from getBandRaw, getFocalPlaneRaw, etc.
        
        @param swap: if True, swap the endian state
        """
        raise NotImplementedError


class BIPMixin(object):
    def getBandBoundary(self):
        return 1

    def flatToLocation(self,pos):
        line=pos/(self.bands*self.samples)
        temp=pos%(self.bands*self.samples)
        sample=temp/self.bands
        band=temp%self.bands
        return (line,sample,band)

    def locationToFlat(self,line,sample,band):
        pos=line*self.bands*self.samples + sample*self.bands + band
        return pos

class BILMixin(object):
    def getBandBoundary(self):
        return self.samples

    def flatToLocation(self,pos):
        line=pos/(self.bands*self.samples)
        temp=pos%(self.bands*self.samples)
        band=temp/self.samples
        sample=temp%self.samples
        return (line,sample,band)

    def locationToFlat(self,line,sample,band):
        pos=line*self.bands*self.samples + band*self.samples + sample
        return pos

class BSQMixin(object):
    def getBandBoundary(self):
        return self.samples*self.lines

    def flatToLocation(self,pos):
        band=pos/(self.lines*self.samples)
        temp=pos%(self.lines*self.samples)
        line=temp/self.samples
        sample=temp%self.samples
        return (line,sample,band)

    def locationToFlat(self,line,sample,band):
        pos=band*self.lines*self.samples + line*self.samples + sample
        return pos


class FileCubeReader(CubeReader):
    """Base class for direct file access to data cube.
    
    Note: this is (potentially much) slower than mmap access of the
    L{MMapCubeReader}, but won't throw out of memory exceptions.
    """
    def __init__(self, cube, url=None, array=None):
        self.fh = vfs.open(url)
        # If we're using a WindowReader on a NITF file, the offset is already
        # accounted for within the WindowReader
        if hasattr(self.fh, 'offset') and self.fh.offset == cube.data_offset:
            self.offset = 0
        else:
            self.offset = cube.data_offset
        self.dprint("url=%s file=%s offset=%d" % (url, self.fh, self.offset))
        self.lines = cube.lines
        self.samples = cube.samples
        self.bands = cube.bands
        self.data_type = cube.data_type
        self.itemsize = cube.itemsize
        self.getProgressBar = cube.getProgressBar
        if cube.byte_order != nativeByteOrder:
            self.swap = True
        else:
            self.swap = False
    
    def getNumpyArrayFromFile(self, fh, count):
        """Convenience function to replace call to numpy.fromfile.
        
        Numpy can't use fromfile if the file handle is not an actual pointer to
        a file.  File handles returned by vfs.open can be file-like objects,
        so we have read the data by hand and use numpy.fromstring instead of
        numpy.fromfile directly.
        """
        bytes = fh.read(count * self.itemsize)
        s = numpy.fromstring(bytes, dtype=self.data_type, count=count)
        return s
    
    def getBytesFromArray(self, band, swap=False):
        # Because arrays used by FileCubeReaders are created on the fly during
        # calls to getBandRaw and the others, we can use byteswap to force the
        # bytes to change in the array itself.
        if swap:
            band = band.byteswap(False)
        return band.tostring()


class FileBIPCubeReader(BIPMixin, FileCubeReader):
    """Read a BIP format data cube using a file handle for direct access to
    the file.
    
    Offset into a BIP is calculated by:
    
    line * (num_samples * num_bands) + sample * (num_bands) + band
    """
    def getPixel(self, line, sample, band):
        fh = self.fh
        skip = (self.bands * self.samples) * line + (self.bands * sample) + band
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, 1)
        if self.swap:
            s.byteswap(True)
        return s[0]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        s = numpy.empty((self.lines, self.samples), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + (band * self.itemsize))
        
        # the amount to skip between successive reads will be one less than the
        # number of bands, because the file pointer advances by one item after
        # a read
        skip = self.itemsize * (self.bands - 1)
        samp = 0
        line = 0
        progress = self.getProgressBar(use_progress)
        if progress:
            progress.startProgress("Loading Band %d" % band, self.lines, delay=1.0)
        while True:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[line, samp] = data[0]
            samp += 1
            if samp >= self.samples:
                samp = 0
                line += 1
                if line >= self.lines:
                    break
                if progress:
                    progress.updateProgress(line)
            fh.seek(skip, 1)
        if progress:
            progress.stopProgress("Loaded Band %d" % band)
            
        if self.swap:
            s.byteswap(True)
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        fh = self.fh
        skip = (self.bands * self.samples) * line + (self.bands * sample)
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, self.bands)
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        fh = self.fh
        skip = (self.bands * self.samples) * line
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, (self.bands * self.samples))
        s = s.reshape(self.samples, self.bands).T
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values along a line, the given sample and band"""
        s = numpy.empty((self.lines,), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + (((self.bands * sample) + band) * self.itemsize))
        
        # amount to skip to read the next line at the same sample, band
        # coordinate is one less because the file pointer will have advanced
        # by one due to the file read
        skip = self.itemsize * ((self.samples * self.bands) - 1)
        line = 0
        while line < self.lines:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[line] = data[0]
            line += 1
            fh.seek(skip, 1)
            
        if self.swap:
            s.byteswap(True)
        return s


class FileBILCubeReader(BILMixin, FileCubeReader):
    """Read a BIL format data cube using a file handle for direct access to
    the file.
    
    Offset into a BIL is calculated by:
    
    line * (num_samples * num_bands) + band * (num_samples) + sample
    """
    def getPixel(self, line, sample, band):
        fh = self.fh
        skip = (self.bands * self.samples) * line + (self.samples * band) + sample
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, 1)
        if self.swap:
            s.byteswap(True)
        return s[0]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        s = numpy.empty((self.lines, self.samples), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + ((band * self.samples) * self.itemsize))
        
        # the amount to skip between successive reads will be less than the
        # number of bands * samples, because the file pointer advances by the
        # number of samples after a read
        skip = self.itemsize * ((self.samples * self.bands) - self.samples)
        samp = 0
        line = 0
        progress = self.getProgressBar(use_progress)
        if progress:
            progress.startProgress("Loading Band %d" % band, self.lines, delay=1)
        while True:
            data = self.getNumpyArrayFromFile(fh, self.samples)
            s[line, :] = data
            line += 1
            if line >= self.lines:
                break
            if progress:
                progress.updateProgress(line)
            fh.seek(skip, 1)
        if progress:
            progress.stopProgress("Loaded Band %d" % band)
            
        if self.swap:
            s.byteswap(True)
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        s = numpy.empty((self.bands,), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + ((((self.bands * self.samples) * line) + sample) * self.itemsize))
        
        # amount to skip to read the next band at the same line and sample,
        # less one because the file pointer will have advanced by one due to
        # the file read
        skip = self.itemsize * (self.samples - 1)
        band = 0
        while band < self.bands:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[band] = data[0]
            band += 1
            fh.seek(skip, 1)
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        fh = self.fh
        skip = (self.bands * self.samples) * line
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, (self.bands * self.samples))
        s = s.reshape(self.bands, self.samples)
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values along a line, the given sample and band"""
        s = numpy.empty((self.lines,), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + (((band * self.samples) + sample) * self.itemsize))
        
        # amount to skip to read the next line at the same sample, band
        # coordinate is one less because the file pointer will have advanced
        # by one due to the file read
        skip = self.itemsize * ((self.samples * self.bands) - 1)
        line = 0
        while line < self.lines:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[line] = data[0]
            line += 1
            fh.seek(skip, 1)
            
        if self.swap:
            s.byteswap(True)
        return s


class FileBSQCubeReader(BSQMixin, FileCubeReader):
    """Read a BSQ format data cube using a file handle for direct access to
    the file.
    
    Offset into a BSQ is calculated by:
    
    band * (num_samples * num_lines) + line * (num_samples) + sample
    """
    def getPixel(self, line, sample, band):
        fh = self.fh
        skip = (self.lines * self.samples) * band + (self.samples * line) + sample
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, 1)
        if self.swap:
            s.byteswap(True)
        return s[0]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        fh = self.fh
        skip = (self.lines * self.samples) * band
        fh.seek(self.offset + (skip * self.itemsize))
        s = self.getNumpyArrayFromFile(fh, (self.lines * self.samples))
        s = s.reshape(self.lines, self.samples)
        if self.swap:
            s.byteswap(True)
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        s = numpy.empty((self.bands,), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + (((self.samples * line) + sample) * self.itemsize))
        
        # amount to skip to read the next band at the same line and sample,
        # less one because the file pointer will have advanced by one due to
        # the file read
        skip = self.itemsize * ((self.samples * self.lines) - 1)
        band = 0
        while band < self.bands:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[band] = data[0]
            band += 1
            fh.seek(skip, 1)
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        s = numpy.empty((self.bands, self.samples), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + ((self.samples * line) * self.itemsize))

        # amount to skip to read the next band at the same line and sample,
        # less one because the file pointer will have advanced by one due to
        # the file read
        skip = (self.lines - 1) * self.samples * self.itemsize
        progress = self.getProgressBar(use_progress)
        if progress:
            progress.startProgress("Loading Focal Plane at line %d" % line, self.bands, delay=1)
        band = 0
        while True:
            data = self.getNumpyArrayFromFile(fh, self.samples)
            s[band, :] = data
            band += 1
            if band >= self.bands:
                break
            if progress:
                progress.updateProgress(band)
            fh.seek(skip, 1)
        if progress:
            progress.stopProgress("Loaded Focal Plane at line %d" % line)
        if self.swap:
            s.byteswap(True)
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values along a line, the given sample and band"""
        s = numpy.empty((self.lines,), dtype=self.data_type)
        fh = self.fh
        fh.seek(self.offset + (((band * self.samples * self.lines) + sample) * self.itemsize))
        
        # amount to skip to read the next line at the same sample, band
        # coordinate is one less because the file pointer will have advanced
        # by one due to the file read
        skip = self.itemsize * (self.samples - 1)
        line = 0
        while line < self.lines:
            data = self.getNumpyArrayFromFile(fh, 1)
            s[line] = data[0]
            line += 1
            fh.seek(skip, 1)
        if self.swap:
            s.byteswap(True)
        return s


def getFileCubeReader(cube):
    i = cube.interleave.lower()
    if i == 'bip':
        return FileBIPCubeReader
    elif i == 'bil':
        return FileBILCubeReader
    elif i == 'bsq':
        return FileBSQCubeReader
    else:
        raise TypeError("Unknown interleave %s" % interleave)



class MMapCubeReader(CubeReader):
    """Base class for memory mapped access to data cube using numpy's built-in
    mmap function.
    
    Note: this can fail with MemoryError (or WindowsError on MSW) when
    attempting to first mmap a file that is larger than physical memory.
    """
    def __init__(self, cube, url=None, array=None):
        self.mmap = None
        self.raw = None
        self.lines = cube.lines
        self.samples = cube.samples
        self.bands = cube.bands
        if url:
            self.open(cube, url)
        elif array is not None:
            self.raw = array
        
        if self.raw is not None:
            self.shape(cube)
    
#    def __str__(self):
#        return repr(self.raw)
    
    def open(self, cube, url):
        if url.scheme == "file":
            self.mmap = numpy.memmap(str(url.path), mode="r")
        elif url.scheme == "mem":
            fh = vfs.open(url)
            data = fh.read()
            self.mmap = numpy.fromstring(data, dtype=numpy.uint8)
        else:
            self.mmap = vfs.open_numpy_mmap(url)
        
        if cube.data_offset>0:
            if cube.data_bytes>0:
                slice = self.mmap[cube.data_offset:cube.data_offset+cube.data_bytes]
            else:
                slice = self.mmap[cube.data_offset:]
        else:
            slice = self.mmap[:]
                
        view = slice.view(cube.data_type)
        self.raw = view.newbyteorder(byteordertext[cube.byte_order])
    
    def getRaw(self):
        """Return the raw numpy array"""
        return self.raw
    
    def save(self, url):
        if self.mmap:
            self.mmap.flush()
            self.mmap.sync()
        else:
            self.raw.tofile(str(url.path))
    
    def shape(self, cube):
        """Shape the memory mapped to the correct data type and offset within
        the file."""
        raise NotImplementedError
    
    def getBytesFromArray(self, band, swap=False):
        # Unlike FileCubeReader, arrays from calls to getBandRaw and similar
        # methods are views into the entire mmap'd array and byteswapping
        # the individual arrays only creates a view.  Attempting a tostring()
        # call on those arrays results in the underlying bytes being generated
        # using the original order, not the byteswapped order that we want.
        if swap:
            if band.dtype.byteorder == ">":
                band.newbyteorder("<")
            else:
                band.newbyteorder(">")
        return band.tostring()


class MMapBIPCubeReader(BIPMixin, MMapCubeReader):
    def shape(self, cube):
        self.raw = numpy.reshape(self.raw, (cube.lines, cube.samples, cube.bands))

    def getPixel(self, line, sample, band):
        return self.raw[line][sample][band]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        s = self.raw[:, :, band]
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        s = self.raw[line, sample, :]
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        # Note: transpose doesn't seem to automatically generate a copy, so
        # we're safe with this transpose
        s = self.raw[line, :, :].T
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values at constant line, the given sample and band"""
        s = self.raw[:, sample, band]
        return s

    def getLineOfSpectraCopy(self, line):
        """Get the spectra along the given line"""
        s = self.raw[line, :, :].copy()
        return s


class MMapBILCubeReader(BILMixin, MMapCubeReader):
    def shape(self, cube):
        self.raw = numpy.reshape(self.raw, (cube.lines, cube.bands, cube.samples))

    def getPixel(self, line, sample, band):
        return self.raw[line][band][sample]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        s = self.raw[:, band, :]
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        s = self.raw[line, :, sample]
        return s
    
    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        s = self.raw[line, :, :]
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values at constant line, the given sample and band"""
        s = self.raw[:, band, sample]
        return s

    def getLineOfSpectraCopy(self, line):
        """Get the spectra along the given line"""
        # FIXME: transpose doesn't automatically generate a copy in the latest
        # numpy?
        s = numpy.transpose(self.raw[line, :, :].copy())
        return s


class MMapBSQCubeReader(BSQMixin, MMapCubeReader):
    def shape(self, cube):
        self.raw = numpy.reshape(self.raw, (cube.bands, cube.lines, cube.samples))

    def getPixel(self, line, sample, band):
        return self.raw[band][line][sample]

    def getBandRaw(self, band, use_progress=True):
        """Get an array of (lines x samples) at the specified band"""
        s = self.raw[band, :, :]
        return s

    def getSpectraRaw(self, line, sample):
        """Get the spectra at the given pixel"""
        s = self.raw[:, line, sample]
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        """Get an array of (bands x samples) the given line"""
        s = self.raw[:, line, :]
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get an array of values at constant line, the given sample and band"""
        s = self.raw[band, :, sample]
        return s

    def getLineOfSpectraCopy(self, line):
        """Get the spectra along the given line"""
        # FIXME: transpose doesn't automatically generate a copy in the latest
        # numpy?
        s = numpy.transpose(self.raw[:, line, :].copy())
        return s


def getMMapCubeReader(cube, check_size=True):
    if check_size:
        pixels = cube.samples * cube.lines * cube.bands
        if cube.mmap_size_limit > 0 and pixels > cube.mmap_size_limit:
            raise TypeError("Not using mmap for large cubes")
    i = cube.interleave.lower()
    if i == 'bip':
        return MMapBIPCubeReader
    elif i == 'bil':
        return MMapBILCubeReader
    elif i == 'bsq':
        return MMapBSQCubeReader
    else:
        raise TypeError("Unknown interleave %s" % interleave)


class Cube(debugmixin):
    """Generic representation of an HSI datacube.  Specific subclasses
    L{BILCube}, L{BIPCube}, and L{BSQCube} exist to fill in the
    concrete implementations of the common formats of HSI data.
    """

    # : mmap is the preferred method of accessing data.  If it's preferable
    # to use slower the direct file access method, set the size limit here.
    # Image sizes smaller than the limit specified here will be loaded using
    # mmap; otherwise will be loaded with direct file access
    mmap_size_limit = -1

    def __init__(self, filename=None, interleave='unknown', progress=None):
        self.url = None
        self.setURL(filename)
        
        self.samples=-1
        self.lines=-1
        self.bands=-1
        self.interleave = interleave.lower()
        self.sensor_type='unknown'

        # date/time metadata
        self.imaging_date = 0
        self.file_date = datetime.now()

        # absolute pointer to data within the file
        self.file_offset=0
        # number of header bytes to skip when reading the raw data
        # file (relative to file_offset)
        self.header_offset=0
        # data_offset = cube_offset + header_offset.  This is an
        # absolute pointer to the raw data within the file
        self.data_offset=0
        self.data_bytes=0 # number of bytes in the data part of the file

        # Data type is a numarray data type, one of: [None,Int8,Int16,Int32,Float32,Float64,Complex32,Complex64,None,None,UInt16,UInt32,Int64,UInt64]
        self.data_type=None

        self.byte_order = nativeByteOrder

        # per band information, should be lists of dimension self.bands
        self.wavelengths=[]
        self.bbl=[]
        self.fwhm=[]
        self.band_names=[]

        # wavelength units: 'nm' for nanometers, 'um' for micrometers,
        # None for unknown
        self.wavelength_units=None

        # scale_factor is the value by which the samples in the cube
        # have already been multiplied.  To get values in the range of
        # 0.0 - 1.0, you must B{divide} by this value.
        self.scale_factor=None
        
        # UTM Georeferencing information
        self.utm_zone = -1
        self.utm_origin = (0, 0)
        self.utm_pixel_size = (0, 0)
        self.utm_easting = 0
        self.utm_northing = 0

        # Lat/Long Georeferencing information
        self.georef_system = None
        self.georef_origin = (0, 0) # reference pixel location
        self.georef_pixel_size = (0, 0) # in degrees
        self.georef_lat = 0 # of upper left corner of pixel
        self.georef_long = 0 # of upper left corner of pixel

        self.description=''

        # data reader
        self.cube_io = None
        self.itemsize=0

        # calculated quantities
        self.spectraextrema=[None,None] # min and max over whole cube
        
        # progress bar indicator
        self.progress = progress


    def __str__(self):
        s=StringIO()
        s.write("""Cube: filename=%s
        description=%s
        data_offset=%d header_offset=%d file_offset=%d data_type=%s
        samples=%d lines=%d bands=%d data_bytes=%d
        interleave=%s byte_order=%d (native byte order=%d)\n""" % (self.url,self.description,self.data_offset,self.header_offset,self.file_offset,str(self.data_type),self.samples,self.lines,self.bands,self.data_bytes,self.interleave,self.byte_order,nativeByteOrder))
        if self.utm_zone >= 0:
            s.write("        utm: zone=%s easting=%f northing=%f\n" % (self.utm_zone, self.utm_easting, self.utm_northing))
        if self.scale_factor: s.write("        scale_factor=%f\n" % self.scale_factor)
        s.write("        wavelength units: %s\n" % self.wavelength_units)
        # s.write("        wavelengths: %s\n" % self.wavelengths)
        s.write("        bbl: %s\n" % self.bbl)
        # s.write("        fwhm: %s\n" % self.fwhm)
        # s.write("        band_names: %s\n" % self.band_names)
        s.write("        cube_io=%s\n" % str(self.cube_io))
        return s.getvalue()

    def fileExists(self):
        return vfs.exists(self.url)
                
    def isDataLoaded(self):
        return self.cube_io is not None

    def setURL(self, url=None):
        #dprint("setting url to %s" % url)
        if url:
            self.url = vfs.normalize(url)
        else:
            self.url=None
    
    @classmethod
    def getCubeReaderList(cls):
        """Return a list of cube readers"""
        return [getMMapCubeReader, getFileCubeReader]
    
    def getCubeReader(self):
        """Loop through all the potential cube readers and find the first one
        that works.
        """
        for cube_reader in self.getCubeReaderList():
            self.dprint("Trying %s" % cube_reader)
            try:
                reader = cube_reader(self)
            except TypeError, e:
                self.dprint(e)
                continue
            try:
                return reader(self, self.url)
            except OSError, e:
                # Caught what is most likely an out of memory error
                self.dprint(e)
                continue
        raise IndexError("No cube reader found")

    def open(self,url=None):
        if url:
            self.setURL(url)
            self.cube_io = None

        if self.url:
            if self.cube_io is None: # don't try to reopen if already open
                self.initialize()
                
                self.cube_io = self.getCubeReader()
                
                self.verifyAttributes()
        else:
            raise IOError("No url specified.")
    
    def save(self,url=None):
        if url:
            self.setURL(url)

        if self.url:
            self.cube_io.save(self.url)

    def initialize(self,datatype=None,byteorder=None):
        self.initializeSizes(datatype,byteorder)
        self.initializeOffset()

    def initializeOffset(self):
        if self.header_offset>0 or self.file_offset>0:
            if self.data_offset==0:
                # if it's not already set, set it
                self.data_offset=self.file_offset+self.header_offset

    def initializeSizes(self,datatype=None,byteorder=None):
        if datatype:
            self.data_type=datatype
        if byteorder:
            self.byte_order=byteorder
        
        # find out how many bytes per element in this datatype
        if self.data_type:
            self.itemsize=numpy.empty([1],dtype=self.data_type).itemsize

        # calculate the size of the raw data only if it isn't already known
        if self.data_bytes==0:
            self.data_bytes=self.itemsize*self.samples*self.lines*self.bands

    def verifyAttributes(self):
        """Clean up after loading a cube to make sure some values are
        populated and that everything that should have defaults does."""

        # supply reasonable scale factor
        if self.scale_factor == None:
            self.guessScaleFactor()

        # supply bad band list
        if not self.bbl:
            self.bbl=[1]*self.bands
        # dprint("verifyAttributes: bands=%d bbl=%s" % (self.bands,self.bbl))

        # guess wavelength units if not supplied
        if len(self.wavelengths)>0 and not self.wavelength_units:
            self.guessWavelengthUnits()

        if self.url is not None:
            self.file_date = vfs.get_mtime(self.url)

    

    def guessScaleFactor(self):
        """Try to supply a good guess as to the scale factor of the
        samples based on the type of the data"""
        if self.data_type in [numpy.int8,numpy.int16,numpy.int32,numpy.uint16,numpy.uint32,numpy.int64,numpy.uint64]:
            self.scale_factor=10000.0
        elif self.data_type in [numpy.float32, numpy.float64]:
            self.scale_factor=1.0
        else:
            self.scale_factor=1.0

    def guessDisplayBands(self):
        """Guess the best bands to display a false-color RGB image
        using the wavelength info from the cube's metadata."""
        if self.bands>=3 and len(self.wavelengths)>0:
            # bands=[random.randint(0,self.bands-1) for i in range(3)]
            bands=[self.getBandListByWavelength(wl)[0] for wl in (660,550,440)]

            # If all the bands are the same, then visible light isn't
            # within the wavelength region
            if bands[0]==bands[1] and bands[1]==bands[2]:
                bands=[bands[0]]
        else:
            bands=[0]
        return bands
        
    def guessWavelengthUnits(self):
        """Try to guess the wavelength units if the wavelength list is
        supplied but the units aren't."""
        if self.wavelengths[-1]<100.0:
            self.wavelength_units='um'
        else:
            self.wavelength_units='nm'
    
    def getWavelengthStr(self, band):
        if self.wavelengths and band >=0 and band < len(self.wavelengths):
            text = "%.2f %s" % (self.wavelengths[band], self.wavelength_units)
            return text
        return "no value"

    def getDescriptiveBandName(self, band):
        """Get a text string that describes the band.
        
        Use the wavelength array and the array of band names to create a text
        string that describes the band.
        """
        text = []
        if self.wavelengths and band >=0 and band < len(self.wavelengths):
            text.append(u"\u03bb=%.2f %s" % (self.wavelengths[band], self.wavelength_units))
        if self.band_names and band >=0 and band < len(self.band_names):
            text.append(unicode(self.band_names[band]))
        return u" ".join(text)

    def updateExtrema(self, spectra):
        mn=spectra.min()
        if self.spectraextrema[0]==None or mn<self.spectraextrema[0]:
            self.spectraextrema[0]=mn
        mx=spectra.max()
        if self.spectraextrema[1]==None or  mx>self.spectraextrema[1]:
            self.spectraextrema[1]=mx

    def getUpdatedExtrema(self):
        return self.spectraextrema

    def getPixel(self,line,sample,band):
        """Get an individual pixel at the specified line, sample, & band"""
        return self.cube_io.getPixel(line, sample, band)

    def getBand(self, band, use_progress=True):
        """Get a copy of the array of (lines x samples) at the
        specified band.  You are not working on the original data."""
        s = self.getBandInPlace(band, use_progress).copy()
        return s

    def getBandInPlace(self, band, use_progress=True):
        """Get the slice of the data array (lines x samples) at the
        specified band.  This points to the actual in-memory array."""
        s = self.getBandRaw(band, use_progress)
        self.updateExtrema(s)
        return s

    def getBandRaw(self, band, use_progress=True):
        return self.cube_io.getBandRaw(band, use_progress)

    def getFocalPlaneInPlace(self, line, use_progress=True):
        """Get the slice of the data array (bands x samples) at the specified
        line, which corresponds to a view of the data as the focal plane would
        see it.  This points to the actual in-memory array.
        """
        s = self.getFocalPlaneRaw(line, use_progress)
        self.updateExtrema(s)
        return s

    def getFocalPlaneRaw(self, line, use_progress=True):
        return self.cube_io.getFocalPlaneRaw(line, use_progress)

    def getFocalPlaneDepthInPlace(self, sample, band):
        """Get the slice of the data array through the cube at the specified
        sample and band.  This points to the actual in-memory array.
        """
        s=self.getFocalPlaneDepthRaw(sample, band)
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        return self.cube_io.getFocalPlaneDepthRaw(sample, band)

    def getSpectra(self,line,sample):
        """Get the spectra at the given pixel.  Calculate the extrema
        as we go along."""
        spectra=self.getSpectraInPlace(line,sample).copy()
        spectra*=self.bbl
        self.updateExtrema(spectra)
        return spectra
        
    def getSpectraInPlace(self,line,sample):
        """Get the spectra at the given pixel.  Calculate the extrema
        as we go along."""
        spectra=self.getSpectraRaw(line,sample)
        return spectra

    def getSpectraRaw(self,line,sample):
        """Get the spectra at the given pixel"""
        return self.cube_io.getSpectraRaw(line, sample)

    def getLineOfSpectra(self,line):
        """Get the all the spectra along the given line.  Calculate
        the extrema as we go along."""
        spectra=self.getLineOfSpectraCopy(line)
        spectra*=self.bbl
        self.updateExtrema(spectra)
        return spectra
        
    def getLineOfSpectraCopy(self,line):
        """Get the spectra along the given line.  Subclasses override
        this."""
        return self.cube_io.getLineOfSpectraCopy(line)

    def normalizeUnits(self,val,units):
        """Normalize a value in the specified units to the cube's
        default wavelength unit."""
        if not self.wavelength_units:
            return val
        cubeunits=utils.units_scale[self.wavelength_units]
        theseunits=utils.units_scale[units]
##        converted=val*cubeunits/theseunits
        converted=val*theseunits/cubeunits
        #dprint("val=%s converted=%s cubeunits=%s theseunits=%s" % (str(val),str(converted),str(cubeunits),str(theseunits)))
        return converted

    def normalizeUnitsTo(self,val,units):
        """Normalize a value given in the cube's default wavelength
        unit to the specified unit.
        """
        if not self.wavelength_units:
            return val
        cubeunits=utils.units_scale[self.wavelength_units]
        theseunits=utils.units_scale[units]
        converted=val*cubeunits/theseunits
        #dprint("val=%s converted=%s cubeunits=%s theseunits=%s" % (str(val),str(converted),str(cubeunits),str(theseunits)))
        return converted

    def getBandListByWavelength(self,wavelen_min,wavelen_max=-1,units='nm'):
        """Get list of bands between the specified wavelength, or if
        the wavelength range is too small, get the nearest band."""
        bandlist=[]
        if wavelen_max<0:
            wavelen_max=wavelen_min
        wavelen_min=self.normalizeUnits(wavelen_min,units)
        wavelen_max=self.normalizeUnits(wavelen_max,units)
        if len(self.wavelengths)==0:
            return bandlist
        
        for channel in range(self.bands):
            # dprint("wavelen[%d]=%f" % (channel,self.wavelengths[channel]))
            if (self.bbl[channel]==1 and
                  self.wavelengths[channel]>=wavelen_min and
                  self.wavelengths[channel]<=wavelen_max):
                bandlist.append(channel)
        if not bandlist:
            center=(wavelen_max+wavelen_min)/2.0
            if center<self.wavelengths[0]:
                for channel in range(self.bands):
                    if self.bbl[channel]==1:
                        bandlist.append(channel)
                        break
            elif center>self.wavelengths[self.bands-1]:
                for channel in range(self.bands-1,-1,-1):
                    if self.bbl[channel]==1:
                        bandlist.append(channel)
                        break
            else:
                for channel in range(self.bands-1):
                    if (self.bbl[channel]==1 and
                           self.wavelengths[channel]<center and
                           self.wavelengths[channel+1]>center):
                        if (center-self.wavelengths[channel] <
                               self.wavelengths[channel+1]-center):
                            bandlist.append(channel)
                            break
                        else:
                            bandlist.append(channel+1)
                            break
        return bandlist

    def getFlatView(self):
        """Get a flat, one-dimensional view of the data"""
        #self.flat=self.raw.view()
        #self.flat.setshape((self.raw.size()))
        #return self.raw.flat
        raise NotImplementedError

    def getBandBoundary(self):
        """return the number of items you have to add to a flat
        version of the data until you reach the next band in the data"""
        raise NotImplementedError

    def flatToLocation(self,pos):
        """Convert the flat index to a tuple of line,sample,band"""
        raise NotImplementedError

    def locationToFlat(self,line,sample,band):
        """Convert location (line,sample,band) to flat index"""
        return self.cube_io.locationToFlat(line, sample, band)
    
    def getBadBandList(self,other=None):
        if other:
            bbl2=[0]*self.bands
            for i in range(self.bands):
                if self.bbl[i] and other.bbl[i]:
                    bbl2[i]=1
            return bbl2
        else:
            return self.bbl
    
    def isFasterFocalPlane(self):
        return self.interleave in ["bip", "bil"]
    
    def isFasterBand(self):
        return self.interleave in ["bsq"]
    
    def iterFocalPlanes(self):
        """Iterate over all focal planes.
        
        Note that this will be slow when the cube is in BSQ format
        """
        for i in range(self.lines):
            fp = self.getFocalPlaneRaw(i, use_progress=False)
            yield fp
    
    def iterBands(self):
        """Iterate over all bands.
        
        Note that this will be slow when the cube is in BIL format, and
        extremely slow when the cube is BIP.
        """
        for i in range(self.bands):
            band = self.getBandRaw(i, use_progress=False)
            yield band
    
    def getNumpyArray(self):
        """Get a pointer to the raw numpy array if it's capable"""
        if hasattr(self.cube_io, 'getRaw'):
            return self.cube_io.getRaw()
        raise TypeError("Cube is not using numpy to store its data")
    
    def iterRawBIP(self, swap):
        # bands vary fastest, then samples, then lines
        for i in range(self.lines):
            band = self.cube_io.getFocalPlaneRaw(i, use_progress=False).transpose()
            bytes = self.cube_io.getBytesFromArray(band, swap)
            yield bytes
    
    def iterRawBIL(self, swap):
        # samples vary fastest, then bands, then lines
        for i in range(self.lines):
            band = self.cube_io.getFocalPlaneRaw(i, use_progress=False)
            bytes = self.cube_io.getBytesFromArray(band, swap)
            yield bytes
    
    def iterRawBSQ(self, swap):
        # samples vary fastest, then lines, then bands 
        for i in range(self.bands):
            band = self.cube_io.getBandRaw(i, use_progress=False)
            bytes = self.cube_io.getBytesFromArray(band, swap)
            yield bytes
    
    def iterRaw(self, size, interleaveiter, byte_order=None):
        """Iterator used to return the raw data of the cube in manageable chunks.
        
        Uses one of L{iterRawBIP}, L{iterRawBIL}, or L{iterRawBSQ} to grab the
        next chunk of data.  Once there are enough bytes to fill the requested
        size, the bytes are yielded to the calling function.  This loop
        continues until all the data has been returned to the caller.
        
        @param size: length of buffer to return at each iteration (note the
        final iteration may be shorter)
        
        @param iterleaveiter: an interleave functor taking no arguments and
        yielding chunks of data at each iteration
        
        @param byte_order: the desired byte order of the output data
        """
        fh = StringIO()
        i = 0
        if byte_order is None:
            byte_order = self.byte_order
        elif byte_order == '<':
            byte_order = LittleEndian
        elif byte_order == '>':
            byte_order = BigEndian
        swap = bool(byte_order != nativeByteOrder)
        for bytes in interleaveiter(swap):
            count = len(bytes)
            if (i + count) < size:
                fh.write(bytes)
                i += len(bytes)
            else:
                bi = 0
                while bi < count:
                    remaining_bytes = count - bi
                    unfilled = size - i
                    if remaining_bytes < unfilled:
                        fh.write(bytes[bi:])
                        i += remaining_bytes
                        break
                    fh.write(bytes[bi:bi + unfilled])
                    yield fh.getvalue()
                    bi += unfilled
                    fh = StringIO()
                    i = 0
        leftover = fh.getvalue()
        if len(leftover) > 0:
            yield leftover
    
    def getRawIterator(self, block_size, interleave=None, byte_order=None):
        """Get an iterator to return the raw data of the cube in manageable
        chunks.
        
        The blocks of data returned by this iterator are in the interleave
        order supplied.  If no interleave is supplied, the current interleave
        is used.
        
        @param block_size: size of data chunks to be returned
        @param interleave: string, one of 'bip', 'bil', or 'bsq'
        @return: iterator used to loop over blocks of data, or None if unknown
        interleave
        """
        if interleave is None:
            interleave = self.interleave
        iter = {'bip': self.iterRawBIP,
                'bil': self.iterRawBIL,
                'bsq': self.iterRawBSQ,
                }.get(interleave.lower(), None)
        if iter:
            return self.iterRaw(block_size, iter, byte_order)
        return None
    
    def writeRawData(self, fh, options=None, progress=None, block_size=100000):
        if options is None:
            options = dict()
        interleave = options.get('interleave', self.interleave)
        byte_order = options.get('byte_order', self.byte_order)
        num_blocks = (self.data_bytes / block_size) + 1
        iterator = self.getRawIterator(block_size, interleave, byte_order)
        if iterator:
            count = 0
            for block in iterator:
                fh.write(block)
                if progress:
                    progress((count * 100) / num_blocks)
                count += 1
        else:
            raise ValueError("Unknown interleave %s" % interleave)

    def registerProgress(self, progress):
        """Register the progress bar that cube functions may use when needed.
        
        The progress bar should conform to the L{ModularStatusBarInfo} progress
        bar methods.
        """
        self.progress = progress

    def getProgressBar(self, use_progress=True):
        """Return the progress bar generator previously registered with this
        cube.
        
        @param use_progress: Defaults to True, but if False will cause this
        method to return None.  This is used to override the progress bar if
        in some long running calculation that also uses the progress bar and
        you don't want the band loading code to use the progress bar for each
        band.
        """
        return use_progress and self.progress
    
    
    #### Utility functions
    def getRGBImage(self):
        """Return a 3-band image suitable for further conversion into a JPEG.
        
        """
        rgb = self.guessDisplayBands() # returned in r,g,b order
        rgb.reverse() # need to get it in increasing wavelength b,g,r order
        image = createCube('bsq', self.lines, self.samples,
                                 len(rgb), numpy.uint16, self.byte_order,
                                 self.scale_factor)
        index = 0
        for i in rgb:
            image.wavelengths.append(self.wavelengths[i])
            store = image.getBandRaw(index)
            source = self.getBandRaw(i)
            store[:,:] = source[:,:]
            index += 1
        return image


def newCube(interleave, url=None, progress=None):
    cube = Cube(url, interleave, progress=progress)
    return cube

def createCube(interleave,lines,samples,bands,datatype=None, byteorder=nativeByteOrder, scalefactor=10000.0, data=None, dummy=False, progress=None):
    if datatype == None:
        datatype = numpy.int16
    cube = newCube(interleave, None, progress)
    cube.interleave=interleave
    cube.samples=samples
    cube.lines=lines
    cube.bands=bands
    cube.data_type=datatype
    cube.byte_order=byteorder
    cube.scale_factor=scalefactor
    cube.initialize(datatype,byteorder)
    
    cube_io_cls = getMMapCubeReader(cube, check_size=False)
    if not dummy:
        if data:
            raw = numpy.frombuffer(data, datatype)
        else:
            raw = numpy.zeros((samples*lines*bands), dtype=datatype)
    else:
        raw = None
    cube.cube_io = cube_io_cls(cube, array=raw)
    cube.verifyAttributes()
    return cube

def createCubeLike(other, interleave=None, lines=None, samples=None, bands=None, datatype=None, byteorder=None, data=None):
    if interleave is None:
        interleave = other.interleave
    cube = newCube(interleave, None)
    if samples is None:
        cube.samples = other.samples
    else:
        cube.samples = samples
    if lines is None:
        cube.lines = other.lines
    else:
        cube.lines = lines
    if bands is None:
        cube.bands = other.bands
    else:
        cube.bands = bands
    if datatype is None:
        datatype = other.data_type
    if byteorder is None:
        byteorder = other.byte_order
    cube.initialize(datatype, byteorder)
    
    cube_io_cls = getMMapCubeReader(cube, check_size=False)
    if data:
        raw = numpy.frombuffer(data, datatype)
    else:
        raw = numpy.zeros((cube.samples*cube.lines*cube.bands), dtype=datatype)
    cube.cube_io = cube_io_cls(cube, array=raw)
    cube.verifyAttributes()
    return cube


if __name__ == "__main__":
    c=BIPCube()
    c.samples=5
    c.lines=4
    c.bands=3
    c.raw=array(arange(c.samples*c.lines*c.bands))
    c.shape()
    print c.raw
    print c.getPixel(0,0,0)
    print c.getPixel(0,0,1)
    print c.getPixel(0,0,2)
