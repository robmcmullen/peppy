# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os

import wx
import wx.stc

from peppy.major import *
from peppy.debug import *


class MinibufferAction(BufferModificationAction):
    minibuffer_label = None
    
    def modify(self, mode, pos=-1):
        minibuffer=self.minibuffer(mode, self, label=self.minibuffer_label)
        #print minibuffer.win
        mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, mode, text):
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
    
    def __init__(self, mode, action, label=None, error=None):
        self.win=None
        self.mode=mode
        self.action = action
        if error is not None:
            self.error = error
        if label is not None:
            self.label = label
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
        wx.CallAfter(self.mode.removeMinibuffer)
        



class TextMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a text string
    """
    debuglevel = 1
    
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

    def convert(self, text):
        return text

    def OnEnter(self, evt):
        text = self.text.GetValue()
        assert self.dprint("text=%s" % text)
        try:
            text = self.convert(text)
            error = self.action.processMinibuffer(self.mode, text)
            if error is not None:
                self.mode.frame.SetStatusText(error)
        except:
            self.mode.frame.SetStatusText(self.error)
        self.removeFromParent()

class IntMinibuffer(TextMinibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for an integer.
    """
    label = "Integer"
    error = "Not an integer."
    
    def convert(self, text):
        number = int(self.text.GetValue())
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
