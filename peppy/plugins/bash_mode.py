# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Shell script programming language editing support.

Major mode for editing bash shell script files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class BashMode(JobControlMixin, SimpleFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing Bash/KSH/Bourne shell scripts.
    """
    keyword = 'Bash'
    editra_synonym = 'Bash Shell Script'
    
    icon = 'icons/page_white_shell.png'
    regex = "\.sh$"
    
    fold_function_match = ["function "]

    default_classprefs = (
        Param('indent_after', r'(\{(?![^\}]*\})|\b(then|elif|else)\b(?!.+fi)|\bdo\b(?!.+done)|\bcase\s+.+\s+in\b(?!.*esac)|\[\[)', fullwidth=True),
        Param('indent', r'\$\{.*\}', fullwidth=True),
        Param('unindent', r'([}]\s*$|\b(fi|elif|else)\b|\bdone\b|\besac\b|\]\])', fullwidth=True),
       )
    
    autoindent = None
    
    def createPostHook(self):
        if not self.autoindent:
            self.__class__.autoindent = RegexAutoindent(self.classprefs.indent_after,
                                                        self.classprefs.indent,
                                                        self.classprefs.unindent,
                                                        '')


class BashModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface.
    """
   
    def getMajorModes(self):
        yield BashMode
