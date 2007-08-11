# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Widget inspector plugin.

This plugin provides a menu item to pop up the widget inspector, useful
for debugging layout of wxpython widgets.
"""
import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *

class WidgetInspector(SelectAction):
    name="Widget Inspector..."
    tooltip = "Open the wxPython widget inspector."
    icon = "icons/style_edit.png"

    def isEnabled(self):
        return True

    def action(self, pos=-1):
        from wx.lib.inspection import InspectionTool
        if not InspectionTool().initialized:
            InspectionTool().Init()
        InspectionTool().Show(self.frame, True)

class WidgetInspectorMenuProvider(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"&Help",MenuItem(WidgetInspector).last())
