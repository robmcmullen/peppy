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


class STCPrintout(wx.Printout):
    """Specific printing support of the wx.StyledTextCtrl for the wxPython
    framework
    
    
    """
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
        font = self.stc.GetDefaultFont()
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
