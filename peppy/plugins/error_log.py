# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Sidebar for error messages.

Small sidebar to show error messages, since showing multiple errors
isn't possible in the status bar.
"""

import os, re

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.stcinterface import PeppySTC
from peppy.sidebar import *
from peppy.minor import *

class LoggingSTC(PeppySTC, ClassPrefs, debugmixin):
    debuglevel = 0
    
    default_classprefs = (
        BoolParam('show', False),
        BoolParam('always_scroll', False),
        )

    def __init__(self, *args, **kwargs):
        PeppySTC.__init__(self, *args, **kwargs)
        self.IndicatorSetStyle(0, wx.stc.STC_INDIC_SQUIGGLE)
        self.IndicatorSetForeground(0, wx.RED)
        
    def addMessage(self, text):
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
        
        pos = self.GetLength()
        self.SetTargetStart(pos)
        self.SetTargetEnd(pos)
        self.ReplaceTarget(text)
        if scroll:
            self.ScrollToLine(self.GetLineCount())
        self.scanForFilenames()
    
    def scanForFilenames(self):
        if not hasattr(self, 'last_matched_filename'):
            self.last_matched_filename = 0
        
        pos = self.last_matched_filename
        text = self.GetTextRange(pos, self.GetTextLength())
        dprint(text)

        # FIXME: currently hard-coded for Python output
        filere = re.compile("  File \"(.+)\", line ([0-9]+)")
        i = 0
        while i < len(text):
            match = filere.search(text, i)
            if not match:
                break
            
            filename = match.group(1)
            i = match.start(1)
            self.StartStyling(pos + i, wx.stc.STC_INDICS_MASK)
            self.SetStyling(len(filename), wx.stc.STC_INDIC0_MASK)
            self.last_matched_filename = pos + len(filename)
            i = match.end(0)

class ErrorLogSidebar(Sidebar, LoggingSTC):
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
    caption = "Error Log"

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
        LoggingSTC.__init__(self, parent)
        self.frame = parent

        Publisher().subscribe(self.showError, self.message)
        Publisher().sendMessage(self.ready_message)
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def showError(self, message=None):
        if self.frame == wx.GetApp().GetTopWindow():
            paneinfo = self.frame._mgr.GetPane(self)
            if self.classprefs.unhide_on_message:
                if not paneinfo.IsShown():
                    paneinfo.Show(True)
                    self.frame._mgr.Update()
            self.addMessage(message.data)

class DebugLogSidebar(ErrorLogSidebar):
    keyword = "debug_log"
    caption = "Debug Log"

    message = 'peppy.log.debug'
    ready_message = 'peppy.ready.debug'
    
    default_classprefs = (
        BoolParam('unhide_on_message', False),
        )

class InfoLogSidebar(ErrorLogSidebar):
    keyword = "info_log"
    caption = "Information"

    message = 'peppy.log.info'
    ready_message = 'peppy.ready.info'

    default_classprefs = (
        IntParam('best_width', 500),
        IntParam('best_height', 200),
        IntParam('min_width', 100),
        IntParam('min_height', 20),
    )
    
class OutputLogMinorMode(MinorMode, LoggingSTC):
    """An error log using message passing.

    This log is designed to be associated with a major mode that
    implements the JobOutputMixin.  In the stdoutCallback and
    stderrCallback of the JobOutputMixin, you should call showMessage
    to display the output in the log.
    """
    debuglevel = 0
    
    keyword = "OutputLog"
    caption = "Output Log"

    default_classprefs = (
        IntParam('best_width', 500),
        IntParam('best_height', 200),
        IntParam('min_width', 100),
        IntParam('min_height', 200),
        BoolParam('show', False),
        BoolParam('always_scroll', False),
        )

    @classmethod
    def worksWithMajorMode(self, mode):
        """Designed to work with a major mode that inherits the
        JobOutputMixin, so only works when it can find the
        stdoutCallback method in the major mode
        """
        if hasattr(mode, 'stdoutCallback'):
            return True
        return False
    
    def __init__(self, major, parent):
        LoggingSTC.__init__(self, parent)
        self.major = major
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def showMessage(self, text):
        """Display a message and raise the output log if it is hidden."""
        paneinfo = self.major._mgr.GetPane(self)
        if not paneinfo.IsShown():
            paneinfo.Show(True)
            self.major._mgr.Update()
        self.addMessage(text)

    def showPubsubMessage(self, message=None):
        """Same as showMessage, but designed to be used as the target
        of a wx.lib.pubsub.sendMessage call.
        """
        self.showMessage(message.data)

class ErrorLogPlugin(IPeppyPlugin):
    """Plugin to advertize the presense of the ErrorLog sidebar
    """
    
    def getSidebars(self):
        yield ErrorLogSidebar
        yield DebugLogSidebar
        yield InfoLogSidebar
        
    def getMinorModes(self):
        yield OutputLogMinorMode
