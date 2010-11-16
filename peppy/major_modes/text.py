# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Generic text file editing support.

Major mode for generic text editing.
"""

import os

import wx
import wx.stc

from peppy.major import *
from peppy.actions import *
from peppy.yapsy.plugins import IPeppyPlugin
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import FundamentalMode
from peppy.lib.autoindent import BasicAutoindent
from peppy.lib.foldexplorer import *
from peppy.lib.textutil import *

_sample_file="""\
Life is what happens while you're busy making other plans.
-- John Lennon

Everything should be made as simple as possible, but no simpler.
-- Albert Einstein

The key to tennis is to win the last point.
-- Jim Courier

if (under_attack = TRUE) retaliate();
-- unknown C programmer

If God invented marathons to keep people from doing anything more stupid, triathlon must have taken Him completely by surprise.
-- P. Z. Pearce, M.D.

Experience is that marvelous thing that enables you recognize a mistake when you make it again.
-- F. P. Jones

^[:wq! Crap! Thought I was in vi.
-- Steven Clarke

Always use the bathroom when you can, because you never know when you'll get another chance.
-- Winston Churchill
"""


html_converters = [
    (text2HtmlFixed, 'each line in fixed width font'),
    (text2HtmlPlain, 'each line in proportional font'),
    (text2HtmlParagraph, 'consecutive non-blank lines to paragraph'),
    ]
html_converter_descriptions = [item[1] for item in html_converters]

font_size_values = [0, 1, 3, 5, 7]
font_size_descriptions = ['tiny', 'small', 'medium', 'large', 'extra large',]
if wx.Platform == "__WXMAC__":
    default_font_index = 0
else:
    default_font_index = 2


class TextMode(NonFoldCapableCodeExplorerMixin, FundamentalMode):
    """Major mode for editing text files.
    """
    keyword = 'Text'
    editra_synonym = 'Plain Text'
    stc_lexer_id = wx.stc.STC_LEX_NULL
    start_line_comment = ''
    end_line_comment = ''
    icon='icons/page_white_text.png'

        
    default_classprefs = (
        StrParam('extensions', 'txt', fullwidth=True),
        StrParam('filename_regex', '[Rr][Ee][Aa][Dd][Mm][Ee].*', fullwidth=True),
        StrParam('minor_modes', ''),
        BoolParam('word_wrap', True),
        IndexChoiceParam('print_style', html_converter_descriptions,
                         0, 'How lines are displayed when printed'),
        IndexChoiceParam('font_size', font_size_descriptions,
                         default_font_index, 'Size of font when printing'),
        )
    
    autoindent = BasicAutoindent()
    
    def checkFoldEntryFunctionName(self, line, last_line):
        header = self.GetLine(line).rstrip()
        if header and header[0] in "=-`:'\"~^_*+#<>":
            # Make sure the entire line consists of only that character.
            other_chars = header.strip(header[0])
            if len(other_chars) == 0:
                # Determine whether there is an overline and underline, or if
                # it's only an underline.  Overline and underline must match
                # in both character type and length, or it's an error.
                if line + 2 < last_line:
                    underline = self.GetLine(line + 2).rstrip()
                    if underline == header:
                        # Found section header
                        title = self.GetLine(line + 1).strip()
                        return title, line, 3
                
                # If there isn't a complementary overline/underline pair, the
                # header that was found originally is an underline.
                if line > 1:
                    title = self.GetLine(line - 1).strip()
                    return title, line - 1, 1
                
        return "", -1, 1

    def getHtmlForPrinting(self):
        """Produces an HTML representation of its data.
        
        Uses one of the HTML conversion utilities from textutil.py
        """
        converter = html_converters[self.classprefs.print_style][0]
        font_size = font_size_values[self.classprefs.font_size]
        html = converter(self.buffer.stc.GetText(), font_size)
        return html


class PrintStyleSelect(RadioAction):
    """Select printing style
    
    Instead of going through the preferences dialog, this action allows
    selecting of the print style on the menu.
    """
    name = "Paragraph Style"
    inline = False
    localize_items = True
    default_menu = (("File/Print Options", 995.5), 100)

    def getIndex(self):
        return self.mode.classprefs.print_style
                                           
    def getItems(self):
        return html_converter_descriptions

    def action(self, index=-1, multiplier=1):
        self.mode.classprefs.print_style = index

class FontSizeSelect(RadioAction):
    """Select font size for printing 
    
    Instead of going through the preferences dialog, this action allows
    selecting of the print font size on the menu.
    """
    name = "Font Size"
    inline = False
    localize_items = True
    default_menu = (("File/Print Options", 995.5), 200)

    def getIndex(self):
        return self.mode.classprefs.font_size
                                           
    def getItems(self):
        return font_size_descriptions

    def action(self, index=-1, multiplier=1):
        self.mode.classprefs.font_size = index


class TextModePlugin(IPeppyPlugin):
    """Yapsy plugin to register TextMode.
    """
    def aboutFiles(self):
        return {'sample.txt': _sample_file}
        
    def getCompatibleActions(self, modecls):
        actions = []
        if issubclass(modecls, TextMode):
            actions.extend([PrintStyleSelect, FontSizeSelect])
        return actions
    
    def getMajorModes(self):
        yield TextMode
