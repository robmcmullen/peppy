# peppy Copyright (c) 2006-2007 Rob McMullen
# c_mode Copyright (c) 2007 Julian Back
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""C programming language editing support.

Major mode for editing ANSI C files.
"""

import os

import wx
import wx.stc

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
    name = _("&Open Sample C File")
    tooltip = _("Open a sample C file")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:hello.c")

class CMode(FundamentalMode):
    """Major mode for editing C files.
    """
    keyword='C'
    icon='icons/page_white_c.png'
    regex="(\.c|\.cc|\.cpp|\.h|\.hh\.hpp)$"
    
    default_classprefs = (
       StrParam('sample_file', _sample_file),
       )


class CModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def aboutFiles(self):
        return {'hello.c': _sample_file}
    
    def getMajorModes(self):
        yield CMode

    default_menu=((None,(_("&Help"),_("&Samples")),MenuItem(SampleCFile)),
                 )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)
