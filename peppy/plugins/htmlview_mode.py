# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Major mode for viewing HTML text.

This mode uses the wxPython HTML viewer to render HTML marked-up text.
The markup should be edited in another mode; this is for viewing only.
"""

import os
from cStringIO import StringIO

import wx
import wx.html
from wx.lib.evtmgr import eventManager
import wx.lib.newevent

from peppy import *
from peppy.debug import *
from peppy.menu import *
from peppy.major import *

__all__ = ['HTMLViewPlugin']


class HTMLWindow(wx.html.HtmlWindow, debugmixin):
    def __init__(self, parent, mode):
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.mode = mode
        self.stc = mode.buffer.stc
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, linkinfo):
        self.dprint('OnLinkClicked: %s\n' % linkinfo.GetHref())
        #self.mode.frame.SetStatusText(linkinfo.GetHref())

    def OnCellMouseHover(self, cell, x, y):
        self.dprint('OnCellMouseHover: %s\n' % cell)
        linkinfo = cell.GetLink()
        if linkinfo is not None:
            self.mode.frame.SetStatusText(linkinfo.GetHref())
        else:
            self.mode.frame.SetStatusText("")

    def update(self):
        self.SetPage(self.stc.GetText())

class HTMLViewMode(MajorMode):
    """Major mode for viewing HTML markup.

    Editing the markup should be done in an editing mode.
    """
    
    keyword='HTMLView'
    icon='icons/world.png'
    regex="\.(htm|html|shtml)"

    debuglevel=0

    def createEditWindow(self,parent):
        """
        Create the bitmap viewer that is the main window of this major
        mode.

        @param parent: parent window in which to create this window 
        """
        self.dprint()

        win=HTMLWindow(parent, self)

        eventManager.Bind(self.underlyingSTCChanged,stc.EVT_STC_MODIFIED,self.buffer.stc)

        # Thread stuff for the underlying change callback
        self.waiting=None

        return win

    def createWindowPostHook(self):
        """
        Initialize the bitmap viewer with the image contained in the
        buffer.
        """
        self.editwin.update()

    def deleteWindowPostHook(self):
        """
        Clean up the event manager hook that we needed to find out
        when the buffer had been changed by some other view of the
        buffer.
        """
        self.dprint("unregistering %s" % self.underlyingSTCChanged)
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
        # self.editwin.update()
        pass



class HTMLViewPlugin(MajorModeMatcherBase,debugmixin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    implements(IMajorModeMatcher)

    def possibleModes(self):
        yield HTMLViewMode
    
