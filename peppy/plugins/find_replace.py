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
    
    def __init__(self, parent, frame, stc, storage=None, direction=1):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.frame = frame
        self.stc = stc
        if isinstance(storage, dict):
            self.storage = storage
        else:
            self.storage = {}
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, -1, _(self.forward) + u":")
        sizer.Add(self.label, 0, wx.CENTER)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.find, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.match_case = False
        
        # PyPE compat
        self.incr = 1
        self.setDirection(direction)

        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.find.Bind(wx.EVT_TEXT, self.OnChar)
    
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
        self.find.SetBackgroundColour(wx.RED)
        self.frame.SetStatusText("Search string was not found.")
        self.Refresh()

    def expandText(self, findTxt):
        #python strings in find
        if findTxt[0] in ['"', "'"]:
            try:
                findTxt = [i for i in compiler.parse(str(findTxt)).getChildren()[:1] if isinstance(i, basestring)][0]
            except Exception, e:
                pass
            matchcase = True
        else:
            if findTxt != findTxt.lower():
                matchcase = True
            else:
                matchcase = self.match_case
        return findTxt, matchcase

    def getSearchString(self):
        txt = self.find.GetValue()
        if not txt:
            return "", self.match_case
        return self.expandText(txt)

    def resetColor(self):
        if self.find.GetBackgroundColour() != wx.WHITE:
            self.find.SetBackgroundColour(wx.WHITE)
            self.Refresh()

    def sel(self, posns, posne, msg, interactive=True):
        if interactive:
            self.resetColor()
            self.frame.SetStatusText(msg)
            line = self.stc.LineFromPosition(posns)
            self.stc.GotoLine(line)
        posns, posne = self.getRange(posns, posne-posns)
        self.stc.SetSelection(posns, posne)
        if interactive:
            self.stc.EnsureVisible(line)
            self.stc.EnsureCaretVisible()
    
    def cancel(self, pos_at_end=False):
        self.resetColor()
        self.frame.SetStatusText('')
        if pos_at_end:
            pos = self.stc.GetSelectionEnd()
        else:
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
    
    def OnFindN(self, evt, incr=0, allow_wrap=True, help='', interactive=True):
        self._lastcall = self.OnFindN
        self.incr = incr
        findTxt, matchcase = self.getSearchString()
        if not findTxt:
            return self.cancel()
        flags = wx.FR_DOWN
        if matchcase:
            flags |= wx.stc.STC_FIND_MATCHCASE
        
        #handle finding next item, handling wrap-arounds as necessary
        gs = self.stc.GetSelection()
        gs = min(gs), max(gs)
        st = gs[1-incr]
        posn = self.stc.FindText(st, self.stc.GetTextLength(), findTxt, flags)
        if posn != -1:
            self.sel(posn, posn+len(findTxt), help, interactive)
            self.loop = 0
            return
        
        if allow_wrap and st != 0:
            posn = self.stc.FindText(0, self.stc.GetTextLength(), findTxt, flags)
        self.loop = 1
        
        if posn != -1:
            self.sel(posn, posn+len(findTxt), "Reached end of document, continued from start.")
            return
        
        self.OnNotFound()
    
    def OnFindP(self, evt, incr=0, allow_wrap=True, help=''):
        self._lastcall = self.OnFindP
        self.incr = 0
        findTxt, matchcase = self.getSearchString()
        if not findTxt:
            return self.cancel()
        flags = 0
        if matchcase:
            flags |= wx.STC_FIND_MATCHCASE
        
        #handle finding previous item, handling wrap-arounds as necessary
        st = min(self.getRange(min(self.stc.GetSelection()), len(findTxt), 0))
        #print self.stc.GetSelection(), st, 
        posn = self.stc.FindText(st, 0, findTxt, flags)
        if posn != -1:
            self.sel(posn, posn+len(findTxt), help)
            self.loop = 0
            return
        
        if allow_wrap and st != self.stc.GetTextLength():
            posn = self.stc.FindText(self.stc.GetTextLength(), 0, findTxt, flags)
        self.loop = 1
        
        if posn != -1:
            self.sel(posn, posn+len(findTxt), "Reached start of document, continued from end.")
            return
        
        self.OnNotFound()

    def repeat(self, direction):
        last, matchcase = self.getSearchString()
        if not last:
            if 'last_search' in self.storage:
                self.find.ChangeValue(self.storage['last_search'])
                self.find.SetInsertionPointEnd()
                return
            
        if direction < 0:
            self.setDirection(-1)
            self.OnFindP(None)
        else:
            self.setDirection(1)
            self.OnFindN(None)
    
    def saveState(self):
        last, matchcase = self.getSearchString()
        if last:
            self.storage['last_search'] = last


class FindMinibuffer(Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    search_storage = {}
    
    def createWindow(self):
        # Create the find bar widget.
        if self.action.__class__ == FindPrevText:
            dir = -1
        else:
            dir = 1
        self.win = FindBar(self.mode.wrapper, self.mode.frame, self.mode, self.search_storage, direction=dir)
    
    def repeat(self, action):
        self.win.SetFocus()
        if action.__class__ == FindPrevText:
            self.win.repeat(-1)
        else:
            self.win.repeat(1)

    def focus(self):
        # When the focus is asked for by the minibuffer driver, set it
        # to the text ctrl or combo box of the pype findbar.
        self.win.find.SetFocus()
    
    def closePreHook(self):
        self.win.saveState()
        self.dprint(self.search_storage)


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





class ReplaceBar(FindBar):
    """Replace panel in the style of the Emacs replace function
    
    """
    replace = "Replace"
    replace_regex = "Regex Replace"
    help_status = "y: replace, n: skip, q: exit, !:replace all"
    
    def __init__(self, parent, frame, stc, storage=None, direction=1, on_exit=None):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.frame = frame
        self.stc = stc
        if isinstance(storage, dict):
            self.storage = storage
        else:
            self.storage = {}
        
        if on_exit:
            self.on_exit = on_exit
        else:
            self.on_exit = None
        
        self.text = self.replace
        grid = wx.GridBagSizer(0, 0)
        self.label = wx.StaticText(self, -1, _(self.replace) + u":")
        grid.Add(self.label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.find, (0, 1), flag=wx.EXPAND)
        label = wx.StaticText(self, -1, _("with") + u":")
        grid.Add(label, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.replace = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.replace, (1, 1), flag=wx.EXPAND)
        self.command = wx.Button(self, -1, "Replace")
        grid.Add(self.command, (1, 2), flag=wx.EXPAND)
        grid.AddGrowableCol(1)
        self.SetSizer(grid)
        
        self.match_case = False
        self.smart_case = True
        
        # Count of number of replacements
        self.count = 0
        
        # Last cursor position, tracked during replace all
        self.last_cursor = 0
        
        # PyPE compat
        self.incr = 1
        self.setDirection(direction)

        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnTabToReplace)
        self.replace.Bind(wx.EVT_TEXT_ENTER, self.OnTabToPanel)
        self.command.Bind(wx.EVT_BUTTON, self.OnReplace)
        self.command.Bind(wx.EVT_KEY_DOWN, self.OnCommandKeyDown)
        self.command.Bind(wx.EVT_CHAR, self.OnCommandChar)
        self.command.Bind(wx.EVT_SET_FOCUS, self.OnSearchStart)
        self.command.Bind(wx.EVT_KILL_FOCUS, self.OnSearchStop)
    
    def setDirection(self, dir=1):
        self.label.SetLabel(_(self.text) + u":")
        self.Layout()

    def OnTabToReplace(self, evt):
        self.replace.SetFocus()
        self.text = "Regex Replace"
        self.setDirection()
    
    def OnTabToPanel(self, evt):
        self.command.SetFocus()
        self.text = "Replace"
        self.setDirection()
    
    def OnSearchStart(self, evt):
        self.OnFindN(evt, help=self.help_status)
    
    def OnSearchStop(self, evt):
        self.cancel()
        
    def getReplaceString(self, replacing):
        txt = self.replace.GetValue()
        if not txt:
            return ""
        
        replaceTxt, ignore = self.expandText(txt)
        
        if self.smart_case:
            if replacing.upper() == replacing:
                ## print "all upper", replacing
                replaceTxt = replaceTxt.upper()
            elif replacing.lower() == replacing:
                ## print "all lower", replacing
                replaceTxt = replaceTxt.lower()
            elif len(replacing) == len(replaceTxt):
                ## print "smartcasing", replacing
                r = []
                for i,j in zip(replacing, replaceTxt):
                    if i.isupper():
                        r.append(j.upper())
                    elif i.islower():
                        r.append(j.lower())
                    else:
                        r.append(j)
                replaceTxt = ''.join(r)
            elif replacing and replaceTxt and replacing[:1].upper() == replacing[:1]:
                ## print "first upper", replacing
                replaceTxt = replaceTxt[:1].upper() + replaceTxt[1:]
            elif replacing and replaceTxt and replacing[:1].lower() == replacing[:1]:
                ## print "first lower", replacing
                replaceTxt = replaceTxt[:1].lower() + replaceTxt[1:]
        
        return replaceTxt

    def OnReplace(self, evt, find_next=True, interactive=True):
        """Replace the selection
        
        The bulk of this algorithm is from PyPE.
        """
        allow_wrap = not interactive
        findTxt, matchcase = self.getSearchString()
        sel = self.stc.GetSelection()
        if sel[0] == sel[1]:
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            return (-1, -1), 0
        else:
            replacing = self.stc.GetTextRange(sel[0], sel[1])
            if (matchcase and replacing != findTxt) or \
               (not matchcase and replacing.lower() != findTxt.lower()):
                if find_next:
                    self.OnFindN(evt, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
                return (-1, -1), 0
        
        replaceTxt = self.getReplaceString(replacing)
        
        sel = self.stc.GetSelection()
        if not self.stc.GetReadOnly():
            self.stc.ReplaceSelection(replaceTxt)
            #fix for unicode...
            self.stc.SetSelection(min(sel), min(sel)+len(replaceTxt))
            self.last_cursor = self.stc.GetSelectionEnd()
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            self.count += 1
            
            return sel, len(replacing)-len(replaceTxt)
        else:
            return (max(sel), max(sel)), 0
    
    def OnReplaceAll(self, evt):
        self.count = 0
        self.loop = 0
        self.last_cursor = 0
        
        # FIXME: this takes more time than it should, probably because there's
        # a lot of redundant stuff going on in OnReplace.  This should be
        # rewritten for speed at some point.
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(True)
            wx.Yield()
        self.stc.BeginUndoAction()
        try:
            while self.loop == 0:
                self.OnReplace(None, interactive=False)
            self.stc.GotoPos(self.last_cursor)
        finally:
            self.stc.EndUndoAction()
        
        if self.count == 1:
            occurrences = _("Replaced %d occurrence")
        else:
            occurrences = _("Replaced %d occurrences")
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(False)
        self.OnExit(msg=_(occurrences) % self.count)
    
    def OnCommandKeyDown(self, evt):
        key = evt.GetKeyCode()
        mods = evt.GetModifiers()
        if key == wx.WXK_TAB and not mods & (wx.MOD_CMD|wx.MOD_SHIFT|wx.MOD_ALT):
            self.find.SetFocus()
        elif key == wx.WXK_RETURN:
            self.OnExit()
        elif key == wx.WXK_DELETE:
            self.OnFindN(None, help=self.help_status)
        else:
            evt.Skip()
    
    def OnCommandChar(self, evt):
        uchar = unichr(evt.GetKeyCode())
        if uchar in u'n':
            self.OnFindN(None, help=self.help_status)
        elif uchar in u'y ':
            self.OnReplace(None)
        elif uchar in u'p^':
            self.OnFindP(None, help=self.help_status)
        elif uchar in u'q':
            self.OnExit()
        elif uchar in u'.':
            self.OnReplace(None, find_next=False)
            self.OnExit()
        elif uchar in u'!':
            self.OnReplaceAll(None)
        else:
            evt.Skip()
    
    def OnExit(self, msg=''):
        self.cancel(pos_at_end=True)
        if msg:
            self.frame.SetStatusText(msg)
        if self.on_exit:
            self.on_exit()


class ReplaceMinibuffer(Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    search_storage = {}
    
    def createWindow(self):
        self.win = ReplaceBar(self.mode.wrapper, self.mode.frame, self.mode,
                              self.search_storage, on_exit=self.removeFromParent)
    
    def repeat(self, action):
        self.win.SetFocus()
        self.win.repeat(1)

    def focus(self):
        # When the focus is asked for by the minibuffer driver, set it
        # to the text ctrl or combo box of the pype findbar.
        self.win.find.SetFocus()
    
    def closePreHook(self):
        self.win.saveState()
        self.dprint(self.search_storage)




class Replace(MinibufferRepeatAction):
    name = "Replace..."
    tooltip = "Search backwards for a string in the text."
    default_menu = ("Edit", 402)
    key_bindings = {'emacs': 'F6', }
    minibuffer = ReplaceMinibuffer


class FindReplacePlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getActions(self):
        return [FindText, FindPrevText,
                Replace
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
            
            self.replace = ReplaceBar(self, self, self.stc)
            sizer.Add(self.replace, 0, wx.EXPAND)
            
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
self
Self
SELF
SeLF
seLF
SeLf

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
