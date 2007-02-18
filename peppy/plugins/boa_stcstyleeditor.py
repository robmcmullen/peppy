# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""STCStyleEditor plugin.

This plugin provides access to a dialog used to configure the text
styles of the STC.
"""
import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.boa.STCStyleEditor import *


class STCStyles(SelectAction):
    name="Text Styles..."
    tooltip = "Open the STC Style Editor to edit the current mode's text display."
    icon = "icons/style_edit.png"

    def action(self, pos=-1):
        mode=self.frame.getActiveMajorMode()
        if mode:
            config=os.path.normpath(os.path.join(os.path.dirname(__file__),"../config/stc-styles.rc.cfg"))
            dprint(config)
            name = mode.keyword
            lang = mode.keyword.lower()
            dlg = STCStyleEditDlg(self.frame, name, lang, config)
            try:
                dlg.ShowModal()
            finally:
                dlg.Destroy()


class STCStylesMenuProvider(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Edit",MenuItem(STCStyles).after("lastsep"))
