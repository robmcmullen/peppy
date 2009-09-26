# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Progress 4GL programming language editing support.

Major mode for editing Progress 4GL files.

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

class Progress4GLMode(FundamentalMode):
    """Stub major mode for editing Progress 4GL files.

    This major mode has been automatically generated and is a boilerplate/
    placeholder major mode.  Enhancements to this mode are appreciated!
    """
    keyword = 'Progress 4GL'
    editra_synonym = 'Progress 4GL'
    stc_lexer_id = 7
    start_line_comment = u'/*'
    end_line_comment = u'*/'
    
    icon = 'icons/page_white.png'
    
    default_classprefs = (
        StrParam('extensions', '4gl', fullwidth=True),
       )


class Progress4GLModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface for Progress 4GL
    """
   
    def getMajorModes(self):
        yield Progress4GLMode
