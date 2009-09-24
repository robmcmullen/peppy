# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Fortran programming language editing support.

Major mode for editing Fortran files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class Fortran77Mode(SimpleFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing Fortran 77 (fixed format) files.
    """
    keyword = 'Fortran77'
    editra_synonym = 'Fortran 77'
    
    icon = 'icons/page_white_f77.png'
    
    fold_function_match = ["SUBROUTINE ", "FUNCTION ","subroutine ", "function ",
                           "BLOCK DATA ", "block data "]

    default_classprefs = (
        StrParam('extensions', 'f for f77', fullwidth=True),
        IntParam('edge_column', 72),
        BoolParam('indentation_guides', False),
       )


class FortranModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def getMajorModes(self):
        yield Fortran77Mode
