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
from peppy.lib.processmanager import *
from peppy.trac.core import *
from peppy.sidebar import *

class ProcessSidebar(Sidebar, ProcessList, debugmixin):
    """A sidebar showing the running processes

    This is a global plugin that displays any subprocesses currently
    active.  Any processes started using the ProcessManager will be
    displayed here.
    """
    debuglevel = 0
    
    keyword = "processes"
    caption = _("Running Jobs")

    default_settings = {
        'best_width': 500,
        'best_height': 50,
        'min_width': 100,
        'min_height': 20,
        'show': False,
        }
    
    def __init__(self, parent):
        ProcessList.__init__(self, parent)
        self.frame = parent
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()


class ProcessSidebarProvider(Component):
    """Plugin to advertize the presense of the ErrorLog sidebar
    """
    implements(ISidebarProvider)

    def getSidebars(self):
        yield ProcessSidebar
