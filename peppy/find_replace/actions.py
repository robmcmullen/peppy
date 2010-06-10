# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Actions and minibuffer definitions for the find and replace plugin

This module includes the actions and minibuffer definitions used by the
L{FindReplacePlugin} to define the user interface to the L{FindService} that
is appropriate to each major mode.
"""

import os, glob, re

import wx
import wx.lib.stattext
from wx.lib.pubsub import Publisher

from peppy.actions.minibuffer import *

from peppy.actions import *
from peppy.actions.base import *
from peppy.debug import *

from services import *


class FindBar(wx.Panel, debugmixin):
    """Find panel customized from PyPE's findbar.py
    
    """
    debuglevel = 0
    
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
        self._lastcall = None
        self.setDirection(direction)
        
        self.repeatLastUserInput()
    
    def createCtrls(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, -1, _(self.service.forward) + u":")
        sizer.Add(self.label, 0, wx.CENTER)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.find, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.find.Bind(wx.EVT_TEXT, self.OnChanged)
        
    def setDirection(self, dir=1):
        if dir > 0:
            self._lastcall = self.OnFindN
            text = self.service.forward
        else:
            self._lastcall = self.OnFindP
            text = self.service.backward
        self.label.SetLabel(_(text) + u":")
        self.Layout()
    
    def OnChanged(self, evt):
        #handle updating the background color
        self.resetColor()

        self.service.setFindString(self.find.GetValue())
        self.service.resetFirstFound()
        
        #search in whatever direction we were before
        self._lastcall(evt, incremental=True)
        
        evt.Skip()
    
    def OnNotFound(self, msg=None):
        self.find.SetForegroundColour(wx.RED)
        if msg is None:
            msg = _("Search string was not found.")
        self.frame.SetStatusText(msg)
        self.Refresh()
        
    def OnFinished(self, msg=None):
        self.find.SetForegroundColour(wx.GREEN)
        if msg is None:
            msg = _("Returned to the starting point")
        self.frame.SetStatusText(msg)
        self.Refresh()

    def resetColor(self):
        if self.find.GetForegroundColour() != wx.BLACK:
            self.find.SetForegroundColour(wx.BLACK)
            self.Refresh()

    def showLine(self, pos, msg):
        self.dprint()
        self.resetColor()
        self.dprint()
        self.frame.SetStatusText(msg)
        self.dprint()
        line = self.stc.LineFromPosition(pos)
        self.dprint()
        if not self.stc.GetLineVisible(line):
            self.stc.EnsureVisible(line)
        self.dprint()
        self.stc.EnsureCaretVisible()
        self.dprint()
    
    def cancel(self, pos_at_end=False):
        self.resetColor()
        self.frame.SetStatusText('')
        self.removeSelection(pos_at_end)
    
    def removeSelection(self, pos_at_end=False):
        """Remove the selected text and place the cursor at either the
        beginning or the end of the selection.
        """
        if pos_at_end:
            pos = self.stc.GetSelectionEnd()
        else:
            pos = self.stc.GetSelectionStart()
        self.stc.GotoPos(pos)
        self.stc.EnsureCaretVisible()
    
    def OnFindN(self, evt, allow_wrap=True, help='', interactive=True, incremental=False):
        self._lastcall = self.OnFindN
        
        posn, st = self.service.doFindNext(incremental=incremental)
        self.dprint("start=%s pos=%s" % (st, posn))
        if posn is None:
            self.cancel()
            return
        elif not isinstance(posn, int):
            return self.OnNotFound(posn)
        elif posn != -1:
            self.dprint("interactive=%s" % interactive)
            if interactive:
                self.showLine(posn, help)
            if self.service.isEntireDocumentChecked(posn, 1):
                self.OnFinished()
            return
        
        if allow_wrap and st != 0:
            posn, st = self.service.doFindNext(0)
            self.dprint("wrapped: start=%d pos=%d" % (st, posn))
        self.service.setWrapped()
        
        if posn != -1:
            if interactive:
                self.showLine(posn, "Reached end of document, continued from start.")
            if self.service.isEntireDocumentChecked(posn, 1):
                self.OnFinished()
            return
        
        self.dprint("not found: start=%d pos=%d" % (st, posn))
        self.OnNotFound()
    
    def OnFindP(self, evt, allow_wrap=True, help='', incremental=False):
        self._lastcall = self.OnFindP
        
        posn, st = self.service.doFindPrev(incremental=incremental)
        if posn is None:
            self.cancel()
            return
        elif not isinstance(posn, int):
            return self.OnNotFound(posn)
        elif posn != -1:
            self.showLine(posn, help)
            if self.service.isEntireDocumentChecked(posn, -1):
                self.OnFinished()
            return
        
        if allow_wrap and st != self.stc.GetTextLength():
            posn, st = self.service.doFindPrev(self.stc.GetTextLength())
        self.service.setWrapped()
        
        if posn != -1:
            self.showLine(posn, "Reached start of document, continued from end.")
            if self.service.isEntireDocumentChecked(posn, -1):
                self.OnFinished()
            return
        
        self.OnNotFound()
    
    def repeatLastUserInput(self):
        """Load the user interface with the last saved user input
        
        @return: True if user input was loaded from the storage space
        """
        if not self.settings.find_user:
            self.service.unserialize(self.storage)
            self.find.ChangeValue(self.settings.find_user)
            self.find.SetInsertionPointEnd()
            self.find.SetSelection(0, self.find.GetLastPosition())
            return True
        return False

    def repeat(self, direction, service=None, last_focus=None):
        self.resetColor()
        if service is not None:
            self.service = service(self.stc, self.settings)
        
        if direction < 0:
            self.setDirection(-1)
        else:
            self.setDirection(1)
        
        if self.repeatLastUserInput():
            return
        
        # If this method gets called but the last object to have focus wasn't
        # the find textfield, that means that the search minibuffer existed
        # but the user was typing in the main editing window.  The search
        # string should then be highlighted in case the user wants to start a
        # new search from scratch.
        if last_focus != self.find:
            self.find.SetInsertionPointEnd()
            self.find.SetSelection(0, self.find.GetLastPosition())
            return
        
        # replace doesn't use an automatic search, so make sure that a method
        # has been specified before calling it
        if self._lastcall:
            self._lastcall(None)
    
    def saveState(self):
        self.service.serialize(self.storage)









class MinibufferFindMixin(object):
    @classmethod
    def worksWithSpecificMinibuffer(self, minibuffer):
        return isinstance(minibuffer, FindMinibuffer)

    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, FindMinibuffer) and isinstance(ctrl, wx.TextCtrl)


class FindBarMoveFocusToText(MinibufferFindMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'TAB',}
    
    def actionKeystroke(self, evt, multiplier=1):
        self.minibuffer.mode.focus()


class FindBarFindNext(MinibufferFindMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'RET',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, FindMinibuffer) and isinstance(ctrl, wx.TextCtrl)

    def actionKeystroke(self, evt, multiplier=1):
        msg = ""
        for i in range(multiplier):
            self.minibuffer.win._lastcall(evt)




class FindReplaceMinibufferMixin(object):
    """Mixin class for both find and replace minibuffers
    """
    search_storage = {}
    
    def getHelp(self):
        return self.win.service.help

    def repeat(self, action):
        last_focus = self.win.FindFocus()
        self.win.SetFocus()
        self.win.repeat(action.find_direction, action.find_service, last_focus)

    def focus(self):
        dprint("focus to %s" % self.win.find)
        self.win.find.SetFocus()
    
    def closePreHook(self):
        self.win.saveState()
        self.dprint(self.search_storage)


class FindMinibuffer(FindReplaceMinibufferMixin, Minibuffer):
    """Minibuffer for the incremental search function
    """
    search_storage = {}
    
    def createWindow(self, parent, **kwargs):
        self.win = FindBar(parent, self.mode.frame, self.mode, self.search_storage, direction=self.action.find_direction, service=self.action.find_service)


class FindText(MinibufferRepeatAction):
    """Search for a string in the text."""
    name = "Find..."
    default_menu = ("Edit", -400)
    icon = "icons/find.png"
    key_bindings = {'default': "C-f", 'emacs': 'C-s', }
    minibuffer = FindMinibuffer
    find_service = FindService
    find_direction = 1

class FindRegex(MinibufferRepeatAction):
    """Search for a python regular expression."""
    name = "Find Regex..."
    default_menu = ("Edit", 401)
    key_bindings = {'emacs': 'C-M-s', }
    minibuffer = FindMinibuffer
    find_service = FindRegexService
    find_direction = 1

class FindWildcard(MinibufferRepeatAction):
    """Search using shell-style wildcards."""
    name = "Find Wildcard..."
    default_menu = ("Edit", 402)
    key_bindings = {'emacs': 'C-S-M-s', }
    minibuffer = FindMinibuffer
    find_service = FindWildcardService
    find_direction = 1

class FindPrevText(MinibufferRepeatAction):
    """Search backwards for a string in the text."""
    name = "Find Previous..."
    default_menu = ("Edit", 402)
    key_bindings = {'default': "C-S-f", 'emacs': 'C-r', }
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
    replacements:
    
    'y' or SPACE: replace one match and advance to the next match
    ',': replace the current match but not advance to the next match
    'n' or DELETE: skip to the next match
    'p' or '^': move to the previous match
    'q': quit matching and remove the replace bar
    '.': replace one match and quit matching
    '!': replace all remaining matches and quit matching
    """
    help_status = "y: replace, n: skip, q: exit, !:replace all, f: edit find, r: edit replace, ?: help"
    
    def __init__(self, *args, **kwargs):
        FindBar.__init__(self, *args, **kwargs)
        
        if 'on_exit' in kwargs:
            self.on_exit = kwargs['on_exit']
        else:
            self.on_exit = None
        
        # Count of number of replacements
        self.count = 0
        
        # focus tracker to make sure that focus events come from us
        self.focus_tracker = None
    
    def createCtrls(self):
        text = self.service.forward
        grid = wx.GridBagSizer(2, 2)
        self.label = wx.StaticText(self, -1, _(text) + u":")
        grid.Add(self.label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.find = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.find, (0, 1), flag=wx.EXPAND)
        self.replace = wx.TextCtrl(self, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        grid.Add(self.replace, (1, 1), flag=wx.EXPAND)
        
        # Windows doesn't process char events through a real button, so we use
        # this fake button as a label and process events through it.  It's
        # added here so that it will be last in the tab order.
        self.command = FakeButton(self, -1, _("Replace with") + u":")
        grid.Add(self.command, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        
        grid.AddGrowableCol(1)
        self.SetSizer(grid)
        
        self.find.Bind(wx.EVT_SET_FOCUS, self.OnFindSetFocus)
        self.replace.Bind(wx.EVT_KILL_FOCUS, self.OnReplaceLoseFocus)
        self.replace.Bind(wx.EVT_SET_FOCUS, self.OnReplaceSetFocus)
        self.command.Bind(wx.EVT_BUTTON, self.OnReplace)
        self.command.Bind(wx.EVT_SET_FOCUS, self.OnSearchStart)
    
    def OnReplaceError(self, msg=None):
        self.replace.SetForegroundColour(wx.RED)
        self.frame.SetStatusText(msg)
        self.Refresh()

    def resetColor(self):
        if self.replace.GetBackgroundColour() != wx.WHITE:
            self.replace.SetBackgroundColour(wx.WHITE)
            self.replace.Refresh()
        FindBar.resetColor(self)

    def setDirection(self, dir=1):
        self.label.SetLabel(_(self.service.forward) + u":")
        self.Layout()

    def OnFindSetFocus(self, evt):
        self.dprint(evt.GetWindow())
        self.cancel()
        self.frame.SetStatusText("Enter search text and press Return")
        evt.Skip()
    
    def OnReplaceSetFocus(self, evt):
        self.dprint(evt.GetWindow())
        self.frame.SetStatusText("Enter replacement text and press Return")
        self.focus_tracker = True
        evt.Skip()
    
    def OnReplaceLoseFocus(self, evt):
        self.dprint(evt.GetWindow())
        # Using tab after changing color when a selection exists in
        # self.replace causes the text to appear white on a white background.
        # Force the selection to disappear when tabbing off of self.replace
        self.replace.SetInsertionPointEnd()
        evt.Skip()
    
    def OnTabToFind(self, evt):
        self.find.SetFocus()
    
    def OnTabToReplace(self, evt):
        self.replace.SetFocus()
    
    def OnTabToCommand(self, evt):
        # Using tab after changing color when a selection exists in
        # self.replace causes the text to appear white on a white background.
        # Force the selection to disappear when tabbing off of self.replace
        self.replace.SetInsertionPointEnd()
        self.command.SetFocus()
    
    def OnSearchStart(self, evt):
        #dprint(self.focus_tracker)
        if self.focus_tracker:
            self.service.setFindString(self.find.GetValue())
            self.service.setReplaceString(self.replace.GetValue())
            #dprint("find=%s replace=%s" % (self.service.settings.find, self.service.settings.replace))
            self.OnFindN(evt, help=self.help_status)
            self.focus_tracker = False
    
    def OnReplace(self, evt, find_next=True, interactive=True):
        """Replace the selection
        
        The bulk of this algorithm is from PyPE.
        """
        if self.stc.GetReadOnly():
            return False

        allow_wrap = interactive
        if not self.service.hasMatch():
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            return True
        
        try:
            self.service.doReplace()
            if find_next:
                self.OnFindN(None, allow_wrap=allow_wrap, help=self.help_status, interactive=interactive)
            self.count += 1
                
            return True
        except ReplacementError, e:
            self.OnReplaceError(str(e))
        return False
    
    def OnReplaceAll(self, evt):
        self.count = 0
        last_cursor = self.stc.GetCurrentPos()
        self.service.setWrapped(False)
        
        # FIXME: this takes more time than it should, probably because there's
        # a lot of redundant stuff going on in OnReplace.  This should be
        # rewritten for speed at some point.
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(True)
            wx.Yield()
        self.stc.BeginUndoAction()
        valid = True
        try:
            while not self.service.isWrapped() and valid:
                valid = self.OnReplace(None, interactive=False)
                last_cursor = self.stc.GetSelectionEnd()
            self.stc.GotoPos(last_cursor)
        finally:
            self.stc.EndUndoAction()
        
        if hasattr(self.stc, 'showBusy'):
            self.stc.showBusy(False)
        if valid:
            if self.count == 1:
                occurrences = _("Replaced %d occurrence")
            else:
                occurrences = _("Replaced %d occurrences")
            self.OnExit(msg=_(occurrences) % self.count)
    
    def OnExit(self, msg=''):
        self.cancel(pos_at_end=True)
        if msg:
            self.frame.SetStatusText(msg)
        if self.on_exit:
            wx.CallAfter(self.on_exit)

    def repeatLastUserInput(self):
        """Load the user interface with the last saved user input
        
        @return: True if user input was loaded from the storage space
        """
        # disable the repeat search when using the replace buffer
        self._lastcall = None
        
        # Set the focus to the find string to prevent the focus from staying on
        # the command control.  Unless this is done, the focus tends to stay
        # on the command control which highlights the last successful search.
        self.find.SetFocus()
        
        if not self.settings.find_user:
            self.service.unserialize(self.storage)
            self.find.ChangeValue(self.settings.find_user)
            self.find.SetInsertionPointEnd()
            self.replace.ChangeValue(self.settings.replace_user)
            self.replace.SetInsertionPointEnd()
            return True
        return False


class ReplaceMinibuffer(FindReplaceMinibufferMixin, Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    search_storage = {}
    
    def createWindow(self, parent, **kwargs):
        self.win = ReplaceBar(parent, self.mode.frame, self.mode,
                              self.search_storage, on_exit=self.removeFromParent,
                              direction=self.action.find_direction,
                              service=self.action.find_service)



class MinibufferReplaceMixin(object):
    @classmethod
    def worksWithSpecificMinibuffer(self, minibuffer):
        return isinstance(minibuffer, ReplaceMinibuffer)


class ReplaceBarCommand(MinibufferReplaceMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'default',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, ReplaceMinibuffer) and isinstance(ctrl, FakeButton)

    def actionKeystroke(self, evt, multiplier=1):
        uchar = unichr(evt.GetKeyCode())
        for i in range(multiplier):
            if uchar in u'nN':
                self.minibuffer.win.OnFindN(None, help=self.minibuffer.win.help_status)
            elif uchar in u'yY ':
                self.minibuffer.win.OnReplace(None)
            elif uchar in u'pP^':
                self.minibuffer.win.OnFindP(None, help=self.minibuffer.win.help_status)
            elif uchar in u'qQ':
                self.minibuffer.win.OnExit()
            elif uchar in u'.':
                self.minibuffer.win.OnReplace(None, find_next=False)
                self.minibuffer.win.OnExit()
            elif uchar in u',':
                self.minibuffer.win.OnReplace(None, find_next=False)
            elif uchar in u'!':
                self.minibuffer.win.OnReplaceAll(None)
            elif uchar in u'fF':
                self.minibuffer.win.OnTabToFind(None)
            elif uchar in u'rR':
                self.minibuffer.win.OnTabToReplace(None)
            elif uchar in u'?':
                Publisher().sendMessage('peppy.log.info', (self.minibuffer.mode.frame, self.minibuffer.win.__doc__))
                break


class ReplaceBarMoveFocus(MinibufferReplaceMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'TAB',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, ReplaceMinibuffer)

    def actionKeystroke(self, evt, multiplier=1):
        focus = self.minibuffer.win.FindFocus()
        if focus == self.minibuffer.win.find:
            self.minibuffer.win.OnTabToReplace(None)
        elif focus == self.minibuffer.win.replace:
            self.minibuffer.win.OnTabToCommand(None)
        elif focus == self.minibuffer.win.command:
            self.minibuffer.win.OnTabToFind(None)
        else:
            dprint("Unknown focus!!!")


class ReplaceBarMoveFocusRet(MinibufferReplaceMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'RET',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, ReplaceMinibuffer) and isinstance(ctrl, wx.TextCtrl)

    def actionKeystroke(self, evt, multiplier=1):
        focus = self.minibuffer.win.FindFocus()
        if focus == self.minibuffer.win.find:
            self.minibuffer.win.OnTabToReplace(None)
        elif focus == self.minibuffer.win.replace:
            self.minibuffer.win.OnTabToCommand(None)


class ReplaceBarFindNext(MinibufferReplaceMixin, MinibufferKeyboardAction):
    key_bindings = {'default': ['RET', 'DELETE',],}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return isinstance(minibuffer, ReplaceMinibuffer) and ctrl == minibuffer.win.command

    def actionKeystroke(self, evt, multiplier=1):
        self.minibuffer.win.OnFindN(None, help=self.minibuffer.win.help_status)
    


class Replace(MinibufferRepeatAction):
    """Replace a string in the text."""
    name = "Replace..."
    default_menu = ("Edit", 410)
    icon = "icons/text_replace.png"
    key_bindings = {'win': 'C-h', 'emacs': 'F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindService
    find_direction = 1

class ReplaceRegex(MinibufferRepeatAction):
    """Replace using python regular expressions."""
    name = "Replace Regex..."
    default_menu = ("Edit", 411)
    key_bindings = {'emacs': 'S-F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindRegexService
    find_direction = 1

class ReplaceWildcard(MinibufferRepeatAction):
    """Replace using shell-style wildcards."""
    name = "Replace Wildcard..."
    default_menu = ("Edit", 411)
    key_bindings = {'emacs': 'M-F6', }
    minibuffer = ReplaceMinibuffer
    find_service = FindWildcardService
    find_direction = 1


class CaseSensitiveSearch(ToggleAction):
    """Should search string require match by case"""
    name = "Case Sensitive Search"
    default_menu = ("Edit", 499)
    
    def isChecked(self):
        return self.mode.locals.case_sensitive_search

    def action(self, index=-1, multiplier=1):
        self.mode.locals.case_sensitive_search = not self.mode.locals.case_sensitive_search

class WholeWordSearch(ToggleAction):
    """Should search string exactly matching within sep"""
    name = "Whole Word Search"
    author = "\u0412\u043e\u0432\u0430 \u0410\u043d\u0442\u043e\u043d\u043e\u0432"
    default_menu = ("Edit", 499)
    
    def isChecked(self):
        return self.mode.locals.whole_word_search

    def action(self, index=-1, multiplier=1):
        self.mode.locals.whole_word_search = not self.mode.locals.whole_word_search


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
            self.doTests()

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
        
        def doTests(self):
            tests = [
                ("(.+) (.+)", "\\u\\1 \\l\\2 upper=\\U\\1 upper \\2\\E lower=\\L\\1 LoWeR \\2\\E", "blah STUFF"),
                ("(_)?spell([A-Z].+)", "\\1\\l\\2", "spellCheck"),
                ]
            service = FindRegexService(self)
            service.__class__.debuglevel = 1
            for search, replace, string in tests:
                service.setFindString(search)
                service.setReplaceString(replace)
                service.getFlags()
                dprint(service.getReplacement(string))
        
    app = wx.App(False)
    frame = Frame(None, size=(-1, 600))
    frame.loadSample()
    frame.Show()
    app.MainLoop()
