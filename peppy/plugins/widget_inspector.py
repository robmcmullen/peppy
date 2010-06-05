# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Widget inspector plugin.

This plugin provides a menu item to pop up the widget inspector, useful
for debugging layout of wxpython widgets.
"""
import os

from peppy.yapsy.plugins import *
from peppy.actions import *

class WidgetInspector(SelectAction):
    """Open the wxPython widget inspector."""
    name = "Widget Inspector..."
    default_menu = ("&Help", -700)

    def isEnabled(self):
        return True

    def action(self, index=-1, multiplier=1):
        from wx.lib.inspection import InspectionTool
        if not InspectionTool().initialized:
            InspectionTool().Init()
        InspectionTool().Show(self.frame, True)

class WidgetInspectorPlugin(IPeppyPlugin):
    def getActions(self):
        return [WidgetInspector]
