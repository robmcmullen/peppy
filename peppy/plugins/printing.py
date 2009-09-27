# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Printer support

This plugin provides the Page Setup, Print Preview, and Print actions
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *


class PageSetup(SelectAction):
    """Set up printing preferences"""
    name = "Page Setup..."
    default_menu = ("File", -995)
    
    print_data = wx.PrintData()
    top_left_margin = wx.Point(15,15)
    bottom_right_margin = wx.Point(15,15)

    def action(self, index=-1, multiplier=1):
        cls = self.__class__
        data = wx.PageSetupDialogData(cls.print_data)
        data.SetPrintData(cls.print_data)
    
        data.SetDefaultMinMargins(True)
        data.SetMarginTopLeft(cls.top_left_margin)
        data.SetMarginBottomRight(cls.bottom_right_margin)

        print_dlg = wx.PageSetupDialog(self.mode.frame, data)
        if print_dlg.ShowModal() == wx.ID_OK:
            cls.print_data = wx.PrintData(data.GetPrintData())
            cls.print_data.SetPaperId(data.GetPaperId())
            cls.top_left_margin = data.GetMarginTopLeft()
            cls.bottom_right_margin = data.GetMarginBottomRight()
        print_dlg.Destroy()


class PrintingSupportedMixin(object):
    def isEnabled(self):
        return self.mode.isPrintingSupported()


class PrintPreview(PrintingSupportedMixin, SelectAction):
    """View a preview representation of the printed output"""
    name = "Print Preview"
    default_menu = ("File", 996)
    
    def action(self, index=-1, multiplier=1):
        printout = self.mode.getPrintout()
        printout2 = self.mode.getPrintout()
        preview = wx.PrintPreview(printout, printout2, PageSetup.print_data)
        preview.SetZoom(150)
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
        pdd = wx.PrintDialogData(PageSetup.print_data)
        printer = wx.Printer(pdd)
        printout = self.mode.getPrintout()
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
