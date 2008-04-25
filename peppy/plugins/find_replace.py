# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob
import compiler

import wx
import wx.lib.stattext

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.actions import *
from peppy.actions.base import *
from peppy.debug import *


class FindSettings(debugmixin):
    def __init__(self, match_case=False, smart_case=True):
        self.match_case = match_case
        self.smart_case = smart_case
        self.find = ''
        self.replace = ''
    
    def serialize(self, storage):
        if self.find:
            storage['last_search'] = self.find
        if self.replace:
            storage['last_replace'] = self.replace


class FindService(debugmixin):
    forward = "Find"
    backward = "Find Backward"
    replace = "Replace"
    
    def __init__(self, stc, settings=None):
        self.stc = stc
        if settings is None:
            self.settings = FindSettings()
        else:
            self.settings = settings
        
        self.flags = 0
    
    def allowBackward(self):
        return True
    
    def expandText(self, findTxt, set_flags=False):
        #python strings in find
        if not findTxt:
            findTxt = ""
        if len(findTxt) > 0 and findTxt[0] in ['"', "'"]:
            try:
                findTxt = [i for i in compiler.parse(str(findTxt)).getChildren()[:1] if isinstance(i, basestring)][0]
            except Exception, e:
                pass
            match_case = True
        else:
            if self.settings.find != self.settings.find.lower():
                match_case = True
            else:
                match_case = self.settings.match_case
        
        if set_flags and match_case:
            self.flags = wx.stc.STC_FIND_MATCHCASE
            
        return findTxt
    
    def setFindString(self, text):
        self.settings.find = self.expandText(text, set_flags=True)
    
    def setReplaceString(self, text):
        self.settings.replace = self.expandText(text)

    def getReplacement(self, replacing):
        """Return the string that will be substituted in the text
        
        @param replacing: the original string from the document
        @return: the string after the substitutions have been made
        """
        replaceTxt = self.settings.replace
        
        if self.settings.smart_case:
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
    
    def highlightSelection(self, pos):
        sel_start, sel_end = self.getRange(pos, len(self.settings.find))
        #dprint("selection = %d - %d" % (sel_start, sel_end))
        self.stc.SetSelection(sel_start, sel_end)
    
    def doFindNext(self, start=-1, incremental=False):
        """Find and highlight the next match in the document.
        
        @param start: starting position in text, or -1 to use current position
        
        @param incremental: True if an incremental search that will be added to
        the current search result
        
        @return: tuple containing the position of the match or -1 if no match
        is found, and the position of the original start of the search.  If
        the search string is invalid, a tuple of (None, None) is returned.
        """
        if not self.settings.find:
            return None, None
        flags = self.flags | wx.FR_DOWN
        
        #handle finding next item, handling wrap-arounds as necessary
        if start < 0:
            sel = self.stc.GetSelection()
            if incremental:
                start = min(sel)
            else:
                start = max(sel)
        pos = self.stc.FindText(start, self.stc.GetTextLength(), self.settings.find, flags)
        
        if pos >= 0:
            self.highlightSelection(pos)
        
        return pos, start

    def doFindPrev(self, start=-1, incremental=False):
        """Find and highlight the previous match in the document.
        
        @param start: starting position in text, or -1 to use current position
        
        @param incremental: True if an incremental search that will be added to
        the current search result
        
        @return: tuple containing the position of the match or -1 if no match
        is found, and the position of the original start of the search.  If
        the search string is invalid, a tuple of (None, None) is returned.
        """
        if not self.settings.find:
            return None, None
        flags = self.flags
        
        if start < 0:
            sel = self.stc.GetSelection()
            if incremental:
                start = min(sel) + len(self.settings.find)
                #dprint("sel=%s min=%d len=%s" % (str(sel), min(sel), len(self.settings.find)))
            else:
                start = min(sel)
        pos = self.stc.FindText(start, 0, self.settings.find, flags)
        
        if pos >= 0:
            self.highlightSelection(pos)
        
        return pos, start

    def doReplace(self):
        """Replace the selection
        
        Replace the current selection in the stc with the replacement text
        """
        if self.stc.GetReadOnly():
            return -1
        sel = self.stc.GetSelection()
        replacing = self.stc.GetTextRange(sel[0], sel[1])

        replaceTxt = self.getReplacement(replacing)
        
        self.stc.ReplaceSelection(replaceTxt)
        #fix for unicode...
        self.stc.SetSelection(min(sel), min(sel)+len(replaceTxt))
        return len(replaceTxt)


class FindBasicRegexService(FindService):
    forward = "Find Regex"
    replace = "Replace Regex"
    
    def __init__(self, stc, settings=None):
        FindService.__init__(self, stc, settings)
    
    def allowBackward(self):
        return False
    
    def expandText(self, findTxt, set_flags=False):
        #python strings in find
        if not findTxt:
            findTxt = ""
        
        if set_flags:
            self.flags = wx.stc.STC_FIND_REGEXP
            
        return findTxt
    




class FindBar(wx.Panel):
    """Find panel customized from PyPE's findbar.py
    
    """
    def __init__(self, parent, frame, stc, storage=None, service=None, direction=1, **kwargs):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        self.frame = frame
        self.stc = stc
        if isinstance(storage, dict):
            self.storage = storage
        else:
            self.storage = {}
        self.settings = FindSettings()
        if service:
            self.service = service(self.stc, self.settings)
        else:
            self.service = FindService(self.stc, self.settings)
        
        self.createCtrls()
        
        # PyPE compat
        self.setDirection(direction)
    
    def createCtrls(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, -1, _(self.service.forward) + u":")
        sizer.Add(self.label, 0, wx.CENTER)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.find, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.find.Bind(wx.EVT_TEXT, self.OnChar)
    
    def setDirection(self, dir=1):
        if dir > 0:
            self._lastcall = self.OnFindN
            text = self.service.forward
        else:
            self._lastcall = self.OnFindP
            text = self.service.backward
        self.label.SetLabel(_(text) + u":")
        self.Layout()

    def OnChar(self, evt):
        #handle updating the background color
        self.resetColor()

        self.service.setFindString(self.find.GetValue())
        
        #search in whatever direction we were before
        self._lastcall(evt, incremental=True)
        
        evt.Skip()

    def OnEnter(self, evt):
        return self._lastcall(evt)
    
    def OnNotFound(self):
        self.find.SetBackgroundColour(wx.RED)
        self.frame.SetStatusText("Search string was not found.")
        self.Refresh()

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
    
    def showLine(self, pos, msg):
        self.resetColor()
        self.frame.SetStatusText(msg)
        line = self.stc.LineFromPosition(pos)
        #self.stc.GotoLine(line)
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
    
    def OnFindN(self, evt, allow_wrap=True, help='', interactive=True, incremental=False):
        self._lastcall = self.OnFindN
        
        posn, st = self.service.doFindNext(incremental=incremental)
        if posn is None:
            self.cancel()
            return
        elif posn != -1:
            if interactive:
                self.showLine(posn, help)
            self.loop = 0
            return
        
        if allow_wrap and st != 0:
            posn, st = self.service.doFindNext(0)
        self.loop = 1
        
        if posn != -1:
            if interactive:
                self.showLine(posn, "Reached end of document, continued from start.")
            return
        
        self.OnNotFound()
    
    def OnFindP(self, evt, allow_wrap=True, help='', incremental=False):
        self._lastcall = self.OnFindP
        
        posn, st = self.service.doFindPrev(incremental=incremental)
        if posn != -1:
            self.showLine(posn, help)
            self.loop = 0
            return
        
        if allow_wrap and st != self.stc.GetTextLength():
            posn, st = self.service.doFindPrev(self.stc.GetTextLength())
        self.loop = 1
        
        if posn != -1:
            self.showLine(posn, "Reached start of document, continued from end.")
            return
        
        self.OnNotFound()

    def repeat(self, direction, service=None):
        if service is not None:
            self.service = service(self.stc, self.settings)
        if not self.settings.find:
            if 'last_search' in self.storage:
                self.settings.find = self.storage['last_search']
                self.find.ChangeValue(self.settings.find)
                self.find.SetInsertionPointEnd()
                return
            
        if direction < 0:
            self.setDirection(-1)
            self.OnFindP(None)
        else:
            self.setDirection(1)
            self.OnFindN(None)
    
    def saveState(self):
        self.settings.serialize(self.storage)


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
        
        self.win = FindBar(self.mode.wrapper, self.mode.frame, self.mode, self.search_storage, direction=dir, service=self.action.find_service)
    
    def repeat(self, action):
        self.win.SetFocus()
        self.win.repeat(action.find_direction, action.find_service)

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
    find_service = FindService
    find_direction = 1

class FindBasicRegex(MinibufferRepeatAction):
    name = "Find Regex..."
    tooltip = "Search for a simple regular expression."
    default_menu = ("Edit", 401)
    icon = "icons/find.png"
    key_bindings = {'emacs': 'C-S-S', }
    minibuffer = FindMinibuffer
    find_service = FindBasicRegexService
    find_direction = 1

class FindPrevText(MinibufferRepeatAction):
    name = "Find Previous..."
    tooltip = "Search backwards for a string in the text."
    default_menu = ("Edit", 402)
    key_bindings = {'default': "C-S-F", 'emacs': 'C-R', }
    minibuffer = FindMinibuffer
    find_service = FindService
    find_direction = -1




class FakeButton(wx.lib.stattext.GenStaticText):
    """Simple text label that accepts focus.
    
    Used as the key processor for replace.  This label accepts focus but
    doesn't display any indicator that focus has been taken, so it looks like
    an ordinary label.  However, events can be processed through this label
    and it is used to handle the keyboard commands for replacing.
    """
    def AcceptsFocus(self):
        return True

class ReplaceBar(FindBar):
    """Replace panel in the style of the Emacs replace function
    
    The control of the minibuffer is similar to emacs:
    
    Type the search string in 'Replace:' and hit enter.  Type the replacement
    string in 'with:' and hit enter.  Then, use the keyboard to control the
    replacements: 'y' or 'space' to replace one match, 'n' or 'delete' to skip
    to the next match, 'q' to quit, '.' to replace one match and quit, '!' to
    replace all remaining matches', 'p' or '^' to move to the previous match.
    """
    replace = "Replace"
    replace_regex = "Regex Replace"
    help_status = "y: replace, n: skip, q: exit, !:replace all"
    
    def __init__(self, *args, **kwargs):
        FindBar.__init__(self, *args, **kwargs)
        
        if 'on_exit' in kwargs:
            self.on_exit = kwargs['on_exit']
        else:
            self.on_exit = None
        
        # Count of number of replacements
        self.count = 0
        
        # Last cursor position, tracked during replace all
        self.last_cursor = 0
    
    def createCtrls(self):
        text = self.service.replace
        grid = wx.GridBagSizer(0, 0)
        self.label = wx.StaticText(self, -1, _(text) + u":")
        grid.Add(self.label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.find, (0, 1), flag=wx.EXPAND)
        self.replace = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.replace, (1, 1), flag=wx.EXPAND)
        
        # Windows doesn't process char events through a real button, so we use
        # this fake button as a label and process events through it.  It's
        # added here so that it will be last in the tab order.
        self.command = FakeButton(self, -1, _("with") + u":")
        grid.Add(self.command, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        
        grid.AddGrowableCol(1)
        self.SetSizer(grid)
        
        self.find.Bind(wx.EVT_TEXT_ENTER, self.OnTabToReplace)
        self.find.Bind(wx.EVT_SET_FOCUS, self.OnFindSetFocus)
        self.replace.Bind(wx.EVT_TEXT_ENTER, self.OnTabToCommand)
        self.replace.Bind(wx.EVT_SET_FOCUS, self.OnReplaceSetFocus)
        self.command.Bind(wx.EVT_BUTTON, self.OnReplace)
        self.command.Bind(wx.EVT_KEY_DOWN, self.OnCommandKeyDown)
        self.command.Bind(wx.EVT_CHAR, self.OnCommandChar)
        self.command.Bind(wx.EVT_SET_FOCUS, self.OnSearchStart)
        self.command.Bind(wx.EVT_KILL_FOCUS, self.OnSearchStop)
    
    def setDirection(self, dir=1):
        self.label.SetLabel(_(self.service.replace) + u":")
        self.Layout()

    def OnFindSetFocus(self, evt):
        self.frame.SetStatusText("Enter search text and press Return")
    
    def OnReplaceSetFocus(self, evt):
        self.frame.SetStatusText("Enter replacement text and press Return")
    
    def OnTabToReplace(self, evt):
        self.replace.SetFocus()
    
    def OnTabToCommand(self, evt):
        self.command.SetFocus()
    
    def OnSearchStart(self, evt):
        self.service.setFindString(self.find.GetValue())
        self.service.setReplaceString(self.replace.GetValue())
        self.OnFindN(evt, help=self.help_status)
    
    def OnSearchStop(self, evt):
        self.cancel()
        
    def OnReplace(self, evt, find_next=True, interactive=True):
        """Replace the selection
        
        The bulk of this algorithm is from PyPE.
        """
        allow_wrap = not interactive
        sel = self.stc.GetSelection()
        if sel[0] == sel[1]:
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            return (-1, -1), 0
        
        if self.service.doReplace() >= 0:
            start, self.last_cursor = self.stc.GetSelection()
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            self.count += 1
            
            return sel, self.last_cursor - start + 1
        else:
            return (-1, -1), 0
    
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
        dprint("key=%s mods=%s" % (key, mods))
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
        dprint("uchar = %s" % uchar)
        if uchar in u'nN':
            self.OnFindN(None, help=self.help_status)
        elif uchar in u'yY ':
            self.OnReplace(None)
        elif uchar in u'pP^':
            self.OnFindP(None, help=self.help_status)
        elif uchar in u'qQ':
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
    tooltip = "Replace a string in the text."
    default_menu = ("Edit", 410)
    icon = "icons/text_replace.png"
    key_bindings = {'win': 'C-H', 'emacs': 'F6', }
    minibuffer = ReplaceMinibuffer


class FindReplacePlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getActions(self):
        return [FindText, FindBasicRegex, FindPrevText,
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
            
            self.search_back = FindBar(self, self, self.stc, direction=-1)
            sizer.Add(self.search_back, 0, wx.EXPAND)
            
            self.search_regex = FindBar(self, self, self.stc, service=FindBasicRegexService)
            sizer.Add(self.search_regex, 0, wx.EXPAND)
            
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
    frame = Frame(None, size=(-1, 600))
    frame.loadSample()
    frame.Show()
    app.MainLoop()
