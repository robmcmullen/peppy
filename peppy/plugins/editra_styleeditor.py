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

AddCopyright("Editra", "http://www.editra.org", "Cody Precord", "2005-2009", "The styling dialog and syntax definitions from")


class PeppyStyleEditor(style_editor.StyleEditor):
    def OpenPreviewFile(self, lang):
        """Overriding the Editra language lookup to scan through major modes
        for the sample text
        """
        from peppy.editra.sample_text import sample_text
        
        self.preview.ClearAll()
        if lang not in sample_text:
            lang = "Python"
        sample = sample_text[lang]
        self.preview.SetText(sample)
        self.preview.FindLexer(lang)
        self.preview.EmptyUndoBuffer()



class EditraStyles(SelectAction):
    name = "Text Styles..."
    tooltip = "Open the STC Style Editor to edit the current mode's text display."
    default_menu = ("Edit", -1000)
    export_count = 0
    osx_minimal_menu = True
    
    def setSampleText(self, dlg):
        dlg.OpenPreviewFile(self.mode.keyword)
        lexer_lst = dlg.FindWindowById(style_editor.ed_glob.ID_LEXER)
        lexer_lst.SetStringSelection(self.mode.keyword)
    
    def action(self, index=-1, multiplier=1):
        stylesheet = wx.GetApp().fonts.getStyleFile()
        dlg = PeppyStyleEditor(self.frame, -1)
        self.setSampleText(dlg)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            # Find style name from controls within the dialog
            ctrl = dlg.FindWindowById(style_editor.ed_glob.ID_PREF_SYNTHEME)
            tag = ctrl.GetStringSelection()
            ctrl = dlg.FindWindowById(wx.ID_NEW)
            if ctrl.GetValue():
                tag = "untitled"
            dlg2 = wx.TextEntryDialog(
                self.frame, caption="Save Style Sheet", message="Enter name for style sheet.\n\nThis style sheet must be saved in your personal\nconfiguration directory before it can be used.\n\nIf you cancel, the style sheet changes will be lost.", defaultValue=tag,
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
