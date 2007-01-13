import os,re,urlparse

from cStringIO import StringIO

from trac.core import *
from plugin import *
from debug import *

__all__ = [ 'GetIOFilter', 'SetAbout' ]

aboutfiles={}
aboutfiles['demo.txt'] = """\
This editor is provided by a class named wx.StyledTextCtrl.  As
the name suggests, you can define styles that can be applied to
sections of text.  This will typically be used for things like
syntax highlighting code editors, but I'm sure that there are other
applications as well.  A style is a combination of font, point size,
foreground and background colours.  The editor can handle
proportional fonts just as easily as monospaced fonts, and various
styles can use different sized fonts.

There are a few canned language lexers and colourizers included,
(see the next demo) or you can handle the colourization yourself.
If you do you can simply register an event handler and the editor
will let you know when the visible portion of the text needs
styling.

wx.StyledTextEditor also supports setting markers in the margin...




...and indicators within the text.  You can use these for whatever
you want in your application.  Cut, Copy, Paste, Drag and Drop of
text works, as well as virtually unlimited Undo and Redo
capabilities, (right click to try it out.)
"""

def SetAbout(path,text):
    aboutfiles[path]=text

class URLInfo(object):
    def __init__(self,url,default="file",usewin=False):
        self.url=url
        (self.protocol, self.netloc, self.path, self.parameters,
         self.query_string, self.fragment)=urlparse.urlparse(self.url,default)

        # special handling for windows filenames with drive letters
        if os.name in ['nt','ce','os2'] or usewin:
            print self
            if len(self.protocol)==1:
                self.path="%s:%s" % (self.protocol,self.path)
                self.protocol="file"

    def __str__(self):
        return "%s %s" % (self.url, (self.protocol,
                                                        self.netloc,
                                                        self.path,
                                                        self.parameters,
                                                        self.query_string,
                                                        self.fragment))
            

#### Loaders for reading files and populating the STC interface

class UnknownProtocolError(ValueError):
    pass

class FileProtocol(ProtocolPluginBase,debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['file']

    def getFilename(self,urlinfo):
        # urlparse makes a distinction between file://name and
        # file:///name:
        # >>> urlparse("file://LICENSE")
        # ('file', 'LICENSE', '', '', '', '')
        # >>> urlparse("file:///LICENSE")
        # ('file', '', '/LICENSE', '', '', '')
        
        # but, I don't need that distinction, so just cat them.
        return urlinfo.netloc+urlinfo.path
    
    def getReader(self,urlinfo):
        filename=self.getFilename(urlinfo)
        self.dprint("getReader: trying to open %s" % filename)
        fh=open(filename,"rb")
        return fh

    def getWriter(self,urlinfo):
        filename=self.getFilename(urlinfo)
        self.dprint("getWriter: trying to open %s" % filename)
        fh=open(filename,"wb")
        return fh

class AboutProtocol(ProtocolPluginBase,debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['about']
    
    def getReader(self,urlinfo):
        if urlinfo.path in aboutfiles:
            fh=StringIO()
            fh.write(aboutfiles[urlinfo.path])
            fh.seek(0)
            return fh
        raise IOError

class HTTPProtocol(ProtocolPluginBase,debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['http','https']
    
    def getReader(self,urlinfo):
        import urllib2

        fh=urllib2.urlopen(urlinfo.url)
        return fh


class ProtocolHandler(Component):
    handlers=ExtensionPoint(ProtocolPlugin)

    def find(self,protoidentifier):
        for handler in self.handlers:
            if protoidentifier in handler.supportedProtocols():
                return handler
        raise UnknownProtocolError("no handler for %s protocol" % protoidentifier)




class IOFilter(debugmixin):
    debuglevel=0
    
    def read(self,protocol,path):
        raise NotImplementedError

    def write(self,protocol,path):
        raise NotImplementedError

class TextFilter(IOFilter):
    def read(self,protocol,path,stc):
        fh=protocol.getReader(path)
        txt=fh.read()
        self.dprint("TextFilter: reading %d bytes from %s" % (len(txt),path))
        stc.SetText(txt)
        return fh,txt

    def write(self,protocol,path,stc):
        fh=protocol.getWriter(path)
        txt=stc.GetText()
        self.dprint("TextFilter: writing %d bytes to %s" % (len(txt),path))
        try:
            fh.write(txt)
        except:
            print "TextFilter: something went wrong writing to %s" % path
            raise
        return fh

class BinaryFilter(IOFilter):
    def read(self,protocol,urlinfo,stc):
        fh=protocol.getReader(urlinfo)
        txt=fh.read()
        self.dprint("BinaryFilter: reading %d bytes from %s" % (len(txt),urlinfo))

        # Now, need to convert it to two bytes per character
        styledtxt='\0'.join(txt)+'\0'
        self.dprint("styledtxt: length=%d" % len(styledtxt))

        stc.ClearAll()
        stc.AddStyledText(styledtxt)

        length=stc.GetTextLength()

        newtxt=stc.GetStyledText(0,length)
        out=" ".join(["%02x" % ord(i) for i in txt])
        self.dprint(out)

        errors=0
        for i in range(len(txt)):
            if newtxt[i*2]!=txt[i]:
                self.dprint("error at: %d (%02x != %02x)" % (i,ord(newtxt[i*2]),ord(txt[i])))
                errors+=1
            if errors>50: break
        self.dprint("errors=%d" % errors)
        return fh,txt
    
    def write(self,protocol,urlinfo,stc):
        fh=protocol.getWriter(urlinfo)
        numchars=stc.GetTextLength()
        # Have to use GetStyledText because GetText will truncate the
        # string at the first zero character.
        txt=stc.GetStyledText(0,numchars)[0:numchars*2:2]
        self.dprint("BinaryFilter: writing %d bytes to %s" % (len(txt),urlinfo))
        self.dprint(repr(txt))
        try:
            fh.write(txt)
        except:
            print "BinaryFilter: something went wrong writing to %s" % urlinfo
            raise
        return fh


#### Filter wrappers that combine Protocols and Filters

class FilterWrapper(debugmixin):
    def __init__(self,protocol,filter,info):
        self.protocol=protocol
        self.filter=filter
        self.urlinfo=info
        self.fh=None

    def read(self,stc):
        self.fh,raw=self.filter.read(self.protocol,self.urlinfo,stc)

        from pype.parsers import detectLineEndings
        stc.format=detectLineEndings(raw)

    def write(self,stc):
        self.fh=self.filter.write(self.protocol,self.urlinfo,stc)

    def getSTC(self,parent):
        return self.protocol.getSTC(parent)


def GetIOFilter(path,default="file",usewin=False):
    comp_mgr=ComponentManager()
    handler=ProtocolHandler(comp_mgr)
    info=URLInfo(path,default,usewin)
    if info.protocol is None:
        info.protocol=default
    protocol=handler.find(info.protocol)
    filter=BinaryFilter()
    return FilterWrapper(protocol,filter,info)


if __name__ == "__main__":
    pass

