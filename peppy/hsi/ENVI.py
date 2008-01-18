# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Read, parse, and write ENVI headers.

Support for reading and writing ENVI headers.  This interfaces with
the HSI module to set up the correct parameters for reading the raw
data contained in the corresponding data file.
"""

import os,os.path,sys,re,csv,textwrap

import peppy.vfs as vfs

import numpy

from common import *

from cStringIO import StringIO

# From the ENVI help: data type - parameter identifying the type of
# data representation, where 1=8 bit byte 2=16-bit signed integer
# 3=32-bit signed long integer 4=32-bit floating point 5=64-bit double
# precision floating point 6=2x32-bit complex, real-imaginary pair of
# double precision 9=2x64-bit double precision complex, real-imaginary
# pair of double precision 12=16-bit unsigned integer 13=32-bit
# unsigned long integer 14=64-bit signed long integer and 15=64-bit
# unsigned long integer.
enviDataType=[None,numpy.uint8,numpy.int16,numpy.int32,numpy.float32,numpy.float64,numpy.complex64,None,None,numpy.complex128,None,None,numpy.uint16,numpy.uint32,numpy.int64,numpy.uint64]

# byte order: 0=little endian, 1=big endian


_header_extensions = ['.hdr','.HDR','hdr','HDR']
def isHeader(filename):
    for ext in _header_extensions:
        if filename.endswith(ext):
            return len(ext)
    return 0

def verifyHeader(filename):
    hasext=False
    for ext in _header_extensions:
        if filename.endswith(ext):
            hasext=True
            break

    if not hasext:
        for ext in _header_extensions:
            if vfs.exists(filename+ext):
                filename+=ext
                hasext=True
                break

    if not hasext:
        name,ext=os.path.splitext(filename)
        for ext in _header_extensions:
            if vfs.exists(name+ext):
                filename=name+ext
                break

    return filename

def findHeaders(url):
    urls = []
    for ext in _header_extensions:
        header = vfs.normalize(str(url)+ext)
        if vfs.exists(header):
            urls.append(header)

    name,ext = os.path.splitext(str(url))
    for ext in _header_extensions:
        header = vfs.normalize(name+ext)
        if vfs.exists(header):
            urls.append(header)

    return urls


class Header(dict,MetadataMixin):
    """
    Class representing the text fields of an ENVI format header, with
    the ability to populate an L{Cube} with the parsed values from
    this text.

    When initially loading this class, all that is done is to parse the text into name/value pairs.  Conversion from text to something more interesting, like the actual values or lists of values is not done until you call L{getCube}, which then creates an L{Cube} instance and populates its fields with the values parsed from the ENVI header text.
    """

    format_id="ENVI"
    format_name="ENVI Datacube"
    extensions=['.bil','.bip','.bsq','.sli']

    def __init__(self,filename=None,debug=False):
        self.debug = debug
        
        self['samples']="98"
        self['lines']="98"
        self['bands']="98"
        self['interleave']="bil"

        self.strings=['description']
        self.lists=['wavelength','fwhm','sigma','band names','default bands','bbl']
        self.outputorder=['description','samples','lines','bands','byte order','interleave']

        # To convert from python dict to object attributes, here's a
        # list of conversion functions that relate to a list of items
        # in the header file.
        self.convert=(
            (int , ['samples','lines','bands','byte order','bbl','x start','header offset']),
            (float , ['wavelength','fwhm','sigma','reflectance scale factor']),
            (lambda s:s.lower() , ['interleave','sensor type']),
            (normalizeUnits, ['wavelength units']),
            (lambda s:enviDataType[int(s)], ['data type']),
            (lambda s:s, ['description','band names','default bands']),
            )

        # convert from the object attributes to the ENVI text format
        self.unconvert=(
            (lambda s:enviDataType.index(s), ['data type']),
            )

        # if attributes are specified here, it will convert the ENVI
        # header key to the attribute name used in the Cube attribute
        # list.  Other ENVI keys will be converted to lower case and
        # have spaces replaced by underscores.
        self.attributeConvert={
            'reflectance scale factor':'scale_factor',
            'wavelength':'wavelengths'
            }

        if filename:
            if isinstance(filename, Cube):
                self.getCubeAttributes(filename)
            else:
                filename = vfs.normalize(filename)
                self.headerurl, self.cubeurl = self.getFilePair(filename)
                self.open(self.headerurl)
        else:
            self.headerurl = None
            self.cubeurl = None

    @classmethod
    def getFilePair(cls, url):
        fh = vfs.open(url)
        line=fh.read(4)
        if line=='ENVI':
            # need to open the cube, not the header
            return (url, None)
        fh.close()
        headers = findHeaders(url)
        for header in headers:
            fh = vfs.open(header)
            line=fh.read(4)
            if line=='ENVI':
                return (header, url)
            fh.close()
        return None

    @classmethod
    def identify(cls, urlinfo):
        try:
            pair = cls.getFilePair(urlinfo)
            if pair is not None and pair[1] is not None:
                return True
        except:
            pass
        return False
        
    def open(self,filename=None):
        """Open the header file, and if successful parse it."""
        if self.headerurl:
            fh = vfs.open(self.headerurl)
            if fh:
                self.read(fh)
                fh.close()
            else:
                eprint("Couldn't open %s for reading.\n" % self.headerurl)

    def save(self,filename=None):
        if filename:
            url = vfs.normalize(filename)
            if vfs.is_file(url):
                fh = vfs.open(url, vfs.WRITE)
            else:
                fh = vfs.make_file(url)
            if fh:
                fh.write(str(self))
                fh.close()
            else:
                eprint("Couldn't open %s for writing.\n" % filename)

    def read(self,fh):
        """parse the header file for the ENVI key/value pairs."""
        key=''
        val=''

        # Simple finite state machine, where the states are 'nothing'
        # and 'bracket'.  'bracket' indicates that we have encountered
        # a open bracket and reading in a list.  This state continues
        # until we encounter a close bracket.  FIXME: should handle
        # the case where a close bracket appears inside quotes
        state='nothing'
        for txt in fh:
            if state == 'bracket':
                txt=txt.rstrip()
                if re.search('[}]',txt):
                    txt=re.sub('[}]*$','',txt)
                    val+=txt
                    # remove trailing whitespace
                    self[key]=val.rstrip()
                    if self.debug: dprint("mutiline: '%s':%s'%s'" % (key,os.linesep,self[key]))
                    state='nothing'
                else:
                    val+=txt+os.linesep
            else:
                if re.search('=',txt):
                    if self.debug: dprint("txt=%s" % txt)
                    key,val = [s.strip() for s in re.split('=\s*',txt,1)]
                    key=key.lower()
                    if self.debug: dprint("matching: '%s'='%s'" % (key,val))
                    if val == "{":
                        state='bracket'
                        val=''
                    else:
                        if val[0]=='{' and val[-1]=='}':
                            # single line string: remove braces and spaces
                            val=val[1:-1].strip()
                        else:
                            # remove garbage characters
                            val=re.sub('\{\}[ \r\n\t]*','',val)
                        self[key]=val
                        if self.debug: dprint("stored: '%s'='%s'" % (key,self[key]))
        self.fixup()

    def fixup(self):
        """convert any nonstandard keys here..."""
        if 'sigma' in self:
            self['fwhm']=self['sigma']
            del self['sigma']


    def convertList(self,orig,txt,converter=lambda s:s):
        """Use csv to parse the text into a list of values, and
        additionally convert those values according to the specified
        function (default: no conversion).  Use the original value to
        determine if the final result should be reduced to a value
        instead of a one-element list."""
        file=StringIO(txt)
        if self.debug: dprint("getList: parsing %s" % txt)
        reader=csv.reader(file)
        count=0
        save=[]
        for row in reader:
            for col in row:
                if self.debug: dprint("  col=%s" % col)
                if len(col)==0 or re.match("[ \n\r\t]+$",col): continue
                save.append(converter(col))
        if self.debug: dprint("getList: %s" % save)
        if len(save)==1 and not isinstance(orig,list) :
            return save[0]
        else:
            return save

    def locateCube(self):
        if self.headerurl==None:
            return None
        
        filename=self.headerurl
        extlen=isHeader(filename)
        if extlen>0:
            filename=filename[:-extlen]
        if os.path.exists(filename):
            return filename
        il="."+self['interleave']
        exts=[".img",".IMG",il,il.lower(),il.upper(),il.title(),".dat",".DAT",".sli",".SLI",".bin",".BIN"]
        for ext in exts:
            check=filename+ext
            if self.debug: dprint("checking %s\n" % check)
            if os.path.exists(check):
                return check
        return None

    def getCube(self,filename=None,index=0):
        #dprint(self.cubeurl, self.headerurl)
        cube=newCube(self['interleave'],self.cubeurl)
        #dprint(cube)
        self.setCubeAttributes(cube)
        cube.open()
        cube.verifyAttributes()
        return cube

    def getCubeNames(self):
        desc = 'Cube #1: %s' % self['description'].strip()
        return [desc]

    def getAttributeId(self,txt):
        """Convert ENVI header text string into the corresponding
        attribute ID of the Cube object"""
        
        if txt in self.attributeConvert:
            item_id=self.attributeConvert[txt]
        else:
            # attributes use '_' in place of spaces
            item_id=re.sub(' ','_',txt).lower()
        return item_id

    def setCubeAttributes(self,cube):
        """Parse the text strings stored in the object (as a
        dictionary) into usable numbers, lists, and strings.  Store
        the resulting values in the Cube that is passed in as a
        parameter."""
        for converter,keys in self.convert:
            for item_txt in keys:
                item_id=self.getAttributeId(item_txt)
                orig=getattr(cube,item_id,None)
##                if orig != None:
##                    dprint(" before: self.%s = %s" % (item_id,str(orig)))

                # if the text exists in the object's dictionary,
                # convert it to its native form and store it as an
                # object attribute in cube
                if item_txt in self:
                    setattr(cube,item_id,self.convertList(orig,self[item_txt],converter))
##                    dprint(" after: cube.%s = %s" % (item_id,str(getattr(cube,item_id,None))))
##                else:
##                    dprint(" item %s not found in header." % item_txt)

    def getCubeAttributes(self,cube):
        """Create header strings from the attributes in the cube."""
        for converter,keys in self.convert:
            for item_txt in keys:
                item_id=self.getAttributeId(item_txt)
                orig=getattr(cube,item_id,None)
                if orig is not None:
                    if self.debug: dprint("converting key='%s' orig='%s'" % (item_txt,orig))
                    for unconverter,unconvertkeys in self.unconvert:
                        if item_txt in unconvertkeys:
                            if isinstance(orig,list):
                                orig=[unconverter(i) for i in orig]
                            else:
                                orig=unconverter(orig)
                            break
                    val=str(orig)
                    if isinstance(orig,list):
                        val=textwrap.fill(
                            val.lstrip('[').rstrip(']'),
                            initial_indent='  ',
                            subsequent_indent='  ')
                    self[item_txt]=val
        
        # FIXME: why was this needed?  Seems like it unnecessarily
        # adds redundant data to the file
##        if self['wavelength'] and not self['band names']:
##            self['band names'] = str(self['wavelength'])

    def str_string(self,key,val):
        return "%s = {%s%s}%s" % (key,os.linesep,val,os.linesep)


    def __str__(self):
        fs=StringIO()
        fs.write("ENVI"+os.linesep)
        order=self.keys()
        if self.debug: dprint("keys in object: %s" % order)
        for key in self.outputorder:
            try:
                i=order.index(key)
                if key in self.lists or key in self.strings: 
                    fs.write(self.str_string(key,self[key]))
                else:
                    fs.write("%s = %s%s" % (key,self[key],os.linesep))
                del order[i]
            except ValueError:
                pass
            
        order.sort()
        for key in order:
            val=self[key]
            if key in self.lists or key in self.strings:
                if val:
                    # only write the list if the list has something in
                    # it
                    fs.write(self.str_string(key,val))
            else:
                fs.write("%s = %s%s" % (key,val,os.linesep))
        return fs.getvalue()


class TextROI(ROIFile):
    """ENVI Text format ROI file support.

    This format supports loading and saving of ENVI text format ROIs.
    """

    format_id="ENVI"
    format_name="ENVI ROI"

    def __init__(self,filename=None,debug=False):
        ROIFile.__init__(self, filename)

    @classmethod
    def identify(cls, urlinfo):
        fh = vfs.open(urlinfo)
        line=fh.read(100)
        if line.startswith('; ENVI Output of ROIs'):
            return True
        return False

    @classmethod
    def load(cls, urlinfo):
        fh = vfs.open(urlinfo)
        group = ENVITextROI(urlinfo)
        current = None
        index = -1
        for line in fh:
            if line.startswith(';'):
                if line.startswith('; ROI '):
                    name, val = line[6:].split(':')
                    name = name.strip()
                    val = val.strip()
                    dprint("name=%s val=%s" % (name, val))
                    if name == 'name':
                        current = ROI(val)
                        group.addROI(current)
                    elif name == 'npts':
                        current.number = int(val)
                    elif name == 'rgb value':
                        current.setColor(val)
                    else:
                        dprint(current)
                        current = None
                elif line.startswith('; ID'):
                    index = 0
                    current = group.getROI(index)
            else:
                vals = line.split()
                if len(vals)>0:
                    # ENVI roi coordinates start from 1, not zero
                    dprint(vals)
                    current.addPoint(int(vals[0]), int(vals[1])-1, int(vals[2])-1)
                else:
                    index += 1
                    current = group.getROI(index)

        dprint(group)
        return group


HyperspectralFileFormat.addDefaultHandler(Header)

##    def supportedROIFormats(self):
##        return [TextROI]

if __name__ == "__main__":
    from optparse import OptionParser
    usage="usage: %prog [files...]"
    parser=OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    print options

    if args:
        for filename in args:
            h=Header(filename,debug=True)
            print h
    else:
        h=Header("t/sco2c.128.hdr")
        print h
