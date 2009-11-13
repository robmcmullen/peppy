# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""m4 macro language editing support.

Major mode for editing M4 files.
"""

import os

import wx
import wx.stc

from peppy.major import *
from peppy.yapsy.plugins import IPeppyPlugin
from peppy.fundamental import FundamentalMode
from peppy.lib.autoindent import BasicAutoindent
from peppy.lib.stclexer import BaseLexer
from peppy.lib.foldexplorer import *
from peppy.actions.base import *
from peppy.debug import *


class M4Lexer(BaseLexer):
    keywords = [
        (0, "changecom changequote decr define defn divert divnum dnl dumpdef "
         "errprint eval ifdef ifelse include incr index len m4exit m4wrap "
         "maketemp popdef pushdef shift sinclude substr syscmd sysval "
         "traceon traceoff translit undefine undivert"),
        ]
    
    styles = [
        (0, "default_style"),
        (1, "comment_style"),
        (2, "keyword_style"),
        ]
    
    def getEditraStyleSpecs(self):
        return self.styles
    
    def adjustStart(self, stc, start):
        col = stc.GetColumn(start)
        if col != 0:
            start = stc.PositionFromLine(stc.LineFromPosition(start))
        return start
    
    def iterStyles(self, stc, start, end):
        # Simplistic styler for comments only
        text = stc.GetTextRangeUTF8(start, end)
        lines = text.splitlines(True)
        for line in lines:
            count = len(line)
            if line.startswith("dnl "):
                yield start, count, 1
            else:
                yield start, count, 0
            start += count



class M4Mode(NonFoldCapableCodeExplorerMixin, FundamentalMode):
    """Major mode for editing text files.
    """
    keyword = 'M4'
    stc_lexer_id = M4Lexer()
    stc_extra_properties = [
        ("fold", "1"),
        ("fold.comment", "1"),
        ("fold.compact", "0"),
        ]
    start_line_comment = u'dnl '
    end_line_comment = ''
    icon='icons/page_white_text.png'
    
    default_classprefs = (
        StrParam('extensions', 'm4 ac', fullwidth=True),
        )
    
    autoindent = BasicAutoindent()

class M4ModePlugin(IPeppyPlugin):
    def getMajorModes(self):
        yield M4Mode
