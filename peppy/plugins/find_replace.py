# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob
import compiler

import wx

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.actions import *
from peppy.actions.base import *
from peppy.debug import *

class FindBar(wx.Panel):
    """Find panel customized from PyPE's findbar.py
    
    """
    forward = "Find"
    backward = "Find Backward"
    
    def __init__(self, parent, frame, stc, initial='', direction=1):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.frame = frame
        self.stc = stc
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, -1, _(self.forward) + u":")
        sizer.Add(self.label, 0, wx.CENTER)
        self.text = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.match_case = False
        
        # PyPE compat
        self.incr = 1
        self.setDirection(direction)

        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.text.Bind(wx.EVT_TEXT, self.OnChar)

        if initial:
            self.text.ChangeValue(initial)
    
    def setDirection(self, dir=1):
        if dir > 0:
            self._lastcall = self.OnFindN
            text = self.forward
        else:
            self._lastcall = self.OnFindP
            text = self.backward
        self.label.SetLabel(_(text) + u":")
        self.Layout()

    def OnChar(self, evt):
        #handle updating the background color
        self.resetColor()

        #search in whatever direction we were before
        self._lastcall(evt, 1)
        
        evt.Skip()

    def OnEnter(self, evt):
        return self.OnFindN(evt)
    
    def OnNotFound(self):
        self.text.SetBackgroundColour(wx.RED)
        self.frame.SetStatusText("Search string was not found.")
        self.Refresh()

    def getSearchString(self):
        findTxt = self.text.GetValue()
        if not findTxt:
            return ""
        
        #python strings in find
        if findTxt and findTxt[0] in ['"', "'"]:
            try:
                findTxt = [i for i in compiler.parse(str(findTxt)).getChildren()[:1] if isinstance(i, basestring)][0]
            except Exception, e:
                pass
        
        return findTxt

    def resetColor(self):
        if self.text.GetBackgroundColour() != wx.WHITE:
            self.text.SetBackgroundColour(wx.WHITE)
            self.frame.SetStatusText('')
            self.Refresh()

    def sel(self, posns, posne, msg):
        self.resetColor()
        self.frame.SetStatusText(msg)
        line = self.stc.LineFromPosition(posns)
        self.stc.GotoLine(line)
        posns, posne = self.getRange(posns, posne-posns)
        self.stc.SetSelection(posns, posne)
        self.stc.EnsureVisible(line)
        self.stc.EnsureCaretVisible()
    
    def cancel(self):
        self.resetColor()
        pos = self.stc.GetSelectionStart()
        self.stc.GotoPos(pos)
        self.stc.EnsureCaretVisible()
    
    def getRange(self, start, chars, dire=1):
        end = start
        if dire==1:
            fcn = self.stc.PositionAfter
        else:
            fcn = self.stc.PositionBefore
        for i in xrange(chars):
            z = fcn(end)
            y = self.stc.GetCharAt(end)
            x = abs(z-end)==2 and (((dire==1) and (y == 13)) or ((dire==0) and (y == 10)))
            ## print y, z-end
            end = z - x
        return start, end
    
    def OnFindN(self, evt, incr=0):
        self._lastcall = self.OnFindN
        self.incr = incr
        findTxt = self.getSearchString()
        if not findTxt:
            return self.cancel()
        flags = wx.FR_DOWN
        if self.match_case:
            flags |= wx.STC_FIND_MATCHCASE
        
        #handle finding next item, handling wrap-arounds as necessary
        gs = self.stc.GetSelection()
        gs = min(gs), max(gs)
        st = gs[1-incr]
        posn = self.stc.FindText(st, self.stc.GetTextLength(), findTxt, flags)
        if posn != -1:
            self.sel(posn, posn+len(findTxt), '')
            self.loop = 0
            return
        
        if st != 0:
            posn = self.stc.FindText(0, self.stc.GetTextLength(), findTxt, flags)
        self.loop = 1
        
        if posn != -1:
            self.sel(posn, posn+len(findTxt), "Reached end of document, continued from start.")
            return
        
        self.OnNotFound()
    
    def OnFindP(self, evt, incr=0):
        self._lastcall = self.OnFindP
        self.incr = 0
        findTxt = self.getSearchString()
        if not findTxt:
            return self.cancel()
        flags = 0
        if self.match_case:
            flags |= wx.STC_FIND_MATCHCASE
        
        #handle finding previous item, handling wrap-arounds as necessary
        st = min(self.getRange(min(self.stc.GetSelection()), len(findTxt), 0))
        #print self.stc.GetSelection(), st, 
        posn = self.stc.FindText(st, 0, findTxt, flags)
        if posn != -1:
            self.sel(posn, posn+len(findTxt), '')
            self.loop = 0
            return
        
        if st != self.stc.GetTextLength():
            posn = self.stc.FindText(self.stc.GetTextLength(), 0, findTxt, flags)
        self.loop = 1
        
        if posn != -1:
            self.sel(posn, posn+len(findTxt), "Reached start of document, continued from end.")
            return
        
        self.OnNotFound()




class FindMinibuffer(Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    def createWindow(self):
        # Create the find bar widget.
        if self.action.__class__ == FindPrevText:
            dir = -1
        else:
            dir = 1
        self.win = FindBar(self.mode.wrapper, self.mode.frame, self.mode, direction=dir)
    
    def repeat(self, action):
        self.win.SetFocus()
        dprint(action)
        if action.__class__ == FindPrevText:
            self.win.setDirection(-1)
            self.win.OnFindP(None)
        else:
            self.win.setDirection(1)
            self.win.OnFindN(None)

    def focus(self):
        # When the focus is asked for by the minibuffer driver, set it
        # to the text ctrl or combo box of the pype findbar.
        self.win.text.SetFocus()


class FindText(MinibufferRepeatAction):
    name = "Find..."
    tooltip = "Search for a string in the text."
    default_menu = ("Edit", -400)
    icon = "icons/find.png"
    key_bindings = {'default': "C-F", 'emacs': 'C-S', }
    minibuffer = FindMinibuffer

class FindPrevText(MinibufferRepeatAction):
    name = "Find Previous..."
    tooltip = "Search backwards for a string in the text."
    default_menu = ("Edit", 401)
    key_bindings = {'default': "C-S-F", 'emacs': 'C-R', }
    minibuffer = FindMinibuffer


class FindReplacePlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getActions(self):
        return [FindText, FindPrevText,
                ]


if __name__ == "__main__":
    import sys
    import __builtin__
    __builtin__._ = str
    
    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

            sizer = wx.BoxSizer(wx.VERTICAL)
            self.stc = wx.stc.StyledTextCtrl(self, -1)
            sizer.Add(self.stc, 1, wx.EXPAND)
            
            self.search = FindBar(self, self, self.stc)
            sizer.Add(self.search, 0, wx.EXPAND)
            
            self.SetSizer(sizer)

            self.CreateStatusBar()
            menubar = wx.MenuBar()
            self.SetMenuBar(menubar)  # Adding the MenuBar to the Frame content.
            menu = wx.Menu()
            menubar.Append(menu, "File")
            self.menuAdd(menu, "Quit", "Exit the pragram", self.OnQuit)
            menu = wx.Menu()
            menubar.Append(menu, "Edit")
            self.menuAdd(menu, "Find Next", "Remove spelling correction indicators", self.OnFind)

        def loadSample(self, paragraphs=2):
            lorem_ipsum = u"""\
Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Vivamus mattis
commodo sem.  Phasellus scelerisque tellus id lorem.  Nulla facilisi.
Suspendisse potenti.  Fusce velit odio, scelerisque vel, consequat nec,
dapibus sit amet, tortor.  Vivamus eu turpis.  Nam eget dolor.  Integer
at elit.  Praesent mauris.  Nullam non nulla at nulla tincidunt malesuada.
Phasellus id ante.  Sed mauris.  Integer volutpat nisi non diam.  Etiam
elementum.  Pellentesque interdum justo eu risus.  Cum sociis natoque
penatibus et magnis dis parturient montes, nascetur ridiculus mus.  Nunc
semper.  In semper enim ut odio.  Nulla varius leo commodo elit.  Quisque
condimentum, nisl eget elementum laoreet, mauris turpis elementum felis, ut
accumsan nisl velit et mi.

And some Russian: \u041f\u0438\u0442\u043e\u043d - \u043b\u0443\u0447\u0448\u0438\u0439 \u044f\u0437\u044b\u043a \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f!

"""
            self.stc.ClearAll()
            for i in range(paragraphs):
                self.stc.AppendText(lorem_ipsum)

        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, name, desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)
            menu.SetHelpString(id, desc)
        
        def OnQuit(self, evt):
            self.Close(True)
        
        def OnFind(self, evt):
            pass
        
    app = wx.App(False)
    frame = Frame(None)
    frame.loadSample()
    frame.Show()
    app.MainLoop()
