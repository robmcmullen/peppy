# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Fortran programming language editing support.

Major mode for editing Fortran files.
"""

import os, re

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.actions.base import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import FundamentalMode
from peppy.paragraph import *


class F77ContinuationLine(LineOrRegionMutateAction):
    """Mark the current line or region as a set of contination lines
    
    """
    name = "Mark as Continuation Lines"
    default_menu = ("Fortran", -100)
    key_bindings = {'emacs': 'C-c C-7',
                    }
    def mutateLines(self, lines):
        modified = []
        for line in lines:
            if len(line) > 6:
                out = line[0:5] + "&" + line[6:]
            else:
                out = line
            modified.append(out)
        return modified


class Fortran77Autoindent(RegexAutoindent):
    digits = u"0123456789"
    
    def getElectricChars(self):
        return self.digits

    def electricChar(self, stc, uchar):
        i = ord(uchar)
        if i >= ord('0') and i <= ord('9'):
            pos = stc.GetCurrentPos()
            s = stc.GetStyleAt(pos)
            col = stc.GetColumn(pos)
            if not stc.isStyleComment(s) and col < 5:
                ln = stc.LineFromPosition(pos)
                fc = stc.PositionFromLine(ln)
                lc = stc.GetLineEndPosition(ln)
                text = stc.GetTextRange(fc, lc)
                #dprint("pos=%d col=%d ln=%d fc=%d lc=%d len=%d" % (pos, col, ln, fc, lc, len(text)))
                #dprint("1234567")
                #dprint(text)
                if len(text) > 5:
                    numbers = text[0:5]
                    continuation = text[5]
                    remainder = text[6:]
                else:
                    numbers = text + " "*(5 - len(text))
                    continuation = " "
                    remainder = ""
                numbers = numbers[0:col] + uchar + numbers[col:]
                before = len(numbers)
                numbers = numbers.lstrip()
                if before > len(numbers):
                    col -= before - len(numbers)
                numbers = numbers.strip()
                #dprint("pos=%d col=%d ln=%d fc=%d lc=%d len=%d" % (pos, col, ln, fc, lc, len(text)))
                line = "%-5s%s%s" % (numbers, continuation, remainder)
                #dprint("1234567")
                #dprint(line)
                stc.SetTargetStart(fc)
                stc.SetTargetEnd(lc)
                stc.ReplaceTarget(line)
                stc.GotoPos(fc + col + 1)
                return True
        return False

    def getNewLineIndentString(self, stc, col, ind):
        """Return the number of characters to be indented on a new line
        
        @param stc: stc of interest
        @param col: column position of cursor on line
        @param ind: indentation in characters of cursor on line
        """
        return stc.GetIndentString(6)

    def findIndent(self, stc, linenum):
        ln = linenum
        pos = 0

        fc = stc.PositionFromLine(ln)
        s = stc.GetStyleAt(fc)
        if stc.isStyleComment(s):
            # comment lines aren't indented at all in F77
            return pos

        # find the first line with content that is not starting with comment
        # text, and take the base indent position from that
        above = ''
        while ln > 0:
            ln -= 1
            fc = stc.PositionFromLine(ln)
            s = stc.GetStyleAt(fc)
            if stc.isStyleComment(s):
                continue
            lc = stc.GetLineEndPosition(ln)
            text = stc.GetTextRange(fc, lc)
            if len(text) < 6:
                # skip lines that have only labels
                continue
            if text[5] != ' ':
                # skip continuation lines
                continue
            above = text[6:]
            pos = 6
            while pos < len(text) and text[pos] == ' ':
                pos += 1
            break

        # try 'couples' for an opening on the above line first.  since we only
        # adjust by 1 unit, we only need 1 match.
        adjustment = 0
        if '(' in self.couples and self.coupleBalance(stc, ln, '(', ')') > 0:
            adjustment += 1

        # check if we should indent, unless the line starts with comment text,
        # or the match is in comment text Here we look at the line above the
        # current line
        if self.reIndentAfter:
            match = self.reIndentAfter.search(above)
            self.dprint(above)
            if match:
                self.dprint("reIndentAfter: found %s at %d" % (match.group(0), match.start(0)))
                adjustment += 1

        # Now that we've found the base indent based on the lines above the
        # current line, check if the current line needs to be modified
        fc = stc.PositionFromLine(linenum)
        lc = stc.GetLineEndPosition(linenum)
        text = stc.GetTextRange(fc, lc)
        if len(text) > 6:
            # Note that no lines that I know of automatically indent
            # themselves, so we only check for lines that should unindent
            # themselves like ELSE, ENDIF, etc.
            text = text[6:]
            if self.reUnindent:
                match = self.reUnindent.search(text)
                if match:
                    self.dprint("reUnndent: found %s at %d" % (match.group(0), match.start(0)))
                    adjustment -= 1
        
        # Find the actual number of spaces to indent
        if adjustment > 0:
            pos += stc.GetIndent()
        elif adjustment < 0:
            pos -= stc.GetIndent()
        if pos < 0:
            pos = 0
        
        return pos
    
    def reindentLine(self, stc, linenum=None, dedent_only=False):
        if linenum is None:
            linenum = stc.GetCurrentLine()
        
        pos = stc.GetCurrentPos()
        s = stc.GetStyleAt(pos)
        if stc.isStyleComment(s):
            return self.reindentComment(stc, linenum, dedent_only)
        else:
            return self.reindentSourceLine(stc, linenum, dedent_only)
    
    def reindentComment(self, stc, ln, dedent_only):
        cursor = stc.GetCurrentPos()
        fc = stc.PositionFromLine(ln)
        lc = stc.GetLineEndPosition(ln)
        text = stc.GetTextRange(fc, lc)
        count = len(text)
        pos = 0
        while pos < count and text[pos] == ' ':
            pos += 1
        stc.SetTargetStart(fc)
        stc.SetTargetEnd(lc)
        stc.ReplaceTarget(text[pos:count])
        cursor -= pos
        return cursor
    
    def reindentSourceLine(self, stc, ln, dedent_only):
        cursor = stc.GetCurrentPos()
        fc = stc.PositionFromLine(ln)
        lc = stc.GetLineEndPosition(ln)
        text = stc.GetTextRange(fc, lc)
        #dprint("1234567")
        #dprint(text)
        #col = stc.GetColumn(cursor)
        #dprint(" "*col + "_")
        if len(text) > 5:
            numbers = text[0:5]
            continuation = text[5]
            remainder = text[6:]
        else:
            numbers = text + " "*(5 - len(text))
            continuation = " "
            remainder = ""
        
        newind = self.findIndent(stc, ln) - 6
        if newind < 0:
            newind = 0
        #dprint("newind: %d" % newind)
        
        col = stc.GetColumn(cursor)
        if col < 5:
            cursor = fc + 6 + newind
        elif col > 5:
            before = len(remainder)
            remainder = remainder.lstrip()
            leading_blanks = before - len(remainder)
            #dprint("leading blanks: %d" % leading_blanks)
            if leading_blanks > newind:
                cursor -= leading_blanks - newind
            elif col - 6 <= newind:
                cursor = fc + 6 + newind
        remainder = remainder.lstrip()
        remainder = " "*newind + remainder
        
        numbers = numbers.strip()
        line = "%-5s%s%s" % (numbers, continuation, remainder)
        #dprint("1234567")
        #dprint(line)
        #col = stc.GetColumn(cursor)
        #dprint(" "*col + "_")
        stc.SetTargetStart(fc)
        stc.SetTargetEnd(lc)
        stc.ReplaceTarget(line)
        return cursor


class F77CommentParagraph(ParagraphInfo):
    def findParagraph(self, start, end):
        style = self.s.GetStyleAt(start)
        if style in self.s.getCommentStyles():
            start, end = self.s.findSameStyle(start)
#            dprint((start, self.s.GetCharAt(start), end, self.s.GetCharAt(end)))
#            dprint("'%s'" % self.s.GetTextRange(start, end))
            linenum = self.s.LineFromPosition(start)
            self.initParagraph(linenum)
            self.addCommentLinesToParagraph(linenum, start, end)
            return
        raise BadParagraphError

    def addCommentLinesToParagraph(self, linenum, start, end):
        # First line is already in info.  Need to add subsequent lines
        linenum += 1
        start = self.s.PositionFromLine(linenum)
        while start < end:
            line = self.s.GetLine(linenum)
#            dprint("%d,%d,%d: '%s'" % (linenum, start, end, line))
            leader, line, trailer = self.s.splitCommentLine(line)
            line = line.strip()
            self.addEndLine(linenum, line)
            linenum += 1
            start = self.s.PositionFromLine(linenum)

    def addStartLine(self, linenum, line):
        """Add the line to the list and update the starting position"""
        nonblank = line.lstrip()
        if len(nonblank) < len(line):
            self.leader_pattern += " " * (len(line) - len(nonblank))
        self._startlines.append(nonblank)
        self.start = self.s.PositionFromLine(linenum)


class Fortran77Mode(SimpleFoldFunctionMatchMixin, FundamentalMode):
    """Major mode for editing Fortran 77 (fixed format) files.
    """
    keyword = 'Fortran 77'
    editra_synonym = 'Fortran 77'
    stc_lexer_id = wx.stc.STC_LEX_F77
    start_line_comment = '*'
    start_line_comment_list = ['*', 'c', 'C', '!']
    end_line_comment = ''
    
    icon = 'icons/page_white_f77.png'
    
    fold_function_match = ["SUBROUTINE ", "FUNCTION ","subroutine ", "function ",
                           "BLOCK DATA ", "block data "]

    default_classprefs = (
        StrParam('extensions', 'f for', fullwidth=True),
        StrParam('keyword_set_0', unique_keywords[38], hidden=False, fullwidth=True),
        StrParam('keyword_set_1', unique_keywords[39], hidden=False, fullwidth=True),
        StrParam('keyword_set_2', unique_keywords[40], hidden=False, fullwidth=True),
        IntParam('edge_column', 72),
        BoolParam('indentation_guides', False),
        
        Param('indent_after', r'(\b(IF)\b(?=.+THEN)|\b(ELSEIF|ELSE|DO))', fullwidth=True),
        Param('indent', r'', fullwidth=True),
        Param('unindent', r'(\b(ELSEIF|ELSE|ENDIF|ENDDO|CONTINUE))', fullwidth=True),
       )
    
    autoindent = None
    
    def createPostHook(self):
        if not self.autoindent:
            self.__class__.autoindent = Fortran77Autoindent(
                self.classprefs.indent_after, self.classprefs.indent,
                self.classprefs.unindent, '', re.IGNORECASE)

    ##### Comment handling
    def findParagraph(self, start, end=-1):
        """Override the standard findParagraph to properly handle Fortran
        comment blocks.  Comment blocks start with c, C, or ! in column 1.
        """
        # See if cursor is inside a comment block
        try:
            info = F77CommentParagraph(self, start)
        except BadParagraphError:
            # Check if cursor is on the last line of a comment block, possibly
            # after the comment.
            linenum = self.LineFromPosition(start)
            start = self.PositionFromLine(linenum)
            try:
                info = F77CommentParagraph(self, start)
            except BadParagraphError:
                # Nope, treat it as a regular paragraph
                info = FundamentalMode.findParagraph(self, start, end)
        return info


class FortranModePlugin(IPeppyPlugin):
    """C plugin to register modes and user interface.
    """
   
    def getCompatibleActions(self, modecls):
        if issubclass(modecls, Fortran77Mode):
            return [
                F77ContinuationLine,
                ]
        
    def getMajorModes(self):
        yield Fortran77Mode
