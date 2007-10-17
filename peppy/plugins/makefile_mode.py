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

# A sample makefile is provided
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

# This action opens up the sample makefile, demonstrating just about the
# minimum amount of code that you need to create an action
class SampleMakefile(SelectAction):
    # name is required, otherwise the action won't be created
    name = "&Open Sample Makefile"
    
    # tooltip is optional, but if present will appear in the statusbar
    # when hovering over the menu item or toolbar entry.
    tooltip = "Open a sample Makefile"
    
    # default_menu is required in order to appear in the menu bar.
    default_menu = "&Help/Samples"
    
    # action is called regardless of how the action was requested: the
    # menubar, the toolbar, or the keyboard
    def action(self, index=-1, multiplier=1):
        self.frame.open("about:sample.mak")


# The Makefile major mode is descended from FundamentalMode, meaning that
# it is an STC based editing window.  Currently, no particular additional
# functionality is present in the mode except for overriding some
# classprefs
class MakefileMode(FundamentalMode):
    """Major mode for editing Makefiles.
    
    """
    # keyword is required: it's a one-word name that must be unique
    # compared to all other major modes
    keyword='Makefile'
    
    # Specifying an icon here will cause it to be displayed in the tab
    # of any file using the Makefile mode
    icon='icons/cog.png'
    
    # Any files matching this regex will be candidates for this major
    # mode
    regex="(\.mak|[Mm]akefile.*)$"

    default_classprefs = (
        # Overrides from FundamentalMode classprefs
        BoolParam('use_tab_characters', True),
        IntParam('tab_size', 8),
        BoolParam('word_wrap', True),
        )


# This is the plugin definition for MakefileMode.  This is the only way
# to inform peppy of the enhancement to the capabilities.  It will ignore
# anything defined in the file unless it is registered using methods of
# IPeppyPlugin.
class MakefilePlugin(IPeppyPlugin):
    """Makefile plugin to register modes and user interface.
    """
    # This registers the data in sample_file as the url "about:sample.mak"
    def aboutFiles(self):
        return {'sample.mak': _sample_file}
    
    # This registers the makefile mode so that it can be used
    def getMajorModes(self):
        yield MakefileMode
    
    # Only the actions that appear in getActions will be available
    def geActions(self):
        return [SampleMakefile]
