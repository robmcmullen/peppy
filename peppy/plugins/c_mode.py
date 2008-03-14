# peppy Copyright (c) 2006-2008 Rob McMullen
# c_mode Copyright (c) 2007 Julian Back
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""C programming language editing support.

Major mode for editing ANSI C files.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import FoldingAutoindent
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

_sample_file="""\
#include <stdio.h>

int main(int argc, char *argv[])
{
   printf("Hello, world!\\n");
   return 0;
}
"""

class SampleCFile(SelectAction):
    name = "&Open Sample C File"
    tooltip = "Open a sample C file"
    default_menu = "&Help/Samples"

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:hello.c")

class CMode(SimpleCLikeFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing C files.
    """
    keyword='C'
    icon='icons/page_white_c.png'
    regex="(\.c|\.h)$"
    
    default_classprefs = (
       )
    
    autoindent = FoldingAutoindent()


class CModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def aboutFiles(self):
        return {'hello.c': _sample_file}
    
    def getMajorModes(self):
        yield CMode

    def getActions(self):
        return [SampleCFile]
