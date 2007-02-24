# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re,urlparse

from cStringIO import StringIO

from trac.core import *
from debug import *
from stcinterface import *

__all__ = [ 'GetIOFilter', 'ProtocolPlugin', 'ProtocolPluginBase', 'URLStats' ]

class URLInfo(object):
    def __init__(self, url, default="file", usewin=False):
        self.url = url
        (self.protocol, self.netloc, self.path, self.parameters,
         self.query_string, self.fragment) = urlparse.urlparse(self.url, default)

        # special handling for windows filenames with drive letters
        if os.name in ['nt', 'ce', 'os2'] or usewin:
            # dprint(self)
            if len(self.protocol)==1:
                self.path = "%s:%s" % (self.protocol, self.path)
                self.protocol = "file"

    def __str__(self):
        return "%s %s" % (self.url, (self.protocol,
                                                        self.netloc,
                                                        self.path,
                                                        self.parameters,
                                                        self.query_string,
                                                        self.fragment))
            

#### ProtocolPlugins that define loaders for reading files and
#### populating the STC interface

class UnknownProtocolError(ValueError):
    pass

class URLStats(object):
    def __init__(self):
        self.size = -1
        self.readonly = False
        self.owner = None
        self.group = None
        self.permissions = None
        
class ProtocolPlugin(Interface):
    """Interface for IO plugins.  A plugin that implements this
    interface takes a URL in the form of protocol://path/to/some/file
    and implements two methods that return a file-like object that can
    be used to either read from or write to the datastore that is
    pointed to by the URL.  Some protocols, like http, will typically
    be read-only, which means the getWriter method may be omitted from
    the plugin."""

    def supportedProtocols():
        """Return a list of protocols that this interface supports,
        i.e. a http protocol class would return ['http'] or
        potentially ['http','https'] if it also http over SSL."""

    def getNormalizedName(urlinfo):
        """Return the normalized URL.

        Return a string representing the normalized URL.
        """

    def getStats(urlinfo):
        """Return statistics on the URLInfo object.

        Return a URLStats instance containing information about the
        data pointed to by the specified url.
        """
        
    def getReader(urlinfo):
        """Returns a file-like object that can be used to read the
        data using the given protocol.
        """

    def getWriter(urlinfo):
        """Returns a file-like object that can be used to write the
        data using the given protocol."""

    def getSTC(parent):
        """
        Get an STC instance that supports this protocol.
        """

class ProtocolPluginBase(Component):
    def supportedProtocols(self):
        return NotImplementedError

    def getNormalizedName(self):
        return NotImplementedError

    def getStats(self, urlinfo):
        return URLStats()
    
    def getReader(self, urlinfo):
        return NotImplementedError
    
    def getWriter(self, urlinfo):
        return NotImplementedError
    
    def getSTC(self, parent):
        return MySTC(parent)


## Default protocols

class FileProtocol(ProtocolPluginBase, debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['file']

    def getNormalizedName(self, urlinfo):
        return "file:" + os.path.abspath(self.getFilename(urlinfo))

    def getFilename(self, urlinfo):
        # urlparse makes a distinction between file://name and
        # file:///name:
        # >>> urlparse("file://LICENSE")
        # ('file', 'LICENSE', '', '', '', '')
        # >>> urlparse("file:///LICENSE")
        # ('file', '', '/LICENSE', '', '', '')
        
        # but, I don't need that distinction, so just cat them.
        return urlinfo.netloc + urlinfo.path
    
    def getStats(self, urlinfo):
        filename = self.getFilename(urlinfo)
        stats = URLStats()
        stats.readonly = not os.access(filename, os.W_OK)
        return stats

    def getReader(self, urlinfo):
        filename = self.getFilename(urlinfo)
        self.dprint("getReader: trying to open %s" % filename)
        fh = open(filename, "rb")
        return fh

    def getWriter(self, urlinfo):
        filename = self.getFilename(urlinfo)
        self.dprint("getWriter: trying to open %s" % filename)
        fh = open(filename, "wb")
        return fh

class HTTPProtocol(ProtocolPluginBase, debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['http', 'https']

    def getNormalizedName(self, urlinfo):
        return urlinfo.url
    
    def getStats(self, urlinfo):
        stats = ProtocolStatistics()
        stats.readonly = True
        return stats

    def getReader(self, urlinfo):
        import urllib2

        fh = urllib2.urlopen(urlinfo.url)
        fh.readonly = True
        return fh


class ProtocolHandler(Component):
    handlers = ExtensionPoint(ProtocolPlugin)

    def find(self, protoidentifier):
        for handler in self.handlers:
            if protoidentifier in handler.supportedProtocols():
                return handler
        raise UnknownProtocolError("no handler for %s protocol" % protoidentifier)




class IOFilter(debugmixin):
    debuglevel = 0
    
    def read(self, fh, stc):
        raise NotImplementedError

    def write(self, fh, stc):
        raise NotImplementedError

class TextFilter(IOFilter):
    def read(self, fh, stc, size=None):
        if size is not None:
            txt = fh.read(size)
        else:
            txt = fh.read()
        self.dprint("TextFilter: reading %d bytes from %s" % (len(txt), fh))
        stc.AddText(txt)
        return fh, txt

    def write(self, fh, stc):
        txt = stc.GetText()
        self.dprint("TextFilter: writing %d bytes to %s" % (len(txt), fh))
        try:
            fh.write(txt)
        except:
            print "TextFilter: something went wrong writing to %s" % fh
            raise

class BinaryFilter(IOFilter):
    debuglevel = 0
    
    def read(self, fh, stc, size=None):
        if size is not None:
            txt = fh.read(size)
        else:
            txt = fh.read()
        self.dprint("BinaryFilter: reading %d bytes from %s" % (len(txt), fh))

        # Now, need to convert it to two bytes per character
        styledtxt = '\0'.join(txt)+'\0'
        self.dprint("styledtxt: length=%d" % len(styledtxt))

        stc.AddStyledText(styledtxt)

        # Debugging stuff to check to see if the text conversion went
        # correctly.
        
##        length = stc.GetTextLength()

##        newtxt = stc.GetStyledText(0, length)
##        out = " ".join(["%02x" % ord(i) for i in txt])
##        self.dprint(out)

##        errors = 0
##        for i in range(len(txt)):
##            if newtxt[i*2]!=txt[i]:
##                self.dprint("error at: %d (%02x != %02x)" % (i, ord(newtxt[i*2]), ord(txt[i])))
##                errors+=1
##            if errors>50: break
##        self.dprint("errors=%d" % errors)
        return txt
    
    def write(self, fh, stc):
        numchars = stc.GetTextLength()
        # Have to use GetStyledText because GetText will truncate the
        # string at the first zero character.
        txt = stc.GetStyledText(0, numchars)[0:numchars*2:2]
        self.dprint("BinaryFilter: writing %d bytes to %s" % (len(txt), fh))
        self.dprint(repr(txt))
        try:
            fh.write(txt)
        except:
            print "BinaryFilter: something went wrong writing to %s" % fh
            raise


#### Filter wrappers that combine Protocols and Filters

class FilterWrapper(debugmixin):
    def __init__(self, protocol, filter, info):
        self.protocol = protocol
        self.filter = filter
        self.urlinfo = info
        self.fh = None
        self.stats = protocol.getStats(info)
        self.url = protocol.getNormalizedName(self.urlinfo)

    def read(self, stc, size=None):
        if self.fh is None:
            self.fh = self.protocol.getReader(self.urlinfo)
        raw = self.filter.read(self.fh, stc, size)
        
        from pype.parsers import detectLineEndings
        stc.format = detectLineEndings(raw)

    def write(self, stc):
        self.fh = self.protocol.getWriter(self.urlinfo)
        self.filter.write(self.fh, stc)

    def close(self):
        if self.fh is not None:
            self.fh.close()
        self.fh = None

    def getSTC(self, parent):
        return self.protocol.getSTC(parent)


def GetIOFilter(path, default="file", usewin=False):
    comp_mgr = ComponentManager()
    handler = ProtocolHandler(comp_mgr)
    info = URLInfo(path, default, usewin)
    if info.protocol is None:
        info.protocol = default
    protocol = handler.find(info.protocol)
    filter = BinaryFilter()
    return FilterWrapper(protocol, filter, info)


if __name__ == "__main__":
    pass

