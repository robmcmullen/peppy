# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info

# Transcribed from KDE's kateautoindent.cpp which was licensed under the
# LGPLv2.  LGPL code can be relicensed under the GPL according to LGPL section
# 3, which is what I've done here.  The original kate code contained the
# following copyright:
#   Copyright (C) 2003 Jesse Yurkovich <yurkjes@iit.edu>
#   Copyright (C) 2004 >Anders Lund <anders@alweb.dk> (KateVarIndent class)
#   Copyright (C) 2005 Dominik Haumann <dhdev@gmx.de> (basic support for config page)

"""Autoindent code for peppy

This is a collection of autoindent code designed for use with peppy's
enhancements to the wx.StyledTextCtrl.

If you wanted to use this without peppy, you'd need to provide several
methods, including C{isStyleComment}, C{isStyleString}, C{getLinesep},
(and others) to the stc of interest.  See the implementation of them in
L{peppy.editra.stcmixin} and L{peppy.stcbase}.
"""

import os, re
import wx.stc
from peppy.debug import *


class BasicAutoindent(debugmixin):
    """Simple autoindent that indents the line to the level of the line above it.
    
    This is about the bare minimum indenter.  It just looks at the line above
    it and reports the indent level of that line.  No effort is made to look
    at syntax or anything.  Simple.
    """
    def __init__(self):
        pass
    
    def findIndent(self, stc, linenum):
        """Find proper indention of current line based on the previous line

        This is designed to be overridden in subclasses.  Given the current
        line and assuming the current line is indented correctly, figure out
        what the indention should be for the next line.
        
        @param linenum: line number
        @return: integer indicating number of columns to indent the following
        line
        """
        # look at indention of previous line
        prevind, prevline = stc.GetPrevLineIndentation(linenum)
        #if (prevind < indcol and prevline < linenum-1) or prevline < linenum-2:
        #    # if there's blank lines before this and the previous
        #    # non-blank line is indented less than this one, ignore
        #    # it.  Make the user manually unindent lines.
        #    return None

        # previous line is not blank, so indent line to previous
        # line's level
        return prevind

    def reindentLine(self, stc, linenum=None, dedent_only=False):
        """Reindent the specified line to the correct level.

        Changes the indentation of the given line by inserting or deleting
        whitespace as required.  This operation is typically bound to the tab
        key, but regardless to the actual keypress to which it is bound is
        *only* called in response to a user keypress.
        
        @param stc: the stc of interest
        @param linenum: the line number, or None to use the current line
        @param dedent_only: flag to indicate that indentation should only be
        removed, not added
        @return: the new cursor position, in case the cursor has moved as a
        result of the indention.
        """
        if linenum is None:
            linenum = stc.GetCurrentLine()
        if linenum == 0:
            # first line is always indented correctly
            return stc.GetCurrentPos()
        
        linestart = stc.PositionFromLine(linenum)

        # actual indention of current line
        indcol = stc.GetLineIndentation(linenum) # columns
        pos = stc.GetCurrentPos()
        indpos = stc.GetLineIndentPosition(linenum) # absolute character position
        col = stc.GetColumn(pos)
        self.dprint("linestart=%d indpos=%d pos=%d col=%d indcol=%d" % (linestart, indpos, pos, col, indcol))

        newind = self.findIndent(stc, linenum)
        if newind is None:
            return pos
        if dedent_only and newind > indcol:
            return pos
            
        # the target to be replaced is the leading indention of the
        # current line
        indstr = stc.GetIndentString(newind)
        self.dprint("linenum=%d indstr='%s'" % (linenum, indstr))
        stc.SetTargetStart(linestart)
        stc.SetTargetEnd(indpos)
        stc.ReplaceTarget(indstr)

        # recalculate cursor position, because it may have moved if it
        # was within the target
        after = stc.GetLineIndentPosition(linenum)
        self.dprint("after: indent=%d cursor=%d" % (after, stc.GetCurrentPos()))
        if pos < linestart:
            return pos
        newpos = pos - indpos + after
        if newpos < linestart:
            # we were in the indent region, but the region was made smaller
            return after
        elif pos < indpos:
            # in the indent region
            return after
        return newpos

    def processReturn(self, stc):
        """Add a newline and indent to the proper tab level.

        Indent to the level of the line above.  This uses the findIndent method
        to determine the proper indentation of the line about to be added,
        inserts the appropriate end-of-line characters, and indents the new
        line to that indentation level.
        
        @param stc: stc of interest
        """
        linesep = stc.getLinesep()
        
        stc.BeginUndoAction()
        # reindent current line (if necessary), then process the return
        #pos = stc.reindentLine()
        
        linenum = stc.GetCurrentLine()
        pos = stc.GetCurrentPos()
        col = stc.GetColumn(pos)
        #linestart = stc.PositionFromLine(linenum)
        #line = stc.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = stc.GetLineIndentation(linenum)

        self.dprint("format = %s col=%d ind = %d" % (repr(linesep), col, ind)) 

        stc.SetTargetStart(pos)
        stc.SetTargetEnd(pos)
        if col <= ind:
            newline = linesep + stc.GetIndentString(col)
        elif not pos:
            newline = linesep
        else:
            ind = self.findIndent(stc, linenum + 1)
            newline = linesep + stc.GetIndentString(ind)
        stc.ReplaceTarget(newline)
        stc.GotoPos(pos + len(newline))
        stc.EndUndoAction()

    def processTab(self, stc):
        stc.BeginUndoAction()
        pos = self.reindentLine(stc)
        stc.GotoPos(pos)
        stc.EndUndoAction()


class FoldingAutoindent(BasicAutoindent):
    """Experimental class to use STC Folding to reindent a line.
    """
    def findIndent(self, stc, linenum=None):
        """Reindent the specified line to the correct level.

        Given a line, use Scintilla's built-in folding to determine
        the indention level of the current line.
        """
        if linenum is None:
            linenum = stc.GetCurrentLine()
        linestart = stc.PositionFromLine(linenum)

        # actual indention of current line
        ind = stc.GetLineIndentation(linenum) # columns
        pos = stc.GetLineIndentPosition(linenum) # absolute character position

        # folding says this should be the current indention
        fold = stc.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE
        self.dprint("ind = %s (char num=%d), fold = %s" % (ind, pos, fold))
        return fold * stc.GetIndent()


class RegexAutoindent(BasicAutoindent):
    """Regex based autoindenter

    This is a flexible autointent module that uses regular expressions to
    determine the proper indentation level of a line of code based on the line
    of code above it.

    The original module was written by Anders Lund for
    the kate editor of the KDE project.  He has a U{blog
    entry<http://www.alweb.dk/blog/anders/autoindentation>} describing his
    thinking that led up to the creation of the code.
    """
    
    def __init__(self, reIndentAfter, reIndent, reUnindent, braces):
        """Create a regex autoindenter.
        
        Creates an instance of the regex autoindenter.  Since this code is
        based on the varindent module from KDE's Kate editor, it uses the same
        regular expressions as Kate to indent code.
        
        @param reIndentAfter: a regular expression used on the nearest line
        above the current line that has content.  If it matches, it will add
        indentation to the current line
        
        @param reIndent: regular expression used on the current line.  If it
        matches, indentation will be added to the current line.
        
        @param reUnindent: regular expression used on the current line.  If it
        matches, indentation is removed from the current line.
        
        @param braces: a list of braces used on the nearest line with content
        above the current.  When an opening brace appears without its matching
        closing brace, and indentation level is added to the current line.
        """
        if reIndentAfter:
            self.reIndentAfter = re.compile(reIndentAfter)
        else:
            self.reIndentAfter = None
        if reIndent:
            self.reIndent = re.compile(reIndent)
        else:
            self.reIndent = None
        if reUnindent:
            self.reUnindent = re.compile(reUnindent)
        else:
            self.reUnindent = None
        
        # list of brace types to handle.  Should be the opening brace, e.g.
        # '(', '[', or '{'
        if braces:
            self.couples = braces.replace(')', '(').replace(']', '[').replace('}', '{')
        else:
            self.couples = ''

    def findIndent(self, stc, linenum):
        """Determine the correct indentation for the line.
        
        This routine uses regular expressions to determine the indentation
        level of the line.
        
        @param linenum: current line number
        
        @param return: the number of columns to indent, or None to leave as-is
        """
        if linenum < 1:
            return None

        #// find the first line with content that is not starting with comment text,
        #// and take the position from that
        ln = linenum
        pos = 0
        above = ''
        while ln > 0:
            ln -= 1
            fc = stc.GetLineIndentPosition(ln)
            lc = stc.GetLineEndPosition(ln)
            self.dprint("ln=%d fc=%d lc=%d line=-->%s<--" % (ln, fc, lc, stc.GetLine(ln)))
            # skip blank lines
            if fc < lc:
                s = stc.GetStyleAt(fc)
                if stc.isStyleComment(s):
                    continue
                pos = stc.GetLineIndentation(ln)
                above = stc.GetTextRange(fc, lc)
                break

        #  // try 'couples' for an opening on the above line first. since we only adjust by 1 unit,
        #  // we only need 1 match.
        adjustment = 0
        if '(' in self.couples and self.coupleBalance(stc, ln, '(', ')') > 0:
            adjustment += 1
        elif '[' in self.couples and self.coupleBalance(stc, ln, '[', ']') > 0:
            adjustment += 1
        elif '{' in self.couples and self.coupleBalance(stc, ln, '{', '}') > 0:
            adjustment += 1
        
        #  // Try 'couples' for a closing on this line first. since we only adjust by 1 unit,
        #  // we only need 1 match. For unindenting, we look for a closing character
        #  // *at the beginning of the line*
        #  // NOTE Assume that a closing brace with the configured attribute on the start
        #  // of the line is closing.
        #  // When acting on processChar, the character isn't highlighted. So I could
        #  // either not check, assuming that the first char *is* meant to close, or do a
        #  // match test if the attrib is 0. How ever, doing that is
        #  // a potentially huge job, if the match is several hundred lines away.
        #  // Currently, the check is done.
        #  {
        #    KateTextLine::Ptr tl = doc->plainKateTextLine( line.line() );
        #    int i = tl->firstChar();
        #    if ( i > -1 )
        #    {
        #      QChar ch = tl->getChar( i );
        #      uchar at = tl->attribute( i );
        #      kdDebug(13030)<<"attrib is "<<at<<endl;
        #      if ( d->couples & Parens && ch == ')'
        #           && ( at == d->coupleAttrib
        #                || (! at && hasRelevantOpening( KateDocCursor( line.line(), i, doc ) ))
        #              )
        #         )
        #        adjustment--;
        #      else if ( d->couples & Braces && ch == '}'
        #                && ( at == d->coupleAttrib
        #                     || (! at && hasRelevantOpening( KateDocCursor( line.line(), i, doc ) ))
        #                   )
        #              )
        #        adjustment--;
        #      else if ( d->couples & Brackets && ch == ']'
        #                && ( at == d->coupleAttrib
        #                     || (! at && hasRelevantOpening( KateDocCursor( line.line(), i, doc ) ))
        #                   )
        #              )
        #        adjustment--;
        #    }
        #  }
        
        # Haven't figured out what that was for, so ignoring for now.
        
        
        #  // check if we should indent, unless the line starts with comment text,
        #  // or the match is in comment text
        # Here we look at the line above the current line
        if self.reIndentAfter:
            match = self.reIndentAfter.search(above)
            self.dprint(above)
            if match:
                self.dprint("reIndentAfter: found %s at %d" % (match.group(0), match.start(0)))
                adjustment += 1

        #  // else, check if this line should indent unless ...
        #  ktl = doc->plainKateTextLine( line.line() );
        #  if ( ! d->reIndent.isEmpty()
        #         && (matchpos = d->reIndent.search( doc->textLine( line.line() ) )) > -1
        #         && ! ISCOMMENT )
        #    adjustment++;
        fc = stc.GetLineIndentPosition(linenum)
        lc = stc.GetLineEndPosition(linenum)
        s = stc.GetStyleAt(fc)
        if self.reIndent and lc > fc and not stc.isStyleComment(s):
            text = stc.GetTextRange(fc, lc)
            match = self.reIndent.search(text)
            self.dprint(text)
            if match:
                self.dprint("reIndent: found %s at %d" % (match.group(0), match.start(0)))
                adjustment += 1
        
        #  // else, check if the current line indicates if we should remove indentation unless ...
        if self.reUnindent and lc > fc and not stc.isStyleComment(s):
            text = stc.GetTextRange(fc, lc)
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
    
    def coupleBalance(self, stc, ln, open, close):
        """Search the line to see if there are unmatched braces
        
        Search the line for unmatched braces given the open and close matching
        pair.  This takes into account the style of the document to make sure
        that the brace isn't in a comment or string.
        
        @param stc: the StyledTextCtrl instance
        @param ln: line number
        @param open: the opening brace character, e.g. "("
        @param close: the complimentary closing brace character, e.g. ")"
        
        @return: brace mismatch count: 0 for matching braces, positive for a
        surplus of opening braces, and negative for a surplus of closing braces
        """
        if ln < 0:
            return 0
        r = 0
        fc = stc.GetLineIndentPosition(ln)
        lc = stc.GetLineEndPosition(ln)
        line = stc.GetStyledText(fc, lc)
        self.dprint(repr(line))
        i = len(line)
        while i > 0:
            i -= 1
            s = line[i]
            i -= 1
            c = line[i]
            if c == open and not (stc.isStyleComment(s) and stc.isStyleString(s)):
                self.dprint("found %s at column %d" % (open, i/2))
                r += 1
            elif c == close and not (stc.isStyleComment(s) and stc.isStyleString(s)):
                self.dprint("found %s at column %d" % (close, i/2))
                r -= 1
        return r
            
        #
        #bool KateVarIndent::hasRelevantOpening( const KateDocCursor &end ) const
        #{
        #  KateDocCursor cur = end;
        #  int count = 1;
        #
        #  QChar close = cur.currentChar();
        #  QChar opener;
        #  if ( close == '}' ) opener = '{';
        #  else if ( close = ')' ) opener = '(';
        #  else if (close = ']' ) opener = '[';
        #  else return false;
        #
        #  //Move backwards 1 by 1 and find the opening partner
        #  while (cur.moveBackward(1))
        #  {
        #    if (cur.currentAttrib() == d->coupleAttrib)
        #    {
        #      QChar ch = cur.currentChar();
        #      if (ch == opener)
        #        count--;
        #      else if (ch == close)
        #        count++;
        #
        #      if (count == 0)
        #        return true;
        #    }
        #  }
        #
        #  return false;
        #}
        #
        #
        #//END KateVarIndent


class NullAutoindent(debugmixin):
    """No-op unindenter that doesn't change the indent level at all.
    """
    def findIndent(self, stc, linenum):
        """No-op that returns the current indent level."""
        return stc.GetLineIndentation(linenum)
    
    def reindentLine(self, stc, linenum=None, dedent_only=False):
        """No-op that doesn't change the current indent level."""
        return stc.GetCurrentPos()
    
    def processReturn(self, stc):
        """Add a newline only."""
        linesep = stc.getLinesep()
        stc.AddText(linesep)
    
    def processTab(self, stc):
        """Don't reindent but insert the equivalent of a tab character"""
        stc.AddText(stc.GetIndentString(stc.GetIndent()))
