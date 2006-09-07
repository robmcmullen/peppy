import os

import wx
import wx.stc as stc

from menudev import *
from buffers import *

class OpenFundamental(Command):
    name = "&Open File..."
    tooltip = "Open a File"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.open(self.frame,"demo.txt")


menu_plugins=[
    ['main',[('&File',0.0)],OpenFundamental,0.2],
]

toolbar_plugins=[
    # toolbar plugins here...
    ['main',OpenFundamental,0.05],
    ]



class MySTC(stc.StyledTextCtrl):
    def __init__(self, parent, ID, log=sys.stdout):
        stc.StyledTextCtrl.__init__(self, parent, ID)
        self.log = log

        self.Bind(stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(stc.EVT_STC_DRAG_OVER, self.OnDragOver)
        self.Bind(stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(stc.EVT_STC_MODIFIED, self.OnModified)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, evt):
        # This is how the clipboard contents can be preserved after
        # the app has exited.
        wx.TheClipboard.Flush()
        evt.Skip()


    def OnStartDrag(self, evt):
        self.log.write("OnStartDrag: %d, %s\n"
                       % (evt.GetDragAllowMove(), evt.GetDragText()))

        if debug and evt.GetPosition() < 250:
            evt.SetDragAllowMove(False)     # you can prevent moving of text (only copy)
            evt.SetDragText("DRAGGED TEXT") # you can change what is dragged
            #evt.SetDragText("")             # or prevent the drag with empty text


    def OnDragOver(self, evt):
        self.log.write(
            "OnDragOver: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
            % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult())
            )

        if debug and evt.GetPosition() < 250:
            evt.SetDragResult(wx.DragNone)   # prevent dropping at the beginning of the buffer


    def OnDoDrop(self, evt):
        self.log.write("OnDoDrop: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
                       "\ttext: %s\n"
                       % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult(),
                          evt.GetDragText()))

        if debug and evt.GetPosition() < 500:
            evt.SetDragText("DROPPED TEXT")  # Can change text if needed
            #evt.SetDragResult(wx.DragNone)  # Can also change the drag operation, but it
                                             # is probably better to do it in OnDragOver so
                                             # there is visual feedback

            #evt.SetPosition(25)             # Can also change position, but I'm not sure why
                                             # you would want to...




    def OnModified(self, evt):
        self.log.write("""OnModified
        Mod type:     %s
        At position:  %d
        Lines added:  %d
        Text Length:  %d
        Text:         %s\n""" % ( self.transModType(evt.GetModificationType()),
                                  evt.GetPosition(),
                                  evt.GetLinesAdded(),
                                  evt.GetLength(),
                                  repr(evt.GetText()) ))


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





class FundamentalView(View):
    pluginkey = 'fundamental'
    keyword='Fundamental'
    regex=".*"

    documents={}

    def createWindow(self,parent):
        print "creating new Fundamental window"
        clone=False
        if self.win:
            print "Fundamental: clone=True"
            clone=True

        self.createSTC(parent,style=True)
        self.win=self.stc

        if clone:
            self.open()

    def createSTC(self,parent,style=False):
        self.stc=MySTC(parent, -1)
        if style:
            self.styleSTC()

    def styleSTC(self):
        face1 = 'Arial'
        face2 = 'Times New Roman'
        face3 = 'Courier New'
        pb = 10

        # make some styles
        self.stc.StyleSetSpec(stc.STC_STYLE_DEFAULT, "size:%d,face:%s" % (pb, face3))
        self.stc.StyleClearAll()

        # line numbers in the margin
        self.stc.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.stc.SetMarginWidth(0, 22)
        self.stc.StyleSetSpec(stc.STC_STYLE_LINENUMBER, "size:%d,face:%s" % (pb, face1))
        

    def open(self):
        filename=self.buffer.getFilename()

        # save the reference count for the old document
        olddoc=self.stc.GetDocPointer()
        self.stc.AddRefDocument(olddoc)
        print "Fundamental: olddoc=%s" % olddoc
        
        if filename in self.documents:
            docptr=self.documents[filename]
            self.stc.SetDocPointer(docptr)
            print "  found existing document %s" % docptr
            self.setupExistingBuffer()
        else:
            newdoc=self.stc.CreateDocument()
            self.stc.SetDocPointer(newdoc)
            print "  creating new document %s" % newdoc
            fh=self.buffer.getFileObject()
            self.readFromBuffer(fh)
            self.documents[filename]=newdoc

    def readFromBuffer(self,fh):
        txt=fh.read()
        print "Fundamental readFromBuffer: reading %d bytes" % len(txt)
        self.stc.SetText(txt)
        self.txt=txt
       
    def setupExistingBuffer(self):
        pass



viewers=[
    FundamentalView,
    ]


if __name__ == "__main__":
    app=testapp(0)
    frame=RootFrame(app.main)
    frame.Show(True)
    app.MainLoop()

