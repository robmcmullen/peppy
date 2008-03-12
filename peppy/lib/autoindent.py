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

If you wanted to use this without peppy, you'd need to provide the methods
C{isStyleComment} and C{isStyleString} to the stc of interest.  They
should return true when the style passed to them is a comment or string,
respectively.  See the implementation of them in L{peppy.editra.stcmixin}
"""

import os, re
from peppy.debug import *


class RegexAutoindent(debugmixin):
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

    def getReindentColumn(self, stc, linenum):
        """Determine the correct indentation of the first not-blank character
        of the line.
        
        This routine should be overridden in subclasses; this provides a
        default implementation of line reindentatiot that simply reindents the
        line to the indentation of the line above it.  Subclasses with more
        specific knowledge of the text being edited will be able to use the
        syntax of previous lines to indent the line properly.
        
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
