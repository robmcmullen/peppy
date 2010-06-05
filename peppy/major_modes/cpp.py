# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""C++ programming language editing support.

Major mode for editing C++ files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import CStyleAutoindent
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import FundamentalMode

class CPlusPlusMode(SimpleCLikeFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing C++ files.
    """
    keyword = 'C++'
    editra_synonym = 'CPP'
    stc_lexer_id = wx.stc.STC_LEX_CPP
    start_line_comment = u'//'
    end_line_comment = ''
    
    icon = 'icons/page_white_cplusplus.png'
    
    default_classprefs = (
        StrParam('extensions', 'c++ cc cpp cxx h++ hh hpp hxx', fullwidth=True),
        StrParam('keyword_set_0', unique_keywords[105], hidden=False, fullwidth=True),
        StrParam('keyword_set_1', unique_keywords[106], hidden=False, fullwidth=True),
        StrParam('keyword_set_2', unique_keywords[14], hidden=False, fullwidth=True),
       )
    
    autoindent = CStyleAutoindent()


class CPlusPlusModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def getMajorModes(self):
        yield CPlusPlusMode
