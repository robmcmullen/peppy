import os

from cStringIO import StringIO

from trac.core import *
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

def SetAbout(filename,text):
    aboutfiles[filename]=text

#### Loaders for reading files and populating the STC interface

class IProtocol(Interface):
    def getReader(filename):
        """Returns a file-like object that can be used to read the
        data using the given protocol."""

    def getWriter(filename):
        """Returns a file-like object that can be used to write the
        data using the given protocol."""

class Protocol(Component,debugmixin):
    debuglevel=0
    identifier=None
    
    @classmethod
    def isFilename(cls,filename):
        if filename.startswith(cls.identifier+':'):
            return True
        return False

    def splitFilename(self,filename):
        if self.isFilename(filename):
            return filename[len(self.identifier)+1:]
        return filename

class FileProtocol(Protocol):
    implements(IProtocol)
    identifier='file'
    
    def getReader(self,filename):
        self.dprint("getReader: trying to open %s" % filename)
        fh=open(filename,"rb")
        return fh

    def getWriter(self,filename):
        self.dprint("getWriter: trying to open %s" % filename)
        fh=open(filename,"wb")
        return fh

class AboutProtocol(Protocol):
    implements(IProtocol)
    identifier='about'
    
    def getReader(self,filename):
        if filename in aboutfiles:
            fh=StringIO()
            fh.write(aboutfiles[filename])
            fh.seek(0)
            return fh
        raise IOError

    def getWriter(self,filename):
        raise NotImplementedError

class HTTPProtocol(Protocol):
    implements(IProtocol)
    identifier='http'
    
    def getReader(self,filename):
        raise NotImplementedError
        
    def getWriter(self,filename):
        raise NotImplementedError


class ProtocolHandler(Component):
    protocols=ExtensionPoint(IProtocol)

    def find(self,filename):
        for protocol in self.protocols:
            if protocol.isFilename(filename):
                return protocol
        return FileProtocol(self.compmgr)




class IOFilter(debugmixin):
    debuglevel=0
    
    def read(self,protocol,filename):
        raise NotImplementedError

    def write(self,protocol,filename):
        raise NotImplementedError

class TextFilter(IOFilter):
    def read(self,protocol,filename,stc):
        fh=protocol.getReader(filename)
        txt=fh.read()
        self.dprint("TextFilter: reading %d bytes" % len(txt))
        stc.SetText(txt)

    def write(self,protocol,filename,stc):
        fh=protocol.getWriter(filename)
        txt=stc.GetText()
        self.dprint("TextFilter: writing %d bytes" % len(txt))
        try:
            fh.write(txt)
        except:
            print "TextFilter: something went wrong writing to %s" % filename
            raise

class BinaryFilter(IOFilter):
    def read(self,protocol,filename,stc):
        fh=protocol.getReader(filename)
        txt=fh.read()
        self.dprint("BinaryFilter: reading %d bytes" % len(txt))

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
    
    def write(self,protocol,filename,stc):
        fh=protocol.getWriter(filename)
        numchars=stc.GetTextLength()
        # Have to use GetStyledText because GetText will truncate the
        # string at the first zero character.
        txt=stc.GetStyledText(0,numchars)[0:numchars*2:2]
        self.dprint("BinaryFilter: writing %d bytes" % len(txt))
        self.dprint(repr(txt))
        try:
            fh.write(txt)
        except:
            print "BinaryFilter: something went wrong writing to %s" % filename
            raise



#### Filter wrappers that combine Protocols and Filters

class FilterWrapper(debugmixin):
    def __init__(self,protocol,filter,filename,stc):
        self.protocol=protocol
        self.filter=filter
        self.filename=protocol.splitFilename(filename)
        self.stc=stc

    def read(self):
        return self.filter.read(self.protocol,self.filename,self.stc)

    def write(self):
        return self.filter.write(self.protocol,self.filename,self.stc)


def GetIOFilter(stc,filename):
    comp_mgr=ComponentManager()
    handler=ProtocolHandler(comp_mgr)
    protocol=handler.find(filename)
    filter=BinaryFilter()
    return FilterWrapper(protocol,filter,filename,stc)


if __name__ == "__main__":
    pass

