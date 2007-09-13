# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Sidebar for error messages.

Small sidebar to show error messages, since showing multiple errors
isn't possible in the status bar.
"""

import os

import wx
from wx.lib.pubsub import Publisher

from peppy import *
from peppy.stcinterface import PeppySTC
from peppy.trac.core import *
from peppy.sidebar import *

class ErrorLog(Sidebar, PeppySTC, debugmixin):
    """An error log using message passing.

    This is a global plugin that displays any messages it receives
    starting with 'peppy.log'.

    Eventually, it could do different things depending on the subtype
    of the message.  For example, 'peppy.log.error' messages could be
    highlighted in red, or there could be different levels of log
    messages and it could show only those messages above a certain
    level.
    """
    debuglevel = 0
    
    keyword = "error_log"
    caption = _("Error Log")

    default_settings = {
        'best_width': 500,
        'best_height': 50,
        'min_width': 100,
        'min_height': 20,
        'show': False,
        'always_scroll': False,
        }
    
    def __init__(self, parent):
        PeppySTC.__init__(self, parent)
        self.frame = parent

        Publisher().subscribe(self.showError, 'peppy.log')
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def showError(self, message=None):
        paneinfo = self.frame._mgr.GetPane(self)
        if not paneinfo.IsShown():
            paneinfo.Show(True)
            self.frame._mgr.Update()

        scroll = False
        if not self.settings.always_scroll:
            # If we're at the end, scroll down as new lines are added.
            # If we are scrolled back reading something else, don't
            # scroll.
            line = self.GetFirstVisibleLine()
            visible = self.LinesOnScreen()
            total = self.GetLineCount()
            if line >= total - visible:
                scroll = True
            else:
                scroll = False
            #dprint("top line: %d, visible: %d, total=%d, scroll=%s" % (line, visible, total, scroll))
            
        self.AddText(message.data)
        if scroll:
            self.ScrollToLine(self.GetLineCount())


class ErrorLogProvider(Component):
    """Plugin to advertize the presense of the ErrorLog sidebar
    """
    implements(ISidebarProvider)

    def getSidebars(self):
        yield ErrorLog
