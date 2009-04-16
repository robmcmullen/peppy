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
from cStringIO import StringIO

import wx.stc
from peppy.debug import *


class BasicAutoindent(debugmixin):
    """Simple autoindent that indents the line to the level of the line above it.
    
    This is about the bare minimum indenter.  It just looks at the line above
    it and reports the indent level of that line.  No effort is made to look
    at syntax or anything.  Simple.
    """
    
    # Scintilla always reports a fold of zero on the last line, so if
    # subclasses use folding to determine the indent, this should be set to
    # True so that processReturn will add an extra newline character if it's
    # at the end of the file.
    folding_last_line_bug = False
    
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
            stc.ReplaceTarget(linesep)
            pos += len(linesep)
            end = min(pos + 1, stc.GetTextLength())
            
            # Scintilla always returns a fold level of zero on the last line,
            # so when trying to indent the last line, must add a newline
            # character.
            if pos == end and self.folding_last_line_bug:
                stc.AddText("\n")
                end = stc.GetTextLength()
            
            # When we insert a new line, the colorization isn't always
            # immediately updated, so we have to force that here before
            # calling findIndent to guarantee that the new line will have the
            # correct fold property set.
            stc.Colourise(stc.PositionFromLine(linenum), end)
            stc.SetTargetStart(pos)
            stc.SetTargetEnd(pos)
            ind = self.findIndent(stc, linenum + 1)
            self.dprint("pos=%d ind=%d fold=%d" % (pos, ind, (stc.GetFoldLevel(linenum+1)&wx.stc.STC_FOLDLEVELNUMBERMASK) - wx.stc.STC_FOLDLEVELBASE))
            newline = stc.GetIndentString(ind)
        stc.ReplaceTarget(newline)
        stc.GotoPos(pos + len(newline))
        stc.EndUndoAction()

    def processTab(self, stc):
        stc.BeginUndoAction()
        self.dprint()
        pos = self.reindentLine(stc)
        stc.GotoPos(pos)
        stc.EndUndoAction()
    
    def electricChar(self, stc, uchar):
        """Autoindent in response to a special character

        This is a hook to cause an autoindent on a particular character.
        Note that the hook can do more than that -- it can insert or delete
        characters as well.
        
        This takes its name from emacs, where "electric" meant that something
        else happened other than simply inserting the char.
        
        @param stc: stc instance
        
        @param uchar: unicode character that was just typed by the user (note
        that it hasn't been inserted into the document yet.)
        
        @return: True if this method handled the character and the text
        was modified; False if the calling event handler should handle the
        character.
        """
        return False
    
    def electricDelete(self, stc):
        """Delete the next character
        
        This hook allows more complex processing of the Delete key than the
        default which is to delete the character after the cursor.
        """
        stc.CmdKeyExecute(wx.stc.STC_CMD_CLEAR)
    
    def electricBackspace(self, stc):
        """Delete the previous character
        
        This hook allows more complex processing of the Backspace key than the
        default which is to delete the character before the cursor.
        """
        stc.CmdKeyExecute(wx.stc.STC_CMD_DELETEBACK)


class FoldingAutoindent(BasicAutoindent):
    """Experimental class to use STC Folding to reindent a line.
    """
    folding_last_line_bug = True
    
    def getFold(self, stc, linenum):
        return stc.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE

    def getPreviousText(self, stc, linenum):
        """Find the text above the line with the same fold level.
        
        """
        fold = self.getFold(stc, linenum)
        ln = linenum - 1
        fc = lc = stc.GetLineEndPosition(ln)
        above = ''
        while ln > 0:
            f = self.getFold(stc, ln)
            if f != fold:
                above = stc.GetTextRange(fc, lc)
                break
            fc = stc.PositionFromLine(ln)
            ln -= 1
        return above

    def getFoldSectionStart(self, stc, linenum):
        """Find the line number of the text above the given line that has the
        same fold level.
        
        Searching from the given line number toward the start of the file,
        find the set of lines that have the same fold level as the given
        line.  Once the fold level changes, we know that we're done searching
        because there's no way that any indentation for the given line can be
        affected by a separate block of code

        @return: the line number of the start of the fold section
        """
        fold = self.getFold(stc, linenum)
        ln = linenum
        while ln > 0:
            f = self.getFold(stc, ln - 1)
            if f != fold:
                break
            ln -= 1
        return ln
    
    def getNonCodeStyles(self, stc):
        """Return a list of styling integers that indicate characters that are
        outside the normal code flow.
        
        Character styles that are outside code flow are strings, comments,
        preprocessor statements, and stuff that should be ignored when
        indenting.
        """
        styles = []
        styles.extend(stc.getStringStyles())
        styles.extend(stc.getCommentStyles())
        #self.dprint(styles)
        return styles
    
    def getCodeChars(self, stc, ln, lc=-1):
        """Get a version of the given line with all non code chars blanked out.
        
        This function blanks out all non-code characters (comments, strings,
        etc) from the line and returns a copy of the interesting stuff.
        
        @param stc: stc of interest
        @param ln: line number
        @param lc: optional integer specifying the last position on the
        line to consider
        """
        fc = stc.PositionFromLine(ln)
        if lc < 0:
            lc = stc.GetLineEndPosition(ln)
        if lc < fc:
            # FIXME: fail hard during development
            raise IndexError("bad line specification for line %d: fc=%d lc=%d" % (ln, fc, lc))
        
        mask = (2 ** stc.GetStyleBits()) - 1
        
        out = []

        line = stc.GetStyledText(fc, lc)
        self.dprint(repr(line))
        i = len(line)
        
        # replace all uninteresting chars with blanks
        skip = self.getNonCodeStyles(stc)
        while i > 0:
            i -= 1
            s = ord(line[i]) & mask
            i -= 1
            if s in skip:
                c = ' '
            else:
                c = line[i]
            out.append(c)
        
        # Note that we assembled the string in reverse, so flip it around
        out = ''.join(reversed(out))
        return out

    def getLastNonWhitespaceChar(self, stc, pos):
        """Working backward, find the closest non-whitespace character
        
        @param stc: stc of interest
        @param pos: boundary position from which to start looking backwards
        @return: tuple of the matching char and the position
        """
        found = ''
        skip = self.getNonCodeStyles(stc)
        while pos > 0:
            check = pos - 1
            c = unichr(stc.GetCharAt(check))
            s = stc.GetStyleAt(check)
            #dprint("check=%d char='%s'" % (check, c))
            
            # Comment or string terminates the search and will return with the
            # character after the last comment/string char.
            if s in skip:
                break
            
            found = c
            pos = check
            if not c.isspace():
                break
        return (found, pos)

    def getBraceMatch(self, text, open=u'(', close=u')'):
        """Search the text to see if there are unmatched braces
        
        Search the line for unmatched braces given the open and close matching
        pair.  This does not look at styling information; it assumes that
        L{getCodeChars} has been called before this.
        
        @param text: line number
        @param open: the opening brace character, e.g. "("
        @param close: the complimentary closing brace character, e.g. ")"
        
        @return: brace mismatch count: 0 for matching braces, positive for a
        surplus of opening braces, and negative for a surplus of closing braces
        """
        r = 0
        for c in text:
            if c == open:
                r += 1
            elif c == close:
                r -= 1
        return r

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


class CStyleAutoindent(FoldingAutoindent):
    """Use the STC Folding to reindent a line in a C-like mode.
    
    This autoindenter uses the built-in Scintilla folding to determine the
    correct indent level for C-like modes (C, C++, Java, Javascript, etc.)
    plus a bunch of heuristics to handle things that Scintilla doesn't.
    """
    debuglevel = 0
    
    def __init__(self, reIndentAfter=None, reIndent=None, reUnindent=None):
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
            self.reIndentAfter = re.compile(r'^(?!.*;\s*//).*[^\s;{}]\s*$')
        if reIndent:
            self.reIndent = re.compile(reIndent)
        else:
            self.reIndent = None
        if reUnindent:
            self.reUnindent = re.compile(reUnindent)
        else:
            self.reUnindent = None
        self.reStatement = re.compile(r'^([^\s]+)\s*(\(.+\)|.+)?$')
        self.reCase = re.compile(r'^\s*(case|default).*:\s*$')
        self.reClassAttrScope = re.compile(r'^\s*(public|private).*:$')
        self.reBreak = re.compile(r'^\s*break\s*;\s*$')
        self.reLabel = re.compile(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*:((?!:)|$)')
    
    def getNonCodeStyles(self, stc):
        """Return a list of styling integers that indicate characters that are
        outside the normal code flow.
        
        Character styles that are outside code flow are strings, comments,
        preprocessor statements, and stuff that should be ignored when
        indenting.
        """
        styles = []
        styles.extend(stc.getStringStyles())
        styles.extend(stc.getCommentStyles())
        # add preprocessor styles for C-like modes -- everything that uses the
        # C syntax highlighter should also use the STC_C_PREPROCESSOR token
        styles.append(wx.stc.STC_C_PREPROCESSOR)
        #self.dprint(styles)
        return styles
    
    def getBraceOpener(self, stc, linenum):
        """Find the statement related to the brace's opening.
        
        If a block of code is related to a reserved keyword, like
        
        switch (blah) {
            case 0:
                stuff;
        }
        
        return the keyword so it can be used to further indent the contents.

        @return: the keyword of interest
        """
        fold = self.getFold(stc, linenum)
        self.dprint("linenum=%d fold=%d" % (linenum, fold))
        ln = linenum
        statement = ''
        first = True
        parens = False
        while ln >= 0:
            f = self.getFold(stc, ln)
            if f != fold:
                break
            line = self.getCodeChars(stc, ln).strip()
            self.dprint(line)
            ln -= 1
            if not line:
                continue
            statement = line + statement
            if first:
                if statement.endswith('{'):
                    statement = statement[:-1].strip()
                    
                if statement.endswith(';'):
                    # A complete statement before an opening brace means it's
                    # an anonymous block, so the statement before doesn't
                    # relate to the block itself.
                    break
                if ')' in statement:
                    parens = True
                else:
                    break
                first = False
            
            # Parens must match to form a complete statement
            if parens:
                if self.getBraceMatch(statement) == 0:
                    break
        if statement:
            match = self.reStatement.match(statement)
            if match:
                statement = match.group(1)
        return statement
    
    def isInsideStatement(self, stc, pos):
        """Find out if the position is inside a statement
        
        Being inside a statement means that the position is after an opening
        paren and the matching close paran either doesn't exist yet or is
        after the position.
        
        @return: True if pos is after an unbalanced amount of opening parens
        """
        linenum = stc.LineFromPosition(pos)

        start = self.getFoldSectionStart(stc, linenum)
        self.dprint("fold start=%d, linenum=%d" % (start, linenum))
        text = self.getCodeChars(stc, start, pos)
        parens = self.getBraceMatch(text)
        self.dprint("text=%s, parens=%d" % (text, parens))
        return parens != 0
    
    def findIndent(self, stc, linenum=None):
        """Reindent the specified line to the correct level.

        Given a line, use Scintilla's built-in folding to determine
        the indention level of the current line.
        """
        if linenum is None:
            linenum = stc.GetCurrentLine()
        linestart = stc.PositionFromLine(linenum)

        # actual indention of current line
        col = stc.GetLineIndentation(linenum) # columns
        pos = stc.GetLineIndentPosition(linenum) # absolute character position

        # folding says this should be the current indention
        fold = (stc.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK) - wx.stc.STC_FOLDLEVELBASE
        c = stc.GetCharAt(pos)
        s = stc.GetStyleAt(pos)
        indent = stc.GetIndent()
        partial = 0
        self.dprint("col=%d (pos=%d), fold=%d char=%s" % (col, pos, fold, repr(chr(c))))
        if c == ord('}'):
            # Scintilla doesn't automatically dedent the closing brace, so we
            # force that here.
            fold -= 1
        elif c == ord('{'):
            # Opening brace on a line by itself always stays at the fold level
            pass
        elif c == ord('#') and s == 9:
            # Force preprocessor directives to start at column zero
            fold = 0
        else:
            start = self.getFoldSectionStart(stc, linenum)
            opener = self.getBraceOpener(stc, start-1)
            self.dprint(opener)
            
            # First, try to match on the current line to see if we know enough
            # about it to figure its indent level
            matched = False
            line = self.getCodeChars(stc, linenum)
            if opener == "switch":
                # case statements are partially dedented relative to the
                # scintilla level
                if self.reCase.match(line):
                    matched = True
                    partial = - (indent / 2)
            elif opener == "class":
                # public/private/protected statements are partially dedented
                # relative to the scintilla level
                if self.reClassAttrScope.match(line):
                    matched = True
                    partial = - (indent / 2)
            
            # labels are matched after case statements to prevent the
            # 'default:' label from getting confused with a regular label
            if not matched and self.reLabel.match(line):
                fold = 0
                matched = True
            
            # If we can't determine the indent level when only looking at
            # the current line, start backing up to find the first non blank
            # statement above the line.  We then look to see if we should
            # indent relative to that statement (e.g.  if the statement is a
            # continuation) or relative to the fold level supplied by scintilla
            if not matched:
                for ln in xrange(linenum - 1, start - 1, -1):
                    line = self.getCodeChars(stc, ln)
                    self.dprint(line)
                    if not line.strip() or self.reLabel.match(line):
                        continue
                    if opener == "switch":
                        if self.reCase.match(line):
                            # a case statement will be interpreted as a continuation
                            break
                    if self.reIndentAfter.match(line):
                        self.dprint("continuation")
                        fold += 1
                    else:
                        self.dprint("terminated statement")
                    break

        return (fold * indent) + partial
    
    def electricChar(self, stc, uchar):
        """Reindent the line and insert a newline when special chars are typed.
        
        Like emacs, a semicolon or curly brace causes the line to be reindented
        and the next line to be indented to the correct column.
        
        @param stc: stc instance
        
        @param uchar: unicode character that was just typed by the user (note
        that it hasn't been inserted into the document yet.)
        
        @return: True if this method handled the character and the text
        was modified; False if the calling event handler should handle the
        character.
        """
        implicit_return = True
        
        if uchar == u';' or uchar == u':' or uchar == '{' or uchar == '}':
            pos = stc.GetCurrentPos()
            s = stc.GetStyleAt(pos)
            if not stc.isStyleComment(s) and not stc.isStyleString(s):
                if uchar == u':':
                    # FIXME: currently only process the : if the current
                    # line is a case statement.  Emacs also indents labels
                    # and namespace operators with a :: by checking if the
                    # last character on the previous line is a : and if so
                    # collapses the current line with the previous line and
                    # reindents the new line
                    linenum = stc.GetCurrentLine()
                    line = self.getCodeChars(stc, linenum, pos) + ":"
                    if not self.reCase.match(line) and not self.reClassAttrScope.match(line):
                        c, prev = self.getLastNonWhitespaceChar(stc, pos)
                        if c == u':':
                            # Found previous ':', so make it a double colon
                            stc.SetSelection(prev + 1, pos)
                            #dprint("selection: %d - %d" % (prev + 1, pos))
                        implicit_return = False
                elif uchar == u';':
                    # Don't process the semicolon if we're in the middle of an
                    # open statement
                    if self.isInsideStatement(stc, pos):
                        return False
                stc.BeginUndoAction()
                start, end = stc.GetSelection()
                if start == end:
                    stc.AddText(uchar)
                else:
                    stc.ReplaceSelection(uchar)
                
                # Always reindent the line, but only process a return if needed
                self.processTab(stc)
                if implicit_return:
                    self.processReturn(stc)
                
                stc.EndUndoAction()
                return True
        return False

    def electricDelete(self, stc):
        """Delete all whitespace after the cursor unless in a string or comment
        """
        start, end = stc.GetSelection()
        if start != end:
            stc.ReplaceSelection("")
            return
        pos = stc.GetCurrentPos()
        s = stc.GetStyleAt(pos)
        if stc.isStyleComment(s) or stc.isStyleString(s):
            stc.CmdKeyExecute(wx.stc.STC_CMD_CLEAR)
        else:
            self.dprint("deleting from pos %d" % pos)
            end = pos
            while end < stc.GetLength():
                c = stc.GetCharAt(end)
                if c == ord(' ') or c == ord('\t') or c == 10 or c == 13:
                    end += 1
                else:
                    break
            if end > pos:
                stc.SetTargetStart(pos)
                stc.SetTargetEnd(end)
                stc.ReplaceTarget('')
            else:
                stc.CmdKeyExecute(wx.stc.STC_CMD_CLEAR)

    def electricBackspace(self, stc):
        """Delete all whitespace before the cursor unless in a string or comment
        """
        start, end = stc.GetSelection()
        if start != end:
            stc.ReplaceSelection("")
            return
        pos = stc.GetCurrentPos()
        if pos <= 0:
            return
        s = stc.GetStyleAt(pos - 1)
        if stc.isStyleComment(s) or stc.isStyleString(s):
            stc.CmdKeyExecute(wx.stc.STC_CMD_DELETEBACK)
        else:
            self.dprint("backspace from pos %d" % pos)
            start = pos
            while start > 0:
                c = stc.GetCharAt(start - 1)
                if c == ord(' ') or c == ord('\t') or c == 10 or c == 13:
                    start -= 1
                else:
                    break
            if start < pos:
                stc.SetTargetStart(start)
                stc.SetTargetEnd(pos)
                stc.ReplaceTarget('')
            else:
                stc.CmdKeyExecute(wx.stc.STC_CMD_DELETEBACK)



class RegexAutoindent(BasicAutoindent):
    """Regex based autoindenter

    This is a flexible autointent module that uses regular expressions to
    determine the proper indentation level of a line of code based on the line
    of code above it.

    The original module was written by Anders Lund for
    the kate editor of the KDE project.  He has a U{blog
    entry<http://www.alweb.dk/blog/anders/autoindentation>} describing his
    thinking that led up to the creation of the code.
    
    The source code for the autoindenting part of Kate is actually in the
    L{kpart<http://websvn.kde.org/branches/KDE/3.5/kdelibs/kate/part/kateautoindent.cpp?revision=620408&view=markup>}
    section of KDE, not with the main Kate application.
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
    
    def electricChar(self, stc, uchar):
        """No electric chars in Null autoindenter."""
        return False
    
    def electricDelete(self, stc):
        """Defaults to standard delete processing in Null autoindenter."""
        stc.CmdKeyExecute(wx.stc.STC_CMD_CLEAR)
    
    def electricBackspace(self, stc):
        """Defaults to standard backspace processing in Null autoindenter."""
        stc.CmdKeyExecute(wx.stc.STC_CMD_DELETEBACK)
