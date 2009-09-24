# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Makefile editing support.

Major mode for editing makefiles.
"""

import os, re
import keyword
from cStringIO import StringIO

import wx
import wx.stc

from peppy.actions import *
from peppy.major import *
from peppy.fundamental import *
from peppy.lib.autoindent import *
from peppy.lib.foldexplorer import *

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


class MakefileAutoindent(BasicAutoindent):
    foldre = re.compile("^[^\s\"\']+:", flags=re.MULTILINE)
    commandre = re.compile("[^\s\"\']+:")
    
    def findIndent(self, stc, linenum):
        """Reindent the specified line to the correct level.

        Given a line, use some regex matching to determine the correct indent
        level.
        """
        # The text begins at indpos; check some special cases to see if there
        # should be a dedent
        before = stc.GetLineIndentPosition(linenum)
        end = stc.GetLineEndPosition(linenum)
        cmd = stc.GetTextRange(before, end)
        dprint(cmd)
        
        # skip blank lines
        if len(cmd) > 0:
            # don't reindent comments
            if cmd[0] == "#": return stc.GetLineIndentation(linenum)
            
            match = self.commandre.match(cmd)
            if match:
                # it's a command, so it shouldn't be indented.
                self.dprint("It's a command!  indent=0")
                return 0
        
        # OK, not a command, so it depends on context.
        while linenum > 0:
            linenum -= 1
            start = stc.PositionFromLine(linenum)
            style = stc.GetStyleAt(start)
            self.dprint("line=%d start=%d style=%d" % (linenum, start, style))
            if style == 5:
                # OK, it's a possible command.
                end = stc.GetLineEndPosition(linenum)
                cmd = stc.GetTextRange(start, end)
                match = self.commandre.match(cmd)
                if match:
                    # Yep, a command.  This line should be tabbed
                    self.dprint("tabbed!")
                    return 8
                return 0
            elif style == 3:
                return 0

        # If all else fails, just use the same amount of indentation as before
        return stc.GetLineIndentation(linenum)


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
    regex="(\.mak|[Mm]akefile$|[Mm]akefile\..*)$"

    default_classprefs = (
        StrParam('filename_regex', '(GNU)?([Mm]akefile$|[Mm]akefile\..*)$"', fullwidth=True),
        StrParam('extensions', 'mak', fullwidth=True),
        BoolParam('use_tab_characters', True),
        IntParam('tab_size', 8),
        BoolParam('word_wrap', True),
        )

    autoindent = MakefileAutoindent()

    def iterFoldEntries(self, line, last_line=-1):
        """Iterator returning items to be included in code explorer.
        
        Given the range of lines in the current mode, return a FoldExplorerNode
        for each item that should be included in the code explorer.
        """
        if last_line < 0:
            last_line = self.GetLineCount()
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(last_line)
        text = self.GetTextRange(start, end)
        pos = 0
        lastpos = end - start
        while pos < lastpos:
            self.dprint("start=%d pos=%d last=%d" % (start, pos, lastpos))
            match = MakefileAutoindent.foldre.search(text, pos)
            if match:
                self.dprint(match.group(0))
                line = self.LineFromPosition(start + match.start(0))
                node = FoldExplorerNode(level=1, start=line, end=last_line, text=match.group(0))
                node.show = True
                yield node
                pos = match.end(0)
            else:
                break
        raise StopIteration


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
