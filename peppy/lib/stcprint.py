#-----------------------------------------------------------------------------
# Name:        stcprint.py
# Purpose:     wx.StyledTextCtrl printing support
#
# Author:      Rob McMullen
#
# Created:     2009
# RCS-ID:      $Id: $
# Copyright:   (c) 2009 Rob McMullen
#              (c) 2007 Cody Precord <staff@editra.org>
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Printing support for the wx.StyledTextCtrl

Concrete implementation of the wx.Printout class to generate a print preview
and paper copies of the contents of a wx.StyledTextCtrl.

The bulk of this code came from U{Editra<http://www.editra.org>}; I've modified
it to remove dependencies on Editra's framework.
"""

import os

import wx
import wx.stc


class STCPrintout(wx.Printout):
    """Specific printing support of the wx.StyledTextCtrl for the wxPython
    framework
    
    
    """
    debuglevel = 0
    
    def __init__(self, stc, print_mode=None, title=None):
        """Initializes the printout object
        @param title: title of document

        """
        wx.Printout.__init__(self)
        self.stc = stc
        if print_mode:
            self.print_mode = print_mode
        else:
            self.print_mode = wx.stc.STC_PRINT_COLOURONWHITEDEFAULTBG
            self.print_mode = wx.stc.STC_PRINT_COLOURONWHITE
        if title is not None:
            self.title = title
        else:
            self.title = ""
        self._start = 0

        self.margin = 0.05 #margins # TODO repect margins from setup dlg
        self.lines_pp = 69
    
    def OnPreparePrinting(self):
        self.calculatePageCount()
    
    def calculatePageCount(self):
        page_offsets = []
        page_line_start = 0
        lines_on_page = 0
        num_lines = self.stc.GetLineCount()
        
        line = 0
        while line < num_lines:
            wrap_count = self.stc.WrapCount(line)
            if wrap_count > 1:
                print("found wrapped line %d: %d" % (line, wrap_count))
            if lines_on_page + wrap_count > self.lines_pp:
                start_pos = self.stc.PositionFromLine(page_line_start)
                end_pos = self.stc.GetLineEndPosition(page_line_start + lines_on_page)
                page_offsets.append((start_pos, end_pos))
                page_line_start = line
                lines_on_page = 0
            lines_on_page += wrap_count
            line += 1
        
        if lines_on_page > 0:
            start_pos = self.stc.PositionFromLine(page_line_start)
            end_pos = self.stc.GetLineEndPosition(page_line_start + lines_on_page)
            page_offsets.append((start_pos, end_pos))
        
        self.page_count = len(page_offsets)
        self.page_offsets = page_offsets

    def getPositionsOfPage(self, page):
        page -= 1
        start_pos, end_pos = self.page_offsets[page]
        return start_pos, end_pos

    def GetPageInfo(self):
        """Get the page range information
        @return: tuple

        """
        return (1, self.page_count, 1, self.page_count)

    def HasPage(self, page):
        """Is a page within range
        @param page: page number
        @return: wheter page is in range of document or not

        """
        return page <= self.page_count

    def OnPrintPage(self, page):
        """Scales and Renders the page to a DC and prints it
        @param page: page number to print

        """
        line_height = self.stc.TextHeight(0)

        # Calculate sizes
        dc = self.GetDC()
        dw, dh = dc.GetSizeTuple()

        margin_w = self.margin * dw
        margin_h = self.margin * dh
#         text_area_w = dw - margin_w * 2
        text_area_h = dh - margin_h * 2

        scale = float(text_area_h) / (line_height * self.lines_pp)
        dc.SetUserScale(scale, scale)

        # Render the title and page numbers
        font = self.stc.GetFont()
        dc.SetFont(font)

        if self.title:
            title_w, title_h = dc.GetTextExtent(self.title)
            dc.DrawText(self.title, int(dw/scale/2 - title_w/2),
                        int(margin_h/scale - title_h * 3))

        # Page Number
        page_lbl = _("Page: %d") % page
        pg_lbl_w, pg_lbl_h = dc.GetTextExtent(page_lbl)
        dc.DrawText(page_lbl, int(dw/scale/2 - pg_lbl_w/2),
                    int((text_area_h + margin_h) / scale + pg_lbl_h * 2))

        # Render the STC window into a DC for printing
        start_pos, end_pos = self.getPositionsOfPage(page)
        max_w = (dw / scale) - margin_w

        self.stc.SetPrintColourMode(self.print_mode)
        edge_mode = self.stc.GetEdgeMode()
        self.stc.SetEdgeMode(wx.stc.STC_EDGE_NONE)
        end_point = self.stc.FormatRange(True, start_pos, end_pos, dc, dc,
                                        wx.Rect(int(margin_w/scale),
                                                int(margin_h/scale),
                                                max_w,
                                                int(text_area_h/scale)+1),
                                        wx.Rect(0, (page - 1) * \
                                                self.lines_pp * \
                                                line_height, max_w,
                                                line_height * self.lines_pp))
        self.stc.SetEdgeMode(edge_mode)
        self._start = end_point

        return True


if __name__ == "__main__":
    import sys
    import __builtin__
    __builtin__._ = unicode
    
    # Set up sample print data
    top_left_margin = wx.Point(15,15)
    bottom_right_margin = wx.Point(15,15)
    print_data = wx.PrintData()

    class TestSTC(wx.stc.StyledTextCtrl):
        def __init__(self, *args, **kwargs):
            wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
            self.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(0, 32)

    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

            self.stc = TestSTC(self, -1)

            self.CreateStatusBar()
            menubar = wx.MenuBar()
            self.SetMenuBar(menubar)  # Adding the MenuBar to the Frame content.
            menu = wx.Menu()
            menubar.Append(menu, "File")
            self.menuAdd(menu, "Open", "Open File", self.OnOpenFile)
            menu.AppendSeparator()
            self.menuAdd(menu, "Print Preview", "Display print preview", self.OnPrintPreview)
            self.menuAdd(menu, "Print", "Print to printer or file", self.OnPrint)
            menu.AppendSeparator()
            self.menuAdd(menu, "Quit", "Exit the pragram", self.OnQuit)


        def loadFile(self, filename):
            fh = open(filename)
            self.stc.SetText(fh.read())
        
        def loadSample(self, paragraphs=10):
            lorem_ipsum = u"""\
Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Vivamus mattis
commodo sem.  Phasellus scelerisque tellus id lorem.  Nulla facilisi.
Suspendisse potenti.  Fusce velit odio, scelerisque vel, consequat nec,
dapibus sit amet, tortor.

Vivamus eu turpis.  Nam eget dolor.  Integer at elit.  Praesent mauris.  Nullam non nulla at nulla tincidunt malesuada. Phasellus id ante.  Sed mauris.  Integer volutpat nisi non diam.

Etiam elementum.  Pellentesque interdum justo eu risus.  Cum sociis natoque
penatibus et magnis dis parturient montes, nascetur ridiculus mus.  Nunc
semper.

In semper enim ut odio.  Nulla varius leo commodo elit.  Quisque condimentum, nisl eget elementum laoreet, mauris turpis elementum felis, ut accumsan nisl velit et mi.

And some Russian: \u041f\u0438\u0442\u043e\u043d - \u043b\u0443\u0447\u0448\u0438\u0439 \u044f\u0437\u044b\u043a \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f!

"""
            self.stc.ClearAll()
            for i in range(paragraphs):
                self.stc.AppendText(lorem_ipsum)

        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, name, desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)
            menu.SetHelpString(id, desc)
        
        def OnOpenFile(self, evt):
            dlg = wx.FileDialog(self, "Choose a text file",
                               defaultDir = "",
                               defaultFile = "",
                               wildcard = "*")
            if dlg.ShowModal() == wx.ID_OK:
                print("Opening %s" % dlg.GetPath())
                self.loadFile(dlg.GetPath())
            dlg.Destroy()
        
        def OnQuit(self, evt):
            self.Close(True)
        
        def OnPrintPreview(self, evt):
            printout = STCPrintout(self.stc)
            printout2 = STCPrintout(self.stc)
            preview = wx.PrintPreview(printout, printout2, print_data)
            preview.SetZoom(150)
            if preview.IsOk():
                pre_frame = wx.PreviewFrame(preview, self,
                                                 _("Print Preview"))
                dsize = wx.GetDisplaySize()
                pre_frame.SetInitialSize((self.GetSize()[0],
                                          dsize.GetHeight() - 100))
                pre_frame.Initialize()
                pre_frame.Show()
            else:
                wx.MessageBox(_("Failed to create print preview"),
                              _("Print Error"),
                              style=wx.ICON_ERROR|wx.OK)
        
        def OnPrint(self, evt):
            pdd = wx.PrintDialogData(print_data)
            printer = wx.Printer(pdd)
            printout = STCPrintout(self.stc)
            result = printer.Print(self, printout)
            if result:
                data = printer.GetPrintDialogData()
                PageSetup.print_data = wx.PrintData(data.GetPrintData())
            elif printer.GetLastError() == wx.PRINTER_ERROR:
                wx.MessageBox(_("There was an error when printing.\n"
                                "Check that your printer is properly connected."),
                              _("Printer Error"),
                              style=wx.ICON_ERROR|wx.OK)
            printout.Destroy()

    app = wx.App(False)
    frame = Frame(None, size=(800, -1))
    need_sample = True
    if len(sys.argv) > 1:
        if not sys.argv[-1].startswith("-"):
            frame.loadFile(sys.argv[-1])
            need_sample = False
    if need_sample:
        frame.loadSample()
    if '-d' in sys.argv:
        STCPrintout.debuglevel = 1
    frame.Show()
    app.MainLoop()
