import os

import wx
import wx.stc as stc

from major import *
from plugin import *
from debug import *


class MinibufferAction(MajorAction):
    def majoraction(self, viewer, pos=-1):
        minibuffer=self.minibuffer(viewer)
        #print minibuffer.win
        viewer.setMinibuffer(minibuffer)


class Minibuffer(debugmixin):
    def __init__(self,viewer):
        self.win=None
        self.viewer=viewer
        self.minibuffer(viewer)
        
    def minibuffer(self,viewer):
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
        wx.CallAfter(self.viewer.removeMinibuffer)
        



class IntMinibuffer(Minibuffer):
    def minibuffer(self, viewer, label="Integer"):
        self.win=wx.Panel(viewer.win, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        sizer=wx.BoxSizer(wx.HORIZONTAL)
        label=wx.StaticText(self.win,-1,label)
        sizer.Add(label,flag=wx.EXPAND)
        self.text=wx.TextCtrl(self.win,-1,size=(125,-1),style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text,flag=wx.EXPAND)
        self.win.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT_ENTER,self.OnEnter)

    def OnInt(self, number):
        return NotImplementedError

    def OnEnter(self, evt):
        try:
            number=int(self.text.GetValue())
            self.dprint("number=%s" % number)
            pos=self.OnInt(number)
        except:
            self.viewer.frame.SetStatusText("Not an integer.")
        self.done()

