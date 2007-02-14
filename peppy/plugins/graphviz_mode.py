# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Python major mode.
"""

import os,struct
import keyword

import wx
import wx.stc as stc

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

from peppy.plugins.about import SetAbout

SetAbout('sample.dot','digraph G {Hello->World}')


class SampleDot(SelectAction):
    name = "&Open Sample Graphviz dot file"
    tooltip = "Open a sample Graphviz file"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:sample.dot")

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
              'size2': 8,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 10,
              'size2': 8,
             }



class GraphvizMode(FundamentalMode):
    keyword='Graphviz'
    icon='icons/graphviz.ico'
    regex="\.dot$"
    lexer=stc.STC_LEX_CPP

    def getKeyWords(self):
        return [(0,"strict graph digraph")]
    
    def styleSTC(self):
        self.format=os.linesep
        
        s=self.stc

        face1 = 'Arial'
        face2 = 'Times New Roman'
        face3 = 'Courier New'
        pb = 10

        # Show mixed tabs/spaces
        s.SetProperty("tab.timmy.whinge.level", "1")
        
        # Global default styles for all languages
        s.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        s.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        s.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        s.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(mono)s,size:%(size2)d" % faces)
        s.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        s.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#0000FF,bold")
        s.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FF0000,bold")

        # Python styles
        # Default 
        s.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comments
        s.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(mono)s,size:%(size)d" % faces)
        # Number
        s.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        s.StyleSetSpec(stc.STC_P_STRING, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Single quoted string
        s.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Keyword
        s.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        s.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        s.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        s.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
        s.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        s.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
        s.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comment-blocks
        s.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F,face:%(mono)s,size:%(size)d" % faces)
        # End of line where string is not closed
        s.StyleSetSpec(stc.STC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)



class GraphvizViewCtrl(wx.Panel):
    """Viewer that calls graphviz to generate an image.

    Call graphviz to generate an image and display it.
    """

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, mgr=None):
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.dotprogs = ['neato', 'dot', 'twopi', 'circo', 'fdp']
        self.prog = wx.Choice(self, -1, (100, 50), choices = self.dotprogs)
        buttons.Add(self.prog, 1, wx.EXPAND)
        
        regen = wx.Button(self, -1, "Regenerate")
        buttons.Add(regen, 1, wx.EXPAND)

        regen.Bind(wx.EVT_BUTTON, self.OnRegenerate)

        self.sizer.Add(buttons)

        self.drawing = wx.Window(self, -1)
        self.sizer.Add(self.drawing, 1, wx.EXPAND)

        self.Layout()

        self.drawing.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnRegenerate(self, event):
        dprint("using %s to run graphviz" % self.prog.GetStringSelection())

    def OnPaint(self, event):
        dc = wx.PaintDC(self.drawing)
        
        size = self.drawing.GetClientSize()
        s = ("Size: %d x %d")%(size.x, size.y)

        dc.SetFont(wx.NORMAL_FONT)
        w, height = dc.GetTextExtent(s)
        height = height + 3
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)
        dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2))

    def OnSize(self, event):
        self.Refresh()
        event.Skip()
        

class GraphvizViewMinorMode(MinorMode):
    keyword="GraphvizView"

    def createWindows(self, parent):
        self.sizerep=GraphvizViewCtrl(parent)
        paneinfo=self.getDefaultPaneInfo("Graphviz View")
        paneinfo.Right()
        self.major.addPane(self.sizerep,paneinfo)
        


class GraphvizPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)
    implements(IMinorModeProvider)
    implements(IMenuItemProvider)

    def scanEmacs(self,emacsmode,vars):
        if emacsmode in ['graphviz',GraphvizMode.keyword]:
            return MajorModeMatch(GraphvizMode,exact=True)
        return None

    def scanShell(self,bangpath):
        if bangpath.find('dot')>-1:
            return MajorModeMatch(GraphvizMode,exact=True)
        return None

    def scanFilename(self,filename):
        if filename.endswith('.dot'):
            return MajorModeMatch(GraphvizMode,exact=True)
        return None

    def getMinorModes(self):
        yield GraphvizViewMinorMode    
    
    default_menu=((None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(SampleDot)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

