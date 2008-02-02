# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""STCStyleEditor plugin.

This plugin provides access to a dialog used to configure the text
styles of the STC.
"""
import os

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.yapsy.plugins import *
from peppy.actions import *

from peppy.editra import *
import peppy.editra.style_editor as style_editor

from peppy.about import AddCopyright

AddCopyright("Editra", "http://www.editra.org", "Cody Precord", "2005-2007", "The styling dialog and syntax definitions for over 30 languages from")


class EditraStyles(SelectAction):
    name = "Text Styles..."
    tooltip = "Open the STC Style Editor to edit the current mode's text display."
    default_menu = ("Edit", -1000)
    export_count = 0
    
    def action(self, index=-1, multiplier=1):
        stylesheet = wx.GetApp().fonts.getStyleFile()
        dlg = style_editor.StyleEditor(self.frame, -1)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            sheet = dlg.GenerateStyleSheet()
            dprint(sheet)
            fh = wx.GetApp().config.open(stylesheet, 'wb')
            fh.write(sheet)
        elif retval == wx.ID_SAVE:
            sheet = dlg.GenerateStyleSheet()
            dprint(sheet)
            self.export_count += 1
            url = "mem:///style-sheet-%d.ess" % self.export_count
            fh = vfs.make_file(url)
            fh.write(sheet)
            fh.close()
            fh = vfs.open(url)
            dprint(fh.read())
            self.frame.open(url)
        dlg.Destroy()
        Publisher().sendMessage('peppy.preferences.changed')



class EditraStylesPlugin(IPeppyPlugin):
    def getActions(self):
        return [EditraStyles]
