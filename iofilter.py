import os

from cStringIO import StringIO

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

class Protocol(debugmixin):
    debuglevel=0
    identifier=None
    
    def __init__(self,filename):
        self.filename=self.splitFilename(filename)

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
    identifier='file'
    
    def getReader(self):
        self.dprint("getReader: trying to open %s" % self.filename)
        fh=open(self.filename,"rb")
        return fh

    def getWriter(self):
        self.dprint("getWriter: trying to open %s" % self.filename)
        fh=open(filename,"wb")
        return fh

class AboutProtocol(Protocol):
    identifier='about'
    
    def getReader(self):
        if self.filename in aboutfiles:
            fh=StringIO()
            fh.write(aboutfiles[self.filename])
            fh.seek(0)
            return fh
        raise IOError

    def getWriter(self):
        raise NotImplementedError

class HTTPProtocol(Protocol):
    identifier='http'
    
    def getReader(self):
        raise NotImplementedError
        
    def getWriter(self):
        raise NotImplementedError

protocols=[AboutProtocol,HTTPProtocol,FileProtocol]

def GetProtocolHandler(filename):
    for protocol in protocols:
        if protocol.isFilename(filename):
            return protocol(filename)
    return FileProtocol(filename)




class IOFilter(debugmixin):
    debuglevel=0
    
    def __init__(self,stc,protocol):
        self.stc=stc
        self.protocol=protocol

    def read(self):
        raise NotImplementedError

    def write(self):
        raise NotImplementedError

class TextFilter(IOFilter):
    def read(self):
        fh=self.protocol.getReader()
        txt=fh.read()
        self.dprint("TextFilter: reading %d bytes" % len(txt))
        self.stc.SetText(txt)

    def write(self):
        fh=self.protocol.getWriter()
        txt=self.stc.GetText()
        self.dprint("TextFilter: writing %d bytes" % len(txt))
        try:
            fh.write(txt)
        except:
            print "TextFilter: something went wrong writing to %s" % self.protocol.filename
            raise

class BinaryFilter(IOFilter):
    def read(self):
        fh=self.protocol.getReader()
        txt=fh.read()
        self.dprint("BinaryFilter: reading %d bytes" % len(txt))

        # Now, need to convert it to two bytes per character
        styledtxt='\0'.join(txt)+'\0'
        self.dprint("styledtxt: length=%d" % len(styledtxt))

        self.stc.ClearAll()
        self.stc.AddStyledText(styledtxt)

        length=self.stc.GetTextLength()
        #wx.StaticText(self.win, -1, str(length), (0, 25))

        newtxt=self.stc.GetStyledText(0,length)
        out=" ".join(["%02x" % ord(i) for i in txt])
        self.dprint(out)
        #wx.StaticText(self.win, -1, out, (20, 45))

        errors=0
        for i in range(len(txt)):
            if newtxt[i*2]!=txt[i]:
                self.dprint("error at: %d (%02x != %02x)" % (i,ord(newtxt[i*2]),ord(txt[i])))
                errors+=1
            if errors>50: break
        self.dprint("errors=%d" % errors)
    
    def write(self):
        fh=self.protocol.getWriter()
        numchars=self.stc.GetTextLength()
        # Have to use GetStyledText because GetText will truncate the
        # string at the first zero character.
        txt=self.stc.GetStyledText(0,numchars)[0:numchars*2:2]
        self.dprint("BinaryFilter: writing %d bytes" % len(txt))
        self.dprint(repr(txt))
        try:
            fh.write(txt)
        except:
            print "BinaryFilter: something went wrong writing to %s" % self.protocol.filename
            raise




def GetIOFilter(stc,filename):
    protocol=GetProtocolHandler(filename)
    filter=BinaryFilter(stc,protocol)
    return filter


if __name__ == "__main__":
    pass

