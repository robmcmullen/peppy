# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time, new, re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.debug import *



class BadParagraphError(RuntimeError):
    pass


class ParagraphInfo(debugmixin):
    """Summary object about the currently selected paragraph.
    
    This object is built up as the paragraph mixin is searching through the
    file looking for the boundaries of the paragraph.  It is then used as
    input to the paragraph fill and other commands.
    """
    def __init__(self, stc, start, end=-1):
        """Initialize the structure by specifying a line that belongs to the
        paragraph.
        """
        self.s = stc
        self.clearLines()
        if end == -1:
            end = start
        self.findParagraph(start, end)
    
    def clearLines(self):
        self.cursor_linenum = 0
        self.start = 0
        self.end = 0
        self._startlines = []
        self._endlines = []
        self._lines = []
    
    def findParagraph(self, start, end):
        """Return a ParagraphInfo object from the current paragraph.
        
        A paragraph is defined as either: 1) a group of lines delimited by
        lines that only contain whitespace, or 2) a group of lines that share
        a common prefix.
        """
        linenum = self.s.LineFromPosition(start)
        self.initParagraph(linenum)
        
        # find the start of the paragraph by searching backwards till the
        # prefix changes or we find a line with only whitespace in it
        while linenum > 0:
            linenum -= 1
            if not self.findParagraphStart(linenum):
                break
        
        endlinenum = self.s.LineFromPosition(end)
        if endlinenum > self.cursor_linenum:
            # find all the lines in the middle, doing the best to strip off any
            # leading comment chars from the line
            linenum = self.cursor_linenum
            while linenum < endlinenum:
                linenum += 1
                leader, line, trailer = self.s.splitCommentLine(self.s.GetLine(linenum))
                self.addEndLine(linenum, line)
                
        # Now, find the end of the paragraph by searching forward until the
        # comment prefix changes or we find only white space
        lastlinenum = self.s.GetLineCount()
        self.dprint("start=%d count=%d end=%d" % (self.cursor_linenum, lastlinenum, endlinenum))
        while endlinenum < lastlinenum:
            endlinenum += 1
            if not self.findParagraphEnd(endlinenum):
                break
    
    def initParagraph(self, linenum):
        self.cursor_linenum = linenum
        
        line = self.s.GetLine(linenum)
        self.leader_pattern, line, self.trailer = self.s.splitCommentLine(line)
        #dprint("leader='%s' trailer='%s'" % (self.leader_pattern, self.trailer))
        
        # The line list is maintained in reverse when searching backward,
        # then is reversed before being added to the final list
        self.addStartLine(linenum, line)
        
        # set initial region end position that will be adjusted as we
        # add lines to the region.
        self.end = self.s.GetLineEndPosition(linenum)

    def findParagraphStart(self, linenum):
        """Check to see if a previous line should be included in the
        paragraph match.
        
        Routine designed to be overridden by subclasses to evaluate
        if a line should be included in the list of lines that belong with
        the current paragraph.
        
        Add the line to the ParagraphInfo class using addStartLine if it
        belongs.
        
        Return True if findParagraph should continue searching; otherwise
        return False
        """
        leader, line, trailer = self.s.splitCommentLine(self.s.GetLine(linenum))
        self.dprint(line)
        if leader != self.leader_pattern or len(line.strip())==0:
            return False
        self.addStartLine(linenum, line)
        return True
    
    def findParagraphEnd(self, linenum):
        """Check to see if a following line should be included in the
        paragraph match.
        
        Routine designed to be overridden by subclasses to evaluate
        if a line should be included in the list of lines that belong with
        the current paragraph.
        
        Add the line to the ParagraphInfo class using addEndLine if it belongs.
        
        Return True if findParagraph should continue searching; otherwise
        return False
        """
        leader, line, trailer = self.s.splitCommentLine(self.s.GetLine(linenum))
        self.dprint(line)
        if leader != self.leader_pattern or len(line.strip())==0:
            return False
        self.addEndLine(linenum, line)
        return True
        
    def addStartLine(self, linenum, line):
        """Add the line to the list and update the starting position"""
        self._startlines.append(line)
        self.start = self.s.PositionFromLine(linenum)
        
    def addEndLine(self, linenum, line):
        """Add the line to the list and update the starting position"""
        self._endlines.append(line)
        self.end = self.s.GetLineEndPosition(linenum)
        
    def getLines(self):
        """Get the list of lines in the paragraph"""
        if not self._lines:
            # The starting lines are stored in reverse order for easy appending
            self._startlines.reverse()
            self._lines.extend(self._startlines)
            self._lines.extend(self._endlines)
        return self._lines
    
    def replaceLines(self, lines):
        self._lines = lines[:]
    
    def addPrefix(self, prefix=None):
        """Add the original prefix to all the lines.
        
        This restores the prefix to all of the saved lines; used, for example,
        after reformatting the lines to remove excess whitespace or line
        breaks.
        """
        if prefix is None:
            prefix = self.leader_pattern
        newlines = [prefix + line for line in self._lines]
        self._lines = newlines
