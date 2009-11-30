# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""68k Assembly programming language editing support.

Major mode for editing 68k Assembly files.

Supporting actions and minor modes should go here only if they are uniquely
applicable to this major mode and can't be used in other major modes.  If
actions can be used with multiple major modes, they should be put in a
separate plugin in the peppy/plugins directory.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class _68kAssemblyMode(FundamentalMode):
    """Stub major mode for editing 68k Assembly files.

    This major mode has been automatically generated and is a boilerplate/
    placeholder major mode.  Enhancements to this mode are appreciated!
    """
    keyword = '68k Assembly'
    editra_synonym = '68k Assembly'
    stc_lexer_id = wx.stc.STC_LEX_ASM
    start_line_comment = u';'
    end_line_comment = ''
    
    icon = 'icons/page_white.png'
    
    default_classprefs = (
        StrParam('extensions', '68k', fullwidth=True),
       )


class _68kAssemblyModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface for 68k Assembly
    """
   
    def getMajorModes(self):
        yield _68kAssemblyMode
