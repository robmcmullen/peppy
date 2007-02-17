# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re

import wx
import wx.stc as stc

from cStringIO import StringIO

from debug import *



#### STC Interface

class STCInterface(object):
    """
    Methods that a data source object must implement in order to be
    compatible with the real STC used as the data source for
    text-based files.

    See U{the Yellowbrain guide to the
    STC<http://www.yellowbrain.com/stc/index.html>} for more info on
    the rest of the STC methods.
    """
    def CanEdit(self):
        """PyPE compat to show read-only status"""
        return True
    
    def Clear(self):
        pass

    def CanCopy(self):
        return False

    def Copy(self):
        pass

    def CanCut(self):
        return False

    def Cut(self):
        pass

    def CanPaste(self):
        return False

    def Paste(self):
        pass

    def EmptyUndoBuffer(self):
        pass

    def CanUndo(self):
        return False

    def Undo(self):
        pass

    def CanRedo(self):
        return False

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

    def GetBinaryData(self,start,end):
        return []

    def GuessBinary(self,amount,percentage):
        return False


class NullSTC(STCInterface):
    """
    Bare-bones STC implementation (without any user interface)
    interface for testing purposes.  A few methods are implemented to
    support testing of the STC without using wx
    """
    def __init__(self):
        self.styledtext=""
        
    def Bind(self,evt,obj):
        pass

    def ClearAll(self):
        self.styledtext=""

    def SetText(self,text):
        self.styledtext='\0'.join(text)+'\0'

    def GetText(self):
        return self.styledtext[::2]

    def GetTextLength(self):
        return len(self.styledtext)/2

    def SetStyledText(self,text):
        self.styledtext=text

    def AddStyledText(self,text):
        self.styledtext+=text

    def GetStyledText(self,start=0,length=0):
        return self.styledtext[start*2:start*2+length*2]
    

class MySTC(stc.StyledTextCtrl,debugmixin):
    """
    Base version of the STC that most major modes will use as the STC
    implementation.
    """
    debuglevel=0
    
    def __init__(self, parent, ID=-1, refstc=None):
        stc.StyledTextCtrl.__init__(self, parent, ID)

        self.Bind(stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(stc.EVT_STC_DRAG_OVER, self.OnDragOver)
        self.Bind(stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(stc.EVT_STC_MODIFIED, self.OnModified)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.debug_dnd=False

        if refstc is not None:
            self.refstc=refstc
            self.docptr=self.refstc.docptr
            self.AddRefDocument(self.docptr)
            self.SetDocPointer(self.docptr)
            self.refstc.addSubordinate(self)
            self.dprint("referencing document %s" % self.docptr)
        else:
            self.refstc=None
            self.docptr=self.CreateDocument()
            self.SetDocPointer(self.docptr)
            self.dprint("creating new document %s" % self.docptr)
            self.subordinates=[]

        ## PyPE compat

        # assume unix line endings for now; will be changed after file
        # is loaded
        self.format='\n'

    def addSubordinate(self,otherstc):
        self.subordinates.append(otherstc)

    def removeSubordinate(self,otherstc):
        self.subordinates.remove(otherstc)

    def sendEvents(self,evt):
        """
        Send an event to all subordinate STCs
        """
        for otherstc in self.subordinates:
            self.dprint("sending event %s to %s" % (evt,otherstc))
            wx.PostEvent(otherstc,evt())

    def addUpdateUIEvent(self, callback):
        """Add the equivalent to STC_UPDATEUI event for UI changes.

        The STC supplies the EVT_STC_UPDATEUI event that fires for
        every change that could be used to update the user interface:
        a text change, a style change, or a selection change.  If the
        editing (viewing) window does not use the STC to display
        information, you should supply the equivalent event for the
        edit window.
        
        @param callback: event handler to execute on event
        """
        self.Bind(stc.EVT_STC_UPDATEUI, callback)
        
    def openPostHook(self,filter):
        """
        Hook here for subclasses of STC to do whatever they need with
        the FilterWrapper object used to load the file.  In some cases it
        might be useful to keep a reference to the filter.
        @param filter: filter used to load the file
        @type filter: iofilter.FilterWrapper
        """
        pass

    def CanEdit(self):
        """PyPE compat"""
        return True

    ## STCInterface additions
    def CanCopy(self):
        return True

    def CanCut(self):
        return True

    def GetBinaryData(self,start,end):
        """
        Convenience function to get binary data out of the STC.  The
        only way to get binary data out of the STC is to use the
        GetStyledText method and chop out every other byte.  Using the
        regular GetText method will stop at the first nul character.

        @param start: first text position
        @param end: last text position
        
        @returns: binary data between start and end-1, inclusive (just
        like standard python array slicing)
        """
        return self.GetStyledText(start,end)[::2]

    def GuessBinary(self,amount,percentage):
        """
        Guess if the text in this file is binary or text by scanning
        through the first C{amount} characters in the file and
        checking if some C{percentage} is out of the printable ascii
        range.

        Obviously this is a poor check for unicode files, so this is
        just a bit of a hack.

        @param amount: number of characters to check at the beginning
        of the file

        @type amount: int
        
        @param percentage: percentage of characters that must be in
        the printable ASCII range

        @type percentage: number

        @rtype: boolean
        """
        endpos=self.GetLength()
        if endpos>amount: endpos=amount
        bin=self.GetBinaryData(0,endpos)
        data = [ord(i) for i in bin]
        binary=0
        for ch in data:
            if (ch<8) or (ch>13 and ch<32) or (ch>126):
                binary+=1
        if binary>(endpos/percentage):
            return True
        return False
        
        
        
    def OnDestroy(self, evt):
        """
        Event handler for EVT_WINDOW_DESTROY. Preserve the clipboard
        contents can be preserved after the window is destroyed so
        that other apps can still grab it.

        @param evt: event
        """
        wx.TheClipboard.Flush()
        evt.Skip()


    def OnStartDrag(self, evt):
        self.dprint("OnStartDrag: %d, %s\n"
                       % (evt.GetDragAllowMove(), evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragAllowMove(False)     # you can prevent moving of text (only copy)
            evt.SetDragText("DRAGGED TEXT") # you can change what is dragged
            #evt.SetDragText("")             # or prevent the drag with empty text


    def OnDragOver(self, evt):
        self.dprint(
            "OnDragOver: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
            % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult())
            )

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragResult(wx.DragNone)   # prevent dropping at the beginning of the buffer


    def OnDoDrop(self, evt):
        self.dprint("OnDoDrop: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
                       "\ttext: %s\n"
                       % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult(),
                          evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 500:
            evt.SetDragText("DROPPED TEXT")  # Can change text if needed
            #evt.SetDragResult(wx.DragNone)  # Can also change the drag operation, but it
                                             # is probably better to do it in OnDragOver so
                                             # there is visual feedback

            #evt.SetPosition(25)             # Can also change position, but I'm not sure why
                                             # you would want to...




    def OnModified(self, evt):
##        self.dprint("""OnModified
##        Mod type:     %s
##        At position:  %d
##        Lines added:  %d
##        Text Length:  %d
##        Text:         %s\n""" % ( self.transModType(evt.GetModificationType()),
##                                  evt.GetPosition(),
##                                  evt.GetLinesAdded(),
##                                  evt.GetLength(),
##                                  repr(evt.GetText()) ))
        self.dprint("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))
        evt.Skip()

    def OnUpdateUI(self, evt):
        dprint("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))
        evt.Skip()


    def transModType(self, modType):
        st = ""
        table = [(stc.STC_MOD_INSERTTEXT, "InsertText"),
                 (stc.STC_MOD_DELETETEXT, "DeleteText"),
                 (stc.STC_MOD_CHANGESTYLE, "ChangeStyle"),
                 (stc.STC_MOD_CHANGEFOLD, "ChangeFold"),
                 (stc.STC_PERFORMED_USER, "UserFlag"),
                 (stc.STC_PERFORMED_UNDO, "Undo"),
                 (stc.STC_PERFORMED_REDO, "Redo"),
                 (stc.STC_LASTSTEPINUNDOREDO, "Last-Undo/Redo"),
                 (stc.STC_MOD_CHANGEMARKER, "ChangeMarker"),
                 (stc.STC_MOD_BEFOREINSERT, "B4-Insert"),
                 (stc.STC_MOD_BEFOREDELETE, "B4-Delete")
                 ]

        for flag,text in table:
            if flag & modType:
                st = st + text + " "

        if not st:
            st = 'UNKNOWN'

        return st

