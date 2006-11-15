import os,re

import wx
import wx.stc as stc

from cStringIO import StringIO

from debug import *



#### STC Interface

class STCInterface(object):
    def CanPaste(self):
        return 0

    def Clear(self):
        pass

    def Copy(self):
        pass

    def Cut(self):
        pass

    def Paste(self):
        pass

    def EmptyUndoBuffer(self):
        pass

    def CanUndo(self):
        return 0

    def Undo(self):
        pass

    def CanRedo(self):
        return 0

    def Redo(self):
        pass

    def GetModify(self):
        return False

    def CreateDocument(self):
        return "notarealdoc"

    def SetDocPointer(self,ptr):
        pass

    def ReleaseDocument(self,ptr):
        pass

    def AddRefDocument(self,ptr):
        pass

# Global default STC interface for user interface purposes
class NullSTC(STCInterface):
    def Bind(self,evt,obj):
        pass
    
BlankSTC=NullSTC()



#### Loaders for reading files and populating the STC interface

class Filter(debugmixin):
    def __init__(self):
        pass

    def read(self,buffer):
        pass

    def write(self,buffer):
        return False

class TextFilter(Filter):
    def read(self,buffer):
        fh=buffer.getReadFileObject()
        txt=fh.read()
        self.dprint("TextFilter: reading %d bytes" % len(txt))
        buffer.stc.SetText(txt)

    def write(self,buffer,filename):
        fh=buffer.getWriteFileObject(filename)
        txt=buffer.stc.GetText()
        self.dprint("TextFilter: writing %d bytes" % len(txt))
        try:
            fh.write(txt)
        except:
            print "TextFilter: something went wrong writing to %s" % filename
            raise

class BinaryFilter(Filter):
    def read(self,buffer):
        fh=buffer.getReadFileObject()
        txt=fh.read()
        self.dprint("BinaryFilter: reading %d bytes" % len(txt))

        # Now, need to convert it to two bytes per character
        styledtxt='\0'.join(txt)+'\0'
        self.dprint("styledtxt: length=%d" % len(styledtxt))

        buffer.stc.ClearAll()
        buffer.stc.AddStyledText(styledtxt)

        length=buffer.stc.GetTextLength()
        #wx.StaticText(self.win, -1, str(length), (0, 25))

        newtxt=buffer.stc.GetStyledText(0,length)
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
    
    def write(self,buffer,filename):
        fh=buffer.getWriteFileObject(filename)
        numchars=buffer.stc.GetTextLength()
        # Have to use GetStyledText because GetText will truncate the
        # string at the first zero character.
        txt=buffer.stc.GetStyledText(0,numchars)[0:numchars*2:2]
        self.dprint("BinaryFilter: writing %d bytes" % len(txt))
        self.dprint(repr(txt))
        try:
            fh.write(txt)
        except:
            print "BinaryFilter: something went wrong writing to %s" % filename
            raise




if __name__ == "__main__":
    pass

