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
from peppy.editra.stcmixin import EditraSTCMixin
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
        dlg.OpenPreviewFile(self.mode.editra_lang)
        lexer_lst = dlg.FindWindowById(style_editor.ed_glob.ID_LEXER)
        lexer_lst.SetStringSelection(self.mode.editra_lang)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            # Find style name from controls within the dialog
            ctrl = dlg.FindWindowById(style_editor.ed_glob.ID_PREF_SYNTHEME)
            tag = ctrl.GetStringSelection()
            ctrl = dlg.FindWindowById(wx.ID_NEW)
            if ctrl.GetValue():
                tag = "untitled"
            dlg2 = wx.TextEntryDialog(
                self.frame, message="Save Style Sheet", defaultValue=tag,
                style=wx.OK|wx.CANCEL)
            retval = dlg2.ShowModal()
            tag = dlg2.GetValue()
            if not tag:
                tag = "untitled"
            dlg2.Destroy()
            
            if retval == wx.ID_OK:
                #dprint("Saving style to %s" % tag)
                filename = wx.GetApp().fonts.getStylePath(tag)

                styles = ed_style.MergeStyles(dlg.preview.BlankStyleDictionary(), dlg.styles_new)
                dlg.preview.SetStyles(filename, styles, True)
                EditraSTCMixin.global_style_set = filename
                sheet = dlg.GenerateStyleSheet()
                #dprint(sheet)
                fh = open(filename, 'wb')
                fh.write(sheet)
                wx.GetApp().fonts.classprefs.editra_style_theme = tag
                Publisher().sendMessage('peppy.preferences.changed')
        elif retval == wx.ID_SAVE:
            dprint("Save!")
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



class EditraStylesPlugin(IPeppyPlugin):
    def getActions(self):
        return [EditraStyles]
