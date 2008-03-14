# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Generic text file editing support.

Major mode for generic text editing.
"""

import os

import wx
import wx.stc

from peppy.major import *
from peppy.yapsy.plugins import IPeppyPlugin
from peppy.fundamental import FundamentalMode
from peppy.lib.autoindent import BasicAutoindent

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


class TextMode(FundamentalMode):
    """Major mode for editing text files.
    """
    keyword='Text'
    icon='icons/page_white_text.png'
    regex="(\.txt|[Rr][Ee][Aa][Dd][Mm][Ee]*)$"

    default_classprefs = (
        StrParam('minor_modes', ''),
        BoolParam('word_wrap', True),
        )
    
    autoindent = BasicAutoindent()
    

class TextModePlugin(IPeppyPlugin):
    """Yapsy plugin to register TextMode.
    """
    def aboutFiles(self):
        return {'sample.txt': _sample_file}
    
    def getMajorModes(self):
        yield TextMode
