# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Printer support

This plugin provides the Page Setup, Print Preview, and Print actions

Some of this code was modified from Editra's ed_print.py.
"""

import os

import wx

from peppy.lib.userparams import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *


class PageSetup(SelectAction, ClassPrefs):
    """Set up printing preferences"""
    name = "Page Setup..."
    default_menu = ("File", -995)
    
    print_data = None
    
    default_classprefs = (
        IntParam('top_margin', 15, 'Top margin in mm'),
        IntParam('left_margin', 15, 'Left margin in mm'),
        IntParam('bottom_margin', 15, 'Bottom margin in mm'),
        IntParam('right_margin', 15, 'Left margin in mm'),
        IntParam('paper_id', wx.PAPER_LETTER, 'Identifier for default paper size')
        )

    @classmethod
    def getPrintData(cls):
        if cls.print_data is None:
            p = wx.PrintData()
            p.SetPaperId(cls.classprefs.paper_id)
            cls.print_data = p
        return cls.print_data
    
    @classmethod
    def getPageSetupData(cls):
        print_data = cls.getPrintData()
        data = wx.PageSetupDialogData(print_data)
        data.SetMarginTopLeft(wx.Point(cls.classprefs.top_margin, cls.classprefs.left_margin))
        data.SetMarginBottomRight(wx.Point(cls.classprefs.bottom_margin, cls.classprefs.right_margin))
        return data

    def action(self, index=-1, multiplier=1):
        print_dlg = wx.PageSetupDialog(self.mode.frame, self.getPageSetupData())
        if print_dlg.ShowModal() == wx.ID_OK:
            data = print_dlg.GetPageSetupData()
            self.__class__.print_data = wx.PrintData(data.GetPrintData())
            self.classprefs.paper_id = data.GetPaperId()
            tl = data.GetMarginTopLeft()
            self.classprefs.top_margin = tl.x
            self.classprefs.left_margin = tl.y
            br = data.GetMarginBottomRight()
            self.classprefs.bottom_margin = br.x
            self.classprefs.right_margin = br.y
        print_dlg.Destroy()


class PrintingSupportedMixin(object):
    def isEnabled(self):
        return self.mode.isPrintingSupported()


class PrintPreview(PrintingSupportedMixin, SelectAction):
    """View a preview representation of the printed output"""
    name = "Print Preview"
    default_menu = ("File", 996)
    
    def action(self, index=-1, multiplier=1):
        data = PageSetup.getPageSetupData()
        printout = self.mode.getPrintout(data)
        printout2 = self.mode.getPrintout(data)
        preview = wx.PrintPreview(printout, printout2, PageSetup.getPrintData())
        preview.SetZoom(100)
        if preview.IsOk():
            pre_frame = wx.PreviewFrame(preview, self.mode.frame,
                                             _("Print Preview"))
            dsize = wx.GetDisplaySize()
            pre_frame.SetInitialSize((self.mode.frame.GetSize()[0],
                                      self.mode.frame.GetSize()[1]))
            pre_frame.Initialize()
            pre_frame.Show()
        else:
            wx.MessageBox(_("Failed to create print preview"),
                          _("Print Error"),
                          style=wx.ICON_ERROR|wx.OK)


class Print(PrintingSupportedMixin, SelectAction):
    """Print the contents of the current major mode"""
    name = "Print..."
    icon = "icons/printer.png"
    default_toolbar = False
    default_menu = ("File", 997)
    
    def action(self, index=-1, multiplier=1):
        pdd = wx.PrintDialogData(PageSetup.getPrintData())
        printer = wx.Printer(pdd)
        data = PageSetup.getPageSetupData()
        printout = self.mode.getPrintout(data)
        result = printer.Print(self.mode, printout)
        if result:
            data = printer.GetPrintDialogData()
            PageSetup.print_data = wx.PrintData(data.GetPrintData())
        elif printer.GetLastError() == wx.PRINTER_ERROR:
            wx.MessageBox(_("There was an error when printing.\n"
                            "Check that your printer is properly connected."),
                          _("Printer Error"),
                          style=wx.ICON_ERROR|wx.OK)
        printout.Destroy()


class PrintPlugin(IPeppyPlugin):
    """Plugin containing all the actions related to printing.
    """
    def getActions(self):
        return [
            PageSetup, PrintPreview, Print
            ]
