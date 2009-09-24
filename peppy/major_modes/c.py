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
from peppy.lib.autoindent import CStyleAutoindent
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode, ParagraphInfo
from peppy.paragraph import *

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


class CCommentParagraph(ParagraphInfo):
    def findParagraph(self, start, end):
        style = self.s.GetStyleAt(start)
        if style in self.s.getCommentStyles():
            start, end = self.s.findSameStyle(start)
            dprint((start, end))
            linenum = self.s.LineFromPosition(start)
            self.initParagraph(linenum)
            self.addCommentLinesToParagraph(linenum, start, end)
            return
        raise BadParagraphError

    def addCommentLinesToParagraph(self, linenum, start, end):
        # First line is already in info.  Need to add subsequent lines
        first = True
        linenum += 1
        start = self.s.PositionFromLine(linenum)
        while start < end:
            line = self.s.GetLine(linenum)
            #dprint("%d: %s" % (linenum, line))
            leader, line, trailer = self.s.splitCommentLine(line)
            match = self.s.mid_comment_regex.match(line)
            if match:
                #dprint(match.groups())
                line = match.group(2)
            line = line.strip()
            self.addEndLine(linenum, line)
            linenum += 1
            start = self.s.PositionFromLine(linenum)

    def addPrefix(self, prefix=None):
        """Add the comment prefix and suffix to all the lines.
        
        This restores the comment block to all of the saved lines; used, for
        example, after reformatting the lines to remove excess whitespace or
        line breaks.
        """
        newlines = ["/* " + self._lines[0]]
        newlines.extend(["** " + line for line in self._lines[1:]])
        newlines.append("*/")
        self._lines = newlines


class CMode(SimpleCLikeFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing C files.
    """
    keyword='C'
    icon='icons/page_white_c.png'
    
    default_classprefs = (
        StrParam('extensions', 'c h', fullwidth=True),
       )
    
    autoindent = CStyleAutoindent()
    mid_comment_regex = re.compile("(\s*[\*]+\s*)(.+)")

    def splitCommentLine(self, line, info=None):
        """Split the line into the whitespace leader and body of the line.
        
        Return a tuple containing the leading whitespace and comment
        character(s), the body of the line, and any trailing comment
        character(s)
        
        @param info: optional ParagraphInfo object to allow subclasses to have
        access to the object.
        """
        match = self.comment_regex.match(line)
        if match is None:
            match = self.mid_comment_regex.match(line)
            if match:
                dprint(match.groups())
                return ("/*", match.group(2), "")
            else:
                return ("", line, "")
        #dprint(match.groups())
        return match.group(1), match.group(2).strip(), match.group(3)

    def findParagraph(self, start, end=-1):
        """Override the standard findParagraph to properly handle several
        styles of C comment blocks.
        
        C style comment blocks may look like:
        
           /* line
           ** line
           */
        
        or
        
           /* line
            * line
            */
        
        or
        
           /* line
              line */
        
        or any number of similar variations.  This is a postprocessing call
        on the fundamental mode's findParagraph that can manipulate the
        ParagraphInfo object if it finds a comment block.
        """
        # See if cursor is inside a comment block
        try:
            info = CCommentParagraph(self, start)
        except BadParagraphError:
            # Check if cursor is on the last line of a comment block, possibly
            # after the comment.
            linenum = self.LineFromPosition(start)
            start = self.PositionFromLine(linenum)
            try:
                info = CCommentParagraph(self, start)
            except BadParagraphError:
                # Nope, treat it as a regular paragraph
                info = FundamentalMode.findParagraph(self, start, end)
        return info


class CModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def aboutFiles(self):
        return {'hello.c': _sample_file}
    
    def getMajorModes(self):
        yield CMode

    def getActions(self):
        return [SampleCFile]
