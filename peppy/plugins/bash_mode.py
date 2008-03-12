# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Fortran programming language editing support.

Major mode for editing Fortran files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class BashMode(SimpleFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing Bash/KSH/Bourne shell scripts.
    """
    keyword = 'Bash'
    editra_synonym = 'Bash Shell Script'
    
    icon = 'icons/page_white_shell.png'
    regex = "\.sh$"
    
    fold_function_match = ["function "]

    default_classprefs = (
        Param('indent_after', r'(\{(?![^\}]*\})|\b(then|elif|else)\b(?!.+fi)|\bdo\b(?!.+done)|\bcase\s+.+\s+in\b(?!.*esac)|\[\[)'),
        Param('indent', r'\$\{.*\}'),
        Param('unindent', r'([}]\s*$|\b(fi|elif|else)\b|\bdone\b|\besac\b|\]\])'),
       )
    
    autoindent = None
    
    def createPostHook(self):
        if not self.autoindent:
            self.__class__.autoindent = RegexAutoindent(self.classprefs.indent_after,
                                                        self.classprefs.indent,
                                                        self.classprefs.unindent,
                                                        '')
    
    def findIndent(self, linenum):
        return self.autoindent.getReindentColumn(self, linenum)
    
    def getReindentColumn(self, linenum, linestart, pos, before, col, ind):
        return self.autoindent.getReindentColumn(self, linenum)


class BashModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface.
    """
   
    def getMajorModes(self):
        yield BashMode
