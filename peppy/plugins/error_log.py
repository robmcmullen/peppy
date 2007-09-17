# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Sidebar for error messages.

Small sidebar to show error messages, since showing multiple errors
isn't possible in the status bar.
"""

import os

import wx
from wx.lib.pubsub import Publisher

from peppy.stcinterface import PeppySTC
from peppy.trac.core import *
from peppy.sidebar import *
from peppy.minor import *

class ErrorLogMixin(PeppySTC, ClassPrefs, debugmixin):
    debuglevel = 0
    
    default_classprefs = (
        BoolParam('show', False),
        BoolParam('always_scroll', False),
        )

    def displayMessage(self, text):
        if self.classprefs.always_scroll:
            scroll = True
        else:
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
            #print("top line: %d, visible: %d, total=%d, scroll=%s" % (line, visible, total, scroll))
            
        self.AddText(text)
        if scroll:
            self.ScrollToLine(self.GetLineCount())

class ErrorLogSidebar(Sidebar, ErrorLogMixin):
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

    message = 'peppy.log.error'
    ready_message = 'peppy.ready.error'

    default_classprefs = (
        IntParam('best_width', 500),
        IntParam('best_height', 100),
        IntParam('min_width', 100),
        IntParam('min_height', 20),
        BoolParam('show', False),
        BoolParam('unhide_on_message', True),
        BoolParam('always_scroll', False),
        )
    
    def __init__(self, parent):
        PeppySTC.__init__(self, parent)
        self.frame = parent

        Publisher().subscribe(self.showError, self.message)
        Publisher().sendMessage(self.ready_message)
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def showError(self, message=None):
        paneinfo = self.frame._mgr.GetPane(self)
        if self.classprefs.unhide_on_message:
            if not paneinfo.IsShown():
                paneinfo.Show(True)
                self.frame._mgr.Update()
        self.displayMessage(message.data)

class DebugLogSidebar(ErrorLogSidebar):
    keyword = "debug_log"
    caption = _("Debug Log")

    message = 'peppy.log.debug'
    ready_message = 'peppy.ready.debug'
    
    default_classprefs = (
        BoolParam('unhide_on_message', False),
        )

class OutputLogMinorMode(MinorMode, ErrorLogMixin):
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
    
    keyword = "OutputLog"
    caption = _("Output Log")

    default_classprefs = (
        IntParam('best_width', 500),
        IntParam('best_height', 200),
        IntParam('min_width', 100),
        IntParam('min_height', 200),
        BoolParam('show', False),
        BoolParam('always_scroll', False),
        )
    
    def __init__(self, major, parent):
        PeppySTC.__init__(self, parent)
        self.major = major
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def showError(self, message=None):
        paneinfo = self.major._mgr.GetPane(self)
        if not paneinfo.IsShown():
            paneinfo.Show(True)
            self.major._mgr.Update()
        self.displayMessage(message.data)

class ErrorLogProvider(Component):
    """Plugin to advertize the presense of the ErrorLog sidebar
    """
    implements(ISidebarProvider)
    implements(IMinorModeProvider)

    def getSidebars(self):
        yield ErrorLogSidebar
        yield DebugLogSidebar
        
    def getMinorModes(self):
        yield OutputLogMinorMode
