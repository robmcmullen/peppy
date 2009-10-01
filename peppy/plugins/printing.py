# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Printer support

This plugin provides the Page Setup, Print Preview, and Print actions

Some of this code was modified from Editra's ed_print.py.
"""

import os

import wx
import wx.html

from peppy.lib.userparams import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *


class PageSetup(SelectAction, ClassPrefs):
    """Set up printing preferences"""
    name = "Page Setup..."
    default_menu = ("File", -995)
    
    easy_print = None
    
    default_classprefs = (
        IntParam('top_margin', 15, 'Top margin in mm'),
        IntParam('left_margin', 15, 'Left margin in mm'),
        IntParam('bottom_margin', 15, 'Bottom margin in mm'),
        IntParam('right_margin', 15, 'Left margin in mm'),
        IntParam('paper_id', wx.PAPER_LETTER, 'Identifier for default paper size')
        )

    @classmethod
    def getEasyPrint(cls, parent=None):
        if cls.easy_print is None:
            cls.easy_print = wx.html.HtmlEasyPrinting()
        cls.easy_print.SetParentWindow(parent)
        data = cls.easy_print.GetPageSetupData()
        data.SetMarginTopLeft(wx.Point(cls.classprefs.top_margin, cls.classprefs.left_margin))
        data.SetMarginBottomRight(wx.Point(cls.classprefs.bottom_margin, cls.classprefs.right_margin))
        data.SetPaperId(cls.classprefs.paper_id)
        p = cls.easy_print.GetPrintData()
        p.SetPaperId(cls.classprefs.paper_id)
        return cls.easy_print

    @classmethod
    def getPrintData(cls):
        # Using the print data from the EasyPrint singleton
        easy_print = cls.getEasyPrint()
        return easy_print.GetPrintData()
    
    @classmethod
    def getPageSetupData(cls):
        # Using the page setup data from the EasyPrint singleton
        easy_print = cls.getEasyPrint()
        return easy_print.GetPageSetupData()

    def action(self, index=-1, multiplier=1):
        easy_print = PageSetup.getEasyPrint(self.mode.frame)
        retval = easy_print.PageSetup()
        data = easy_print.GetPageSetupData()
        self.classprefs.paper_id = data.GetPaperId()
        tl = data.GetMarginTopLeft()
        self.classprefs.top_margin = tl.x
        self.classprefs.left_margin = tl.y
        br = data.GetMarginBottomRight()
        self.classprefs.bottom_margin = br.x
        self.classprefs.right_margin = br.y


class PrintingSupportedMixin(object):
    def isEnabled(self):
        return self.mode.isPrintingSupported()


class PrintPreview(PrintingSupportedMixin, SelectAction):
    """View a preview representation of the printed output"""
    name = "Print Preview"
    default_menu = ("File", 996)
    
    def action(self, index=-1, multiplier=1):
        html = self.mode.getHtmlForPrinting()
        if html:
            self.previewHtml(html)
        else:
            self.previewPrintout()
    
    def previewHtml(self, html):
        easy_print = PageSetup.getEasyPrint(self.mode.frame)
        easy_print.PreviewText(html)
    
    def previewPrintout(self):
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
        html = self.mode.getHtmlForPrinting()
        if html:
            self.printHtml(html)
        else:
            self.printPrintout()
    
    def printHtml(self, html):
        easy_print = PageSetup.getEasyPrint(self.mode.frame)
        easy_print.PrintText(html)
    
    def printPrintout(self):
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
