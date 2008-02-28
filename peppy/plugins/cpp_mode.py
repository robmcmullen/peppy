# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""C++ programming language editing support.

Major mode for editing C++ files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class CPlusPlusMode(SimpleCLikeFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing C++ files.
    """
    keyword = 'C++'
    editra_synonym = 'CPP'
    
    icon = 'icons/page_white_cplusplus.png'
    regex = "(\.cc|\.cpp|\.cxx|\.CC|\.hh|\.hpp|\.hxx|\.HH)$"
    
    default_classprefs = (
       )

    def isStyleString(self, style):
        return style == 6
        
    def isStyleComment(self, style):
        return style == 1 or style == 2


class CPlusPlusModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def getMajorModes(self):
        yield CPlusPlusMode
