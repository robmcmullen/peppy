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
it to remove dependencies on Editra's framework.  Other pointers came from
the wxPython mailing list, and lots was just pure ol' trial and error because I
couldn't find many docs on the FormatRange method of the STC.
"""

import os

import wx
import wx.stc


class STCPrintout(wx.Printout):
    """Specific printing support of the wx.StyledTextCtrl for the wxPython
    framework
    
    
    """
    debuglevel = 0
    
    def __init__(self, stc, top_left_margin=None, bottom_right_margin=None, print_mode=None, title=None, border=False):
        """Initializes the printout object
        @param title: title of document

        """
        wx.Printout.__init__(self)
        self.stc = stc
        if print_mode:
            self.print_mode = print_mode
        else:
            self.print_mode = wx.stc.STC_PRINT_COLOURONWHITEDEFAULTBG
        if title is not None:
            self.title = title
        else:
            self.title = ""
        if top_left_margin is None:
            self.top_left_margin = wx.Point(15,15)
        else:
            self.top_left_margin = top_left_margin
        if bottom_right_margin is None:
            self.bottom_right_margin = wx.Point(15,15)
        else:
            self.bottom_right_margin = bottom_right_margin
        
        self.border_around_text = border
    
    def OnPreparePrinting(self):
        dc = self.GetDC()
        self.calculateScale(dc)
        self.calculatePageCount()
    
    def calculateScale(self, dc):
        page_ppi_x, page_ppi_y = self.GetPPIPrinter()
        screen_ppi_x,  screen_ppi_y = self.GetPPIScreen()
        screen_to_page = 1.0 * page_ppi_y / screen_ppi_y

        pw, ph = self.GetPageSizePixels()
        dw, dh = dc.GetSize()
        self.scale = screen_to_page * dh / ph
        dc.SetUserScale(self.scale, self.scale)
        self.mm_to_page = 1.0 * page_ppi_y / screen_to_page / 25.4
        if self.debuglevel > 0:
            print "scale: %f" % self.scale
            print "device pixels: %dx%d" % (dw, dh)
            print "page pixels: %dx%d" % (pw, ph)
            print "mm_to_page: %f" % self.mm_to_page

        self.x1 = self.top_left_margin[0] * self.mm_to_page
        self.y1 = self.top_left_margin[1] * self.mm_to_page
        self.x2 = dc.DeviceToLogicalXRel(dw) - \
                  self.bottom_right_margin[0] * self.mm_to_page
        self.y2 = dc.DeviceToLogicalYRel(dh) - \
                  self.bottom_right_margin[1] * self.mm_to_page
        self.page_height = self.y2 - self.y1 - 2 * self.mm_to_page

        dc.SetFont(self.stc.GetFont())
        self.line_height = dc.GetCharHeight()
        self.lines_pp = int(self.page_height / self.line_height)
        
        if self.debuglevel > 0:
            print "page size: %d,%d -> %d,%d" % (int(self.x1), int(self.y1), int(self.x2), int(self.y2))
            print "line height: ", self.line_height
            print "page height: ", int(self.page_height)
            print "lines per page: ", self.lines_pp
    
    def calculatePageCount(self, attempt_wrap=False):
        page_offsets = []
        page_line_start = 0
        lines_on_page = 0
        num_lines = self.stc.GetLineCount()
        
        line = 0
        while line < num_lines:
            if attempt_wrap:
                wrap_count = self.stc.WrapCount(line)
                if wrap_count > 1 and self.debuglevel > 0:
                    print("found wrapped line %d: %d" % (line, wrap_count))
            else:
                wrap_count = 1
            
            # If the next line pushes the count over the edge, mark a page and
            # start the next page
            if lines_on_page + wrap_count > self.lines_pp:
                start_pos = self.stc.PositionFromLine(page_line_start)
                end_pos = self.stc.GetLineEndPosition(page_line_start + lines_on_page - 1)
                if self.debuglevel > 0:
                    print("Page: line %d - %d" % (page_line_start, page_line_start + lines_on_page))
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
        if self.debuglevel > 0:
            print("page offsets: %s" % self.page_offsets)

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
        dc = self.GetDC()
        self.calculateScale(dc)

        # Set font for title/page number rendering
        dc.SetFont( wx.FFont( 10, wx.SWISS ) )
        dc.SetTextForeground ("black")
        if self.title:
            title_w, title_h = dc.GetTextExtent(self.title)
            dc.DrawText(self.title, (self.x2 + self.x1)/2 - (title_w/2),
                        self.y1 - title_h)

        # Page Number
        page_lbl = _("Page: %d") % page
        pg_lbl_w, pg_lbl_h = dc.GetTextExtent(page_lbl)
        dc.DrawText(page_lbl, (self.x2 + self.x1)/2 - (pg_lbl_w/2),
                    self.y2)

        # Set the font back to the regular STC font
        dc.SetFont(self.stc.GetFont())
        
        # Render the STC window into a DC for printing.  Force the right margin
        # of the rendered window to be huge so the STC won't attempt word
        # wrapping.
        start_pos, end_pos = self.getPositionsOfPage(page)
        render_rect = wx.Rect(self.x1, self.y1, 32000, self.y2)
        page_rect = wx.Rect(self.x1, self.y1, self.x2, self.y2)

        self.stc.SetPrintColourMode(self.print_mode)
        edge_mode = self.stc.GetEdgeMode()
        self.stc.SetEdgeMode(wx.stc.STC_EDGE_NONE)
        end_point = self.stc.FormatRange(True, start_pos, end_pos, dc, dc,
                                        render_rect, page_rect)
        
        if self.border_around_text:
            dc.SetPen(wx.BLACK_PEN)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(self.x1, self.y1, self.x2 - self.x1 + 1, self.y2 - self.y1 + 1)
        self.stc.SetEdgeMode(edge_mode)

        return True


if __name__ == "__main__":
    import sys
    import __builtin__
    __builtin__._ = unicode
    
    # Set up sample print data
    top_left_margin = wx.Point(15,15)
    bottom_right_margin = wx.Point(15,15)
    
    def wrap(text, width=80):
        """A word-wrap function that preserves existing line breaks
        and most spaces in the text.
        
        Expects that existing line breaks are posix newlines (\n).
        
        http://code.activestate.com/recipes/148061/
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
                      (line,
                       ' \n'[(len(line)-line.rfind('\n')-1
                             + len(word.split('\n',1)[0]
                                  ) >= width)],
                       word),
                      text.split(' ')
                     )

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
            
            self.print_data = wx.PrintData()


        def loadFile(self, filename, word_wrap=False):
            fh = open(filename)
            text = fh.read()
            if word_wrap:
                text = wrap(text)
            self.stc.SetText(fh.read())
        
        def loadSample(self, paragraphs=10, word_wrap=False):
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
            if word_wrap:
                lorem_ipsum = wrap(lorem_ipsum)
            self.stc.ClearAll()
            for i in range(paragraphs):
                self.stc.AppendText(lorem_ipsum)
            wx.CallAfter(self.OnPrintPreview, None)

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
        
        def getPrintData(self):
            return self.print_data
        
        def OnPrintPreview(self, evt):
            wx.CallAfter(self.showPrintPreview)
        
        def showPrintPreview(self):
            printout = STCPrintout(self.stc, title="Testing!!!")
            printout2 = STCPrintout(self.stc, title="Testing!!!")
            preview = wx.PrintPreview(printout, printout2, self.getPrintData())
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
            wx.CallAfter(self.showPrint)
        
        def showPrint(self):
            pdd = wx.PrintDialogData(self.getPrintData())
            printer = wx.Printer(pdd)
            printout = STCPrintout(self.stc)
            result = printer.Print(self.stc, printout)
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
    word_wrap = False
    filename = None
    if len(sys.argv) > 1:
        if not sys.argv[-1].startswith("-"):
            filename = sys.argv[-1]
    if '-d' in sys.argv:
        STCPrintout.debuglevel = 1
    if '-w' in sys.argv:
        word_wrap = True
    if filename:
        frame.loadFile(filenae, word_wrap)
    else:
        frame.loadSample(word_wrap=word_wrap)
    frame.Show()
    app.MainLoop()
