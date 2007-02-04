import os

import wx
import wx.stc as stc

from major import *
from plugin import *
from debug import *


class MinibufferAction(MajorAction):
    def majoraction(self, mode, pos=-1):
        minibuffer=self.minibuffer(mode)
        #print minibuffer.win
        mode.setMinibuffer(minibuffer)


class Minibuffer(debugmixin):
    """
    Base class for an action that is implemented using the minibuffer.
    Minibuffer is a concept from emacs where, instead of popping up a
    dialog box, uses the bottom of the screen as a small user input
    window.
    """
    def __init__(self, mode):
        self.win=None
        self.mode=mode
        self.minibuffer(mode)
        
    def minibuffer(self, mode):
        """
        set create a window that represents the minibuffer, and set
        self.win to that window.
        """
        raise NotImplementedError

    def focus(self):
        self.dprint("focus!!!")
        self.win.SetFocus()
    
    def close(self):
        self.win.Destroy()
        self.win=None

    def done(self):
        wx.CallAfter(self.mode.removeMinibuffer)
        



class IntMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for an integer.
    """
    
    def minibuffer(self, mode, label="Integer"):
        self.win=wx.Panel(mode.win, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        label=wx.StaticText(self.win, -1, label)
        sizer.Add(label, flag=wx.EXPAND)
        self.text=wx.TextCtrl(self.win, -1, size=(125,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text, flag=wx.EXPAND)
        self.win.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

    def OnInt(self, number):
        return NotImplementedError

    def OnEnter(self, evt):
        try:
            number=int(self.text.GetValue())
            self.dprint("number=%s" % number)
            pos=self.OnInt(number)
        except:
            self.mode.frame.SetStatusText("Not an integer.")
        self.done()

