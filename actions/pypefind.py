import os

import wx
import wx.stc as stc

from actions.minibuffer import *

from pype import findbar


class PypeFindReplaceAdapterMixin(object):
    def readPreferences(self):
        # A bit of a trick here.  This is called before the setup
        # routine, so we can use this hook to reset self.parent to our
        # adapter object: FindMinibuffer.  At __init__, self.parent
        # points to the parent wx.Frame object, but after that,
        # self.parent isn't used in that capacity.  So, we can point
        # self.parent to our adapter object and then extend the
        # adapter object to do what pype needs.  The point of all this
        # is that I want to keep the pype adapter clutter out of
        # MajorMode or FundamentalMode.
        self.parent=self.root
        self.pypecls=self.GetPypeSubclass()
        self.pypecls.readPreferences(self)

    def Destroy(self):
        self.pypecls.Destroy(self)

class PypeFindBar(PypeFindReplaceAdapterMixin,findbar.FindBar):
    def GetPypeSubclass(self):
        return findbar.FindBar

class PypeReplaceBar(PypeFindReplaceAdapterMixin,findbar.ReplaceBar):
    def GetPypeSubclass(self):
        return findbar.ReplaceBar    

class FindMinibuffer(Minibuffer):
    """
    Adapter for PyPE findbar.  Maps findbar callbacks to our stuff.
    """
    def minibuffer(self, viewer):
        self.win=PypeFindBar(viewer.win,self)
        print "findbar=%s" % self.win

    def focus(self):
        self.win.box1.SetFocus()

    def close(self):
        # Don't destroy the window here because pype's OnCloseBar
        # callback destroys it.
        pass

    #### PyPE Compatability

    def getglobal(self, param):
        return None

    def SetStatusText(self, text, log=None):
        self.viewer.frame.SetStatusText(text)

    def GetWindow1(self):
        return self.viewer.stc

    def Unsplit(self):
        self.viewer.removeMinibuffer()

    
class ReplaceMinibuffer(FindMinibuffer):
    def minibuffer(self, viewer):
        self.win=PypeReplaceBar(viewer.win,self)
        self.control=self

    def GetPageCount(self):
        # Always force the check in ReentrantReplace that sets
        # the focus back to the page that is getting updated.
        return 1
    
    def GetCurrentPage(self):
        # Force the condition to be true in ReentrantReplace to set
        # the focus back to the text widget.
        return self
    

class FindText(MinibufferAction):
    name = "Find..."
    tooltip = "Search for a string in the text."
    keyboard = 'C-S'
    minibuffer = FindMinibuffer

class ReplaceText(MinibufferAction):
    name = "Replace..."
    tooltip = "Replace a string in the text."
    keyboard = 'F6'
    minibuffer = ReplaceMinibuffer

