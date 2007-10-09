# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os

import wx
import wx.stc

from peppy.major import *
from peppy.debug import *
from peppy.lib.textctrl_autocomplete import TextCtrlAutoComplete

class MinibufferAction(BufferModificationAction):
    minibuffer_label = None
    
    def action(self, index=-1, multiplier=1):
        minibuffer=self.minibuffer(self.mode, self,
                                   label=self.minibuffer_label)
        #print minibuffer.win
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        assert self.dprint("processing %s" % text)


class Minibuffer(debugmixin):
    """
    Base class for an action that is implemented using the minibuffer.
    Minibuffer is a concept from emacs where, instead of popping up a
    dialog box, uses the bottom of the screen as a small user input
    window.
    """
    label = "Input:"
    error = "Bad input."
    
    def __init__(self, mode, action, label=None, error=None, initial=None,
                 **kwargs):
        self.win=None
        self.mode=mode
        self.action = action
        if error is not None:
            self.error = error
        if label is not None:
            self.label = label
        self.initial = initial
        self.createWindow()
        
    def createWindow(self):
        """
        Create a window that represents the minibuffer, and set
        self.win to that window.
        """
        raise NotImplementedError

    def focus(self):
        """
        Set the focus to the component in the menubar that should get
        the text focus.
        """
        assert self.dprint("focus!!!")
        self.win.SetFocus()
    
    def close(self):
        """
        Destroy the minibuffer widgets.
        """
        self.win.Destroy()
        self.win=None

    def removeFromParent(self):
        """
        Convenience routine to destroy minibuffer after the event loop
        exits.
        """
        wx.CallAfter(self.mode.removeMinibuffer, self)
        



class TextMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a text string
    """
    debuglevel = 0
    
    label = "Text"
    error = "Bad input."
    
    def createWindow(self):
        self.win = wx.Panel(self.mode, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.win, -1, self.label)
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = wx.TextCtrl(self.win, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.win.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

        if self.initial:
            self.text.ChangeValue(self.initial)

    def convert(self, text):
        return text

    def OnEnter(self, evt):
        text = self.text.GetValue()
        assert self.dprint("text=%s" % text)
        try:
            text = self.convert(text)
        except:
            self.mode.frame.SetStatusText(self.error)
            text = None

        if text is not None:
            error = self.action.processMinibuffer(self, self.mode, text)
            if error is not None:
                self.mode.frame.SetStatusText(error)
        self.removeFromParent()

class IntMinibuffer(TextMinibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for an integer.
    """
    label = "Integer"
    error = "Not an integer."
    
    def convert(self, text):
        text = self.text.GetValue().strip().lower()
        if text.startswith("0x"):
            base = 16
        elif text.endswith("h"):
            base = 16
            text = text[:-1]
        else:
            base = 10
        number = int(text, base)
        assert self.dprint("number=%s" % number)
        return number

class FloatMinibuffer(TextMinibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a floating point
    number.
    """
    label = "Floating Point"
    error = "Not a number."
    
    def convert(self, text):
        number = float(self.text.GetValue())
        assert self.dprint("number=%s" % number)
        return number


class InPlaceCompletionMinibuffer(TextMinibuffer):
    """Base class for a simple autocompletion minibuffer.

    This completion style is like Outlook's email address completion
    where it suggests the best completion ahead of the cursor,
    adjusting as you type.  There is no dropdown list; everything is
    handled in the text ctrl.

    This class doesn't implement the complete method, leaving its
    implementation to subclasses.
    """
    def createWindow(self):
        self.win = wx.Panel(self.mode, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.win, -1, self.label)
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = wx.TextCtrl(self.win, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.win.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.text.Bind(wx.EVT_TEXT, self.OnText)
        self.text.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        if self.initial:
            self.text.ChangeValue(self.initial)

        self.win.saveSetFocus = self.win.SetFocus
        self.win.SetFocus = self.SetFocus
        
    def SetFocus(self):
        self.win.saveSetFocus()
        self.text.SetInsertionPointEnd()

    def OnText(self, evt):
        text = evt.GetString()
        dprint(text)
        evt.Skip()

    def complete(self, text):
        """Generate the completion list.

        The best guess should be returned as the first item in the
        list, with each subsequent entry being less probable.
        """
        raise NotImplementedError

    def processCompletion(self, text):
        guesses = self.complete(text)
        if guesses:
            self.text.SetValue(guesses[0])
            self.text.SetSelection(len(text), -1)

    def OnKeyDown(self, evt):
        key = evt.GetKeyCode()
        #dprint(key)
        if key == wx.WXK_TAB:
            self.processCompletion(self.text.GetValue())
            # don't call Skip() here.  That way wx knows not to
            # continue on to the EVT_TEXT callback
            return
        evt.Skip()

class CompletionMinibuffer(TextMinibuffer):
    """Base class for a minibuffer based on the TextCtrlAutoComplete
    widget from the wxpython list.

    This class doesn't implement the complete method, leaving its
    implementation to subclasses.
    """
    def createWindow(self):
        self.win = wx.Panel(self.mode, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.win, -1, self.label)
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = TextCtrlAutoComplete(self.win, choices=[], size=(-1,-1), style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.win.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

        if self.initial:
            self.text.ChangeValue(self.initial)
            self.text.SetChoices(self.complete(self.initial))
        self.text.SetEntryCallback(self.setDynamicChoices)

        self.win.saveSetFocus = self.win.SetFocus
        self.win.SetFocus = self.SetFocus
        
    def SetFocus(self):
        self.win.saveSetFocus()
        self.text.SetInsertionPointEnd()

    def complete(self, text):
        raise NotImplementedError
        
    def setDynamicChoices(self):
        ctrl = self.text
        text = ctrl.GetValue()
        current_choices = ctrl.GetChoices()
        choices = self.complete(text)
        self.dprint(choices)
        if choices != current_choices:
            ctrl.SetChoices(choices)

class StaticListCompletionMinibuffer(CompletionMinibuffer):
    """Completion minibuffer where the list of possibilities doesn't change.

    This is used to complete on a static list of items.  This doesn't
    handle cases like searching through the filesystem where a new
    list of matches is generated when you hit a new directory.
    """
    def __init__(self, *args, **kwargs):
        if 'list' in kwargs:
            self.sorted = kwargs['list']
        else:
            self.sorted = []
        CompletionMinibuffer.__init__(self, *args, **kwargs)
        
    def complete(self, text):
        """Return the list of completions that start with the given text"""
        found = []
        for match in self.sorted:
            if match.startswith(text):
                found.append(match)
        return found
