# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""reStructuredText file editing support.

Major mode for editing reStructuredText files.
"""

import os

import wx
import wx.stc

from peppy.major import *
from peppy.yapsy.plugins import IPeppyPlugin
from peppy.fundamental import FundamentalMode
from peppy.lib.autoindent import BasicAutoindent
from peppy.lib.foldexplorer import *
from peppy.actions.base import *
from peppy.debug import *


class AdjustSectionAdornment(OneLineModificationAction):
    """Adjust the current line's adornment to match the length of the title.
    
    Adds or removes characters in the section overlines and underlines to match
    the length of the text.
    """
    name = "Adjust Under/Overline"
    default_menu = ("RST", -100)
    key_bindings = {'emacs': 'C-c C-a',
                    }

    def mutate(self, txt):
        return self.mode.adjustAdornment(txt)

    def adjustTarget(self):
        s = self.mode
        dprint("Orig target: %d - %d" % (s.GetTargetStart(), s.GetTargetEnd()))
        line = s.LineFromPosition(s.GetTargetStart())
        next_line = line + 1
        if next_line < s.GetLineCount():
            text = s.GetLine(next_line)
            if len(text) > 0 and text[0] in RSTMode.adornment_chars:
                s.SetTargetEnd(s.GetLineEndPosition(next_line))
                
                # Only if there is an underline will an overline be detected
                if line > 0:
                    prev_line = line - 1
                    text = s.GetLine(prev_line)
                    if len(text) > 0 and text[0] in RSTMode.adornment_chars:
                        s.SetTargetStart(s.PositionFromLine(prev_line))
        dprint("New target: %d - %d" % (s.GetTargetStart(), s.GetTargetEnd()))



class RSTMode(NonFoldCapableCodeExplorerMixin, FundamentalMode):
    """Major mode for editing text files.
    """
    keyword = 'reStructuredText'
    stc_lexer_id = 1
    start_line_comment = ''
    end_line_comment = ''
    icon='icons/page_white_text.png'
    
    adornment_chars = "=-`:'\"~^_*+#<>"

    default_classprefs = (
        StrParam('extensions', 'rst', fullwidth=True),
        )
    
    autoindent = BasicAutoindent()
    
    def checkFoldEntryFunctionName(self, line, last_line):
        header = self.GetLine(line).rstrip()
        if header and header[0] in self.adornment_chars:
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

    def adjustAdornment(self, txt):
        """Adjust the adornment on the text
        
        @param txt: a two or three line text string.  If two lines, it must
        contain a section title and and underline, and if three lines must
        contain an overline, title, and underline.
        
        @returns: text with underline (and optional overline) adjusted to match
        the length of the title.  If the underline and overline are made up of
        different characters, the overline is modified to match the underline.
        """
        lines = txt.splitlines()
        dprint(lines)
        if len(lines) == 2:
            adornment = lines[1][0] * len(lines[0])
            txt = lines[0] + self.getLinesep() + adornment
        elif len(lines) == 3:
            adornment = lines[2][0] * len(lines[1])
            txt = adornment + self.getLinesep() + lines[1] + self.getLinesep() + adornment
        
        return txt

class RSTModePlugin(IPeppyPlugin):
    def getCompatibleActions(self, modecls):
        if issubclass(modecls, RSTMode):
            return [
                AdjustSectionAdornment,
                ]
        
    def getMajorModes(self):
        yield RSTMode
