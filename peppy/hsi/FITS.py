# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Interface to the hsi module to load cubes in FITS format.

U{FITS<http://fits.gsfc.nasa.gov>} is a simple file format that allows storage
of multiple datasets in a single file.  It is commonly used in astronomy, but
can be used to store arbitrary multi-dimensional arrays.
"""

import os,os.path,sys,re,struct,stat
from cStringIO import StringIO

import peppy.hsi.common as HSI
import peppy.vfs as vfs
from peppy.debug import *

import numpy

class FITSHDU(debugmixin):
    """Header Data Unit (HDU) parser for FITS files.
    """
    def __init__(self, fh):
        """Create a HDU object from a file handle.
        
        The file handle should point to an open file at the start of a 2880
        byte record.
        """
        self.keywords = {}
        self.image_size = 0
        self.image_axes = []
        self.image_bpp = 0
        self.image_offset = 0
        self.image_end = 0
        self.parse(fh)
    
    def __str__(self):
        sorted = self.keywords.keys()
        sorted.sort()
        #return "\n".join("%s = %s" % (k, self.keywords[k]) for k in sorted)
        return "Image: size=%d naxis=%d %s bpp=%d offset=%d end=%d" % (self.image_size, self.keywords['NAXIS'], self.image_axes, self.image_bpp, self.image_offset, self.image_end)
    
    def parse(self, fh):
        """Parse a single HDU block
        """
        while True:
            chunk = fh.read(2880)
            if not chunk:
                raise IOError("End of file")
            end = self.parseKeywords(chunk)
            if end:
                break
        size = self.calcSize()
        if size:
            self.image_offset = fh.tell()
            blocks = (size + 2879) / 2880
            fh.seek(blocks * 2880, 1)
            self.image_end = fh.tell() - 1
    
    def parseKeywords(self, chunk):
        """Parse a 2880 byte header record for keywords
        
        @return: True if the end of record is found; false if another header
        record block should be read
        """
        i = 0
        while i < 2880:
            keyword = chunk[i:i+8].strip()
            if keyword == 'END':
                return True
            equals = chunk[i+8:i+10]
            if equals == '= ':
                value = self.getValue(chunk[i+10:i+80])
                self.dprint("%s = %s" % (repr(keyword), repr(value)))
                self.keywords[keyword] = value
            i += 80
        return False
    
    def getValue(self, text):
        """Get an appropriately typed data value from the given text
        
        FITS has enough constraints on the data that we should be able to tell
        what type of data it is simply because of the way that the value is
        formatted.  For example, strings always start with a single quote
        character ('), booleans are always the single character 'T' or 'F',
        etc.
        """
        text = text.strip()
        value = None
        if text[0] == "'":
            value = text
        elif text[0] in ['T', 't']:
            value = True
        elif text[0] in ['F', 'f']:
            value = False
        else:
            if '/' in text:
                text = text.split('/')[0].strip()
            if '.' in text or 'E' in text:
                value = float(text)
            else:
                value = int(text)
        return value
    
    def calcSize(self):
        """Calculate the image size, if there is an image in this HDU
        """
        if self.keywords['NAXIS'] > 0:
            self.image_bpp = abs(self.keywords['BITPIX'])
            size = self.image_bpp / 8
            self.image_axes = []
            for i in range(self.keywords['NAXIS']):
                k = 'NAXIS%d' % (i + 1)
                axis = self.keywords[k]
                self.image_axes.append(axis)
                size *= axis
            self.image_size = size
            return size
        return 0
    
    def getNumPyDataType(self):
        """Convenience function to return the numpy data type of the image
        """
        dtype = {8: numpy.uint8,
                16: numpy.int16,
                32: numpy.int32,
                -32: numpy.float32,
                -64: numpy.float64,
                }
        if self.keywords['BITPIX'] in dtype:
            return dtype[self.keywords['BITPIX']]
        raise TypeError("Unknown data type in FITS file")
    
    def getInterleave(self):
        """Convenience function to return the pixel ordering
        """
        return "bsq"


class FITSDataset(HSI.MetadataMixin):
    """FITS dataset parser to populate an L{HSI.Cube}.
    
    FITS files start with a defined keyword order, and all lines are 80
    characters without any end of line indicators:
    
    SIMPLE  =                    T
    BITPIX  =                   16
    NAXIS   =                    0
    """
    format_id="FITS"
    format_name="FITS"

    @classmethod
    def identify(cls, url, filename=None):
        fh = vfs.open(url)
        line=fh.read(160)
        cls.dprint(repr(line))
        if line[0:30] =='SIMPLE  =                    T' and line[80:90] == 'BITPIX  = ':
            return True
        return False

    def __init__(self, filename=None, **kwargs):
        self.url = None
        self.hdus = []

        if filename:
            if isinstance(filename, HSI.Cube):
                self.getCubeAttributes(filename)
            else:
                self.open(filename)
    
    def __str__(self):
        if self.hdus:
            return "\n".join(str(hdu) for hdu in self.hdus)
        return "No HDUs"
        
    def setURL(self, url=None):
        if url:
            self.url = vfs.normalize(url)
        else:
            self.url = None

    def open(self, url=None):
        """Open the header file, and if successful parse it."""
        if url:
            self.setURL(url)

        if self.url:
            #fh=self.url.getReader()
            fh = vfs.open(self.url)
            if fh:
                self.read(fh)
                fh.close()

    def read(self, fh):
        while True:
            try:
                hdu = FITSHDU(fh)
            except IOError:
                break
            print("Found HDU %s" % hdu)
            self.hdus.append(hdu)
    
    def save(self,filename=None):
        if filename:
            fh = vfs.open(filename, vfs.WRITE)
            if fh:
                self.parser.write(fh)
                fh.close()
                self.setURL(filename)
            else:
                eprint("Couldn't save %s\n" % filename)

    def setCubeAttributes(self, cube, hdu):
        cube.samples = hdu.image_axes[0]
        cube.lines = hdu.image_axes[1]
        if len(hdu.image_axes) > 2:
            cube.bands = hdu.image_axes[2]
        else:
            cube.bands = 1
        cube.data_type = hdu.getNumPyDataType()
        cube.data_offset = hdu.image_offset
        cube.byte_order = HSI.BigEndian

    def getCubeAttributes(self,cube):
        # transfer attributes from cube to self
        pass
    
    def getCube(self, filename=None, index=0):
        if filename is None:
            filename = self.url
        hdu = None
        i = 0
        for h in self.hdus:
            if h.image_size > 0:
                if index == i:
                    hdu = h
                    break
                i += 1
        if not hdu:
            raise IndexError("HDU index out of range")
        cube = HSI.newCube(hdu.getInterleave())
        self.setCubeAttributes(cube, hdu)
        cube.verifyAttributes()
        if filename:
            try:
                cube.open(filename)
            except:
                dprint("Failed opening cube %s" % cube)
                raise
        return cube

    def write(self,fh):
        pass


HSI.HyperspectralFileFormat.addDefaultHandler(FITSDataset)


if __name__ == "__main__":
    from optparse import OptionParser
    usage="usage: %prog [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option('-v', action='store_true', dest='verbose', help='display lots of debugging information')
    (options, args) = parser.parse_args()
    if options.verbose:
        FITSHDU.debuglevel = 1

    if args:
        for filename in args:
            h=HSI.HyperspectralFileFormat.load(filename)
            print h
            cube=h.getCube()
            print cube
            r=cube.getBand(0)
            print r
    else:
        print parser.usage
