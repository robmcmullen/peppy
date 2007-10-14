# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Makefile editing support.

Major mode for editing makefiles.
"""

import os,struct
import keyword
from cStringIO import StringIO

import wx
import wx.stc

from peppy.menu import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

_sample_file = """\
VAR = something
OTHER = $(VAR)
OTHER1 = ${VAR}
DIR = $(shell ls -1)

.SUFFIXES: .o

all: foo
	echo stuff

foo: bar.o baz.o

clean:
	rm -rf *~ *.o
    
.PHONY: print-% clean

print-%: ; @ echo $* = $($*)
"""


class SampleMakefile(SelectAction):
    name = _("&Open Sample Makefile")
    tooltip = _("Open a sample Makefile")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:sample.mak")


class MakefileMode(FundamentalMode):
    """Major mode for editing Makefiles.

    STC has a built-in Makefile mode, so we'll be using that.
    """
    keyword='Makefile'
    icon='icons/cog.png'
    regex="(\.mak|[Mm]akefile)$"

    start_line_comment = "# "

    default_classprefs = (
        StrParam('minor_modes', ''),
        IntParam('tab_size', 8),
        BoolParam('word_wrap', True),
        StrParam('sample_file', _sample_file),
        )


class MakefilePlugin(IPeppyPlugin):
    """Makefile plugin to register modes and user interface.
    """
    def aboutFiles(self):
        return {'sample.mak': MakefileMode.classprefs.sample_file}
        
    def getMajorModes(self):
        yield MakefileMode
    
    default_menu=((None,(_("&Help"),_("&Samples")),MenuItem(SampleMakefile)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

