import os

import wx
import wx.stc as stc

from menudev import *
from buffers import *
from views import *

from debug import *


class OpenFundamental(FrameAction):
    name = "&Open Sample Text"
    tooltip = "Open some sample text"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("demo.txt")

class WordWrap(FrameToggle):
    name = "&Word Wrap"
    tooltip = "Toggle word wrap in this view"
    icon = wx.ART_TOOLBAR

    def isEnabled(self, state=None):
        return True
    
    def isChecked(self, index):
        viewer=self.frame.getCurrentViewer()
        if viewer:
            return viewer.settings.wordwrap
        return False
    
    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s" % (id(self),self.name))
        viewer=self.frame.getCurrentViewer()
        if viewer:
            viewer.setWordWrap(not viewer.settings.wordwrap)
    
class LineNumbers(FrameToggle):
    name = "&Line Numbers"
    tooltip = "Toggle line numbers in this view"
    icon = wx.ART_TOOLBAR

    def isEnabled(self, state=None):
        return True
    
    def isChecked(self, index):
        viewer=self.frame.getCurrentViewer()
        if viewer:
            return viewer.settings.linenumbers
        return False
    
    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s" % (id(self),self.name))
        viewer=self.frame.getCurrentViewer()
        if viewer:
            viewer.setWordWrap(not viewer.settings.linenumbers)
    
class BeginningOfLine(FrameAction):
    name = "Cursor to Start of Line"
    tooltip = "Move the cursor to the start of the current line."
    keyboard = 'C-A'

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer:
            s=viewer.stc
            pos = s.GetCurrentPos()
            col = s.GetColumn(pos)
            s.GotoPos(pos-col)
        

class EndOfLine(FrameAction):
    name = "Cursor to End of Line"
    tooltip = "Move the cursor to the end of the current line."
    keyboard = 'C-E'

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer:
            s=viewer.stc
            line = s.GetCurrentLine()
            s.GotoPos(s.GetLineEndPosition(line))

menu_plugins=[
    ['main',[('&File',0.0)],OpenFundamental,0.2],
]



class MySTC(stc.StyledTextCtrl,debugmixin):
    def __init__(self, parent, frame, ID=-1):
        stc.StyledTextCtrl.__init__(self, parent, ID)
        self.tabs=parent # this is the tabbed frame
        self.frame=frame # this is the BufferFrame

        self.Bind(stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(stc.EVT_STC_DRAG_OVER, self.OnDragOver)
        self.Bind(stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(stc.EVT_STC_MODIFIED, self.OnModified)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.debug_dnd=False

    def OnDestroy(self, evt):
        # This is how the clipboard contents can be preserved after
        # the app has exited.
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
        self.dprint("""OnModified
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

    defaultsettings={
        'menu_actions':[
            ['main',[('&Edit',0.1)],WordWrap,0.1],
            LineNumbers,
            ],
        'keyboard_actions':[
            ['main',BeginningOfLine],
            EndOfLine,
            ]
        }


    documents={}

    def __init__(self,buffer,frame):
        View.__init__(self,buffer,frame)

    def createWindow(self,parent):
        self.dprint("creating new Fundamental window")

        self.createSTC(parent,style=True)
        self.win=self.stc
        self.win.Bind(wx.EVT_KEY_DOWN, self.frame.KeyPressed)

    def createSTC(self,parent,style=False):
        self.stc=MySTC(parent, self.frame)
        self.applyDefaultStyle()
        if style:
            self.styleSTC()

    def applyDefaultStyle(self):
        face1 = 'Arial'
        face2 = 'Times New Roman'
        face3 = 'Courier New'
        pb = 10

        # make some styles
        self.stc.StyleSetSpec(stc.STC_STYLE_DEFAULT, "size:%d,face:%s" % (pb, face3))
        self.stc.StyleClearAll()

        # line numbers in the margin
        self.stc.StyleSetSpec(stc.STC_STYLE_LINENUMBER, "size:%d,face:%s" % (pb, face1))
        if self.settings.linenumbers:
            self.stc.SetMarginType(0, stc.STC_MARGIN_NUMBER)
            self.stc.SetMarginWidth(0, 22)
        else:
            self.stc.SetMarginWidth(0,0)
            
        # turn off symbol margin
        if self.settings.symbols:
            self.stc.SetMarginWidth(1, 0)
        else:
            self.stc.SetMarginWidth(1, 16)

        # turn off folding margin
        if self.settings.folding:
            self.stc.SetMarginWidth(2, 16)
        else:
            self.stc.SetMarginWidth(2, 0)

        self.setWordWrap()

    def setWordWrap(self,enable=None):
        if enable is not None:
            self.settings.wordwrap=enable
        if self.settings.wordwrap:
            self.stc.SetWrapMode(stc.STC_WRAP_CHAR)
            self.stc.SetWrapVisualFlags(stc.STC_WRAPVISUALFLAG_END)
        else:
            self.stc.SetWrapMode(stc.STC_WRAP_NONE)

    def setLineNumbers(self,enable=None):
        if enable is not None:
            self.settings.linenumbers=enable
        if self.settings.linenumbers:
            self.stc.SetMarginType(0, stc.STC_MARGIN_NUMBER)
            self.stc.SetMarginWidth(0, 22)
        else:
            self.stc.SetMarginWidth(0,0)

    def styleSTC(self):
        pass

    def openPostHook(self):
        # SetIndent must be called whenever a new document is loaded
        # into the STC
        self.stc.SetIndent(4)
        #self.dprint("indention=%d" % self.stc.GetIndent())

        self.stc.SetIndentationGuides(1)




viewers=[
    FundamentalView,
    ]


if __name__ == "__main__":
    app=testapp(0)
    frame=RootFrame(app.main)
    frame.Show(True)
    app.MainLoop()

