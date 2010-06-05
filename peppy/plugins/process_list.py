# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Sidebar for error messages.

Small sidebar to show error messages, since showing multiple errors
isn't possible in the status bar.
"""

import os

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.lib.processmanager import *
from peppy.sidebar import *

class ProcessSidebar(ProcessList, Sidebar, debugmixin):
    """A sidebar showing the running processes

    This is a global plugin that displays any subprocesses currently
    active.  Any processes started using the ProcessManager will be
    displayed here.
    """
    keyword = "processes"
    caption = _("Running Jobs")

    default_classprefs = (
        IntParam('best_width', 500),
        IntParam('best_height', 50),
        IntParam('min_width', 100),
        IntParam('min_height', 20),
        BoolParam('show', False),
        )
    
    def __init__(self, parent):
        ProcessList.__init__(self, parent, pos=(9000,9000))
        Sidebar.__init__(self, parent)
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()


class ProcessSidebarPlugin(IPeppyPlugin):
    """Plugin to advertize the presense of the ErrorLog sidebar
    """
    def getSidebars(self):
        yield ProcessSidebar
