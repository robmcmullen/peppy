# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Widget inspector plugin.

This plugin provides a menu item to pop up the widget inspector, useful
for debugging layout of wxpython widgets.
"""
import os

from peppy.yapsy.plugins import *
from peppy.menu import *

class WidgetInspector(SelectAction):
    name=_("Widget Inspector...")
    tooltip = _("Open the wxPython widget inspector.")
    icon = "icons/style_edit.png"

    def isEnabled(self):
        return True

    def action(self, index=-1):
        from wx.lib.inspection import InspectionTool
        if not InspectionTool().initialized:
            InspectionTool().Init()
        InspectionTool().Show(self.frame, True)

class WidgetInspectorPlugin(IPeppyPlugin):
    def getMenuItems(self):
        yield (None,_("&Help"),MenuItem(WidgetInspector).last())
