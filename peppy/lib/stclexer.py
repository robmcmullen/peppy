#-----------------------------------------------------------------------------
# Name:        stclexer.py
# Purpose:     Custom lexers for the wx.StyledTextControl
#
# Author:      Rob McMullen
#
# Created:     2009
# RCS-ID:      $Id: $
# Copyright:   (c) 2009 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Custom lexers for the wx.StyledTextCtrl

This is a collection of custom lexers for the wx.StyledTextCtrl.

"""

import os, re
from cStringIO import StringIO

import wx.stc
try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        #print txt
        pass


class BaseLexer(debugmixin):
    """Base class for custom lexers.
    
    This lexer does nothing on its own except provide the interface to the
    custom lexers.
    """
    def styleText(self, stc, start, end):
        dprint("Styling text from %d - %d" % (start, end))
        start = self.adjustStart(stc, start)
        
        for pos, count, style in self.iterStyles(stc, start, end):
            #dprint("pos=%d, count=%d: token=%d" % (pos, count, style))
            if count > 0:
                stc.StartStyling(pos, 0x1f)
                stc.SetStyling(count, style)
    
    def adjustStart(self, stc, start):
        """Utility method in case subclass needs to adjust the start of the
        text range.
        
        Some lexers may fail if the text range starts in the middle of a word.
        It's not clear that the STC will ever do this, but just in case this
        method is provided to move the starting point backward if necessary.
        """
        return start
    
    def iterStyles(self, stc, start, end):
        """Splits the text into ranges based on similar styles.
        
        This method is a generator to provide the means to style the text
        by breaking the text range up into styling groups where each group
        contains the same style.
        
        Should be overridden in subclasses to provide custom styling.
        
        @returns: generator where each item is a tuple containing the start
        position, the number of characters to style, and the style ID number.
        """
        text = stc.GetTextRange(start, end)
        yield start, len(text), 0
    
    def getStyleBits(self):
        """Return the number of bits to be used for styling information.
        
        Typically 5; HTML and XML modes use 7.
        
        @returns integer
        """
        return 5
    
    def getEditraStyleSpecs(self):
        """Return the Editra style specs for this lexer.
        
        Editra style specs are a list of 2-tuples, where each tuple maps an
        integer style value to an Edtira style name.
        
        For instance, a simple lexer may define 3 styles and return this list:
        
        [(0, "default_style"), (1, "comment_style"), (2, "keyword_style")]
        
        @returns: list of 2-tuples, where each tuple maps an integer style
        value to an Editra style name.
        """
        return [(0, "default_style")]
