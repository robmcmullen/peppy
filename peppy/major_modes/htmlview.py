# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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
from peppy.actions import *
from peppy.major import *
from peppy.stcinterface import *
from peppy.lib.clipboard import *

__all__ = ['HTMLViewPlugin']


class HTMLViewMode(MajorMode, STCInterface, wx.html.HtmlWindow):
    """Major mode for viewing HTML markup.

    Editing the markup should be done in an editing mode.
    """
    keyword='HTMLView'
    icon='icons/world.png'
    mimetype = "text/html"

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()
            
        self.update()
    
    def isTemporaryMode(self):
        if self.buffer.url.scheme == 'about':
            return True
        return False

    def OnLinkClicked(self, linkinfo):
        assert self.dprint('OnLinkClicked: %s\n' % linkinfo.GetHref())
        url = linkinfo.GetHref()
        if url.startswith("htmlhelp:"):
            wx.GetApp().showHelp(url[9:])
        else:
            wx.CallAfter(self.frame.open, url)

    def OnCellMouseHover(self, cell, x, y):
        assert self.dprint('OnCellMouseHover: %s\n' % cell)
        linkinfo = cell.GetLink()
        if linkinfo is not None:
            self.setStatusText(linkinfo.GetHref())
        else:
            self.setStatusText("")

    def update(self):
        self.SetPage(self.buffer.stc.GetText())

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
    
    def GetReadOnly(self):
        return True

    def CanCopy(self):
        return True

    def Copy(self):
        txt = self.SelectionToText()
        SetClipboardText(txt)
        dprint(txt)
    
    def isPrintingSupported(self):
        return True
    
    def getHtmlForPrinting(self):
        return self.buffer.stc.GetText()


class HTMLViewPlugin(IPeppyPlugin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    def getMajorModes(self):
        yield HTMLViewMode
    
