# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Major mode for viewing HTML text.

This mode uses the wxPython HTML viewer to render HTML marked-up text.
The markup should be edited in another mode; this is for viewing only.
"""

import os
from cStringIO import StringIO

import wx
import wx.stc
import wx.html
from wx.lib.evtmgr import eventManager
import wx.lib.newevent

from peppy.yapsy.plugins import *
from peppy.debug import *
from peppy.menu import *
from peppy.major import *
from peppy.stcinterface import *

__all__ = ['HTMLViewPlugin']


class HTMLSTCWrapper(STCProxy):
    def __init__(self, stc, html):
        self.stc = stc
        self.html = html
        
    def CanEdit(self):
        return False

    def CanCopy(self):
        return True

    def Copy(self):
        txt = self.html.SelectionToText()
        SetClipboardText(txt)
        dprint(txt)

    def CanCut(self):
        return False

    def CanPaste(self):
        return False

    def CanUndo(self):
        return False

    def CanRedo(self):
        return False

    

class HTMLViewMode(MajorMode, wx.html.HtmlWindow):
    """Major mode for viewing HTML markup.

    Editing the markup should be done in an editing mode.
    """
    debuglevel = 0
    
    keyword='HTMLView'
    icon='icons/world.png'
    regex=""

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()
            
        self.stc = HTMLSTCWrapper(self.buffer.stc, self)
        
        self.update()

    def OnLinkClicked(self, linkinfo):
        assert self.dprint('OnLinkClicked: %s\n' % linkinfo.GetHref())
        self.frame.open(linkinfo.GetHref())

    def OnCellMouseHover(self, cell, x, y):
        assert self.dprint('OnCellMouseHover: %s\n' % cell)
        linkinfo = cell.GetLink()
        if linkinfo is not None:
            self.frame.SetStatusText(linkinfo.GetHref())
        else:
            self.frame.SetStatusText("")

    def update(self):
        self.SetPage(self.stc.GetText())

    def createListenersPostHook(self):
        eventManager.Bind(self.underlyingSTCChanged, wx.stc.EVT_STC_MODIFIED,
                          self.buffer.stc)
        # Thread stuff for the underlying change callback
        self.waiting=None

    def removeListenersPostHook(self):
        """
        Clean up the event manager hook that we needed to find out
        when the buffer had been changed by some other view of the
        buffer.
        """
        assert self.dprint("unregistering %s" % self.underlyingSTCChanged)
        eventManager.DeregisterListener(self.underlyingSTCChanged)        
        
    def underlyingSTCChanged(self,evt):
        """
        Update the image when it has been changed by another view of
        the data.

        @param evt: EVT_STC_MODIFIED event 
        """
        # Since we can never edit the image directly, we don't need to
        # short-circuit this callback like we do with hexedit mode.
        # Every change that we get here means that the image has
        # changed.

        # FIXME: don't actually perform the complete update right now
        # because it's probably too slow.  Queue it for later and put
        # it in a thread.
        # self.update()
        pass



class HTMLViewPlugin(IPeppyPlugin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    def getMajorModes(self):
        yield HTMLViewMode
    
