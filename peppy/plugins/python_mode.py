# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Python major mode.
"""

import os,struct
import keyword

import wx
import wx.stc

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.major import *
from peppy.fundamental import *
from peppy.actions.base import *

import idlelib.PyParse as PyParse


_sample_file='''\
import os, sys, time
"""
Sample file to demonstrate running a python script from the editor.
"""

print "Working dir = %s" % os.getcwd()

# Default to 100 repetitions
num = 100

# If we have given it an argument using the Run With Args command, process
# it here
if len(sys.argv) > 1:
    num = int(sys.argv[1])
print "Number of times to loop: %d" % num

# Perform the loop
for x in range(num):
    print 'loop %d: blah' % x
    time.sleep(1)
'''

class SamplePython(SelectAction):
    name = "&Open Sample Python"
    tooltip = "Open a sample Python file"
    default_menu = "&Help/Samples"

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:sample.py")


class ElectricColon(TextModificationAction):
    name = "Electric Colon"
    tooltip = "Indent the current line when a colon is pressed"
    key_bindings = {'default': 'S-;',} # FIXME: doesn't work to specify ':'

    @classmethod
    def worksWithMajorMode(cls, mode):
        return mode.keyword == 'Python'

    def action(self, index=-1, multiplier=1):
        s = self.mode.stc
        style = s.GetStyleAt(s.GetSelectionEnd())
        s.BeginUndoAction()
        s.ReplaceSelection(":")
        if s.isStyleComment(style) or s.isStyleString(style):
            self.dprint("within comment or string: not indenting")
            pass
        else:
            # folding info not automatically updated after a Replace, so
            # do it manually
            linestart = s.PositionFromLine(s.GetCurrentLine())
            s.Colourise(linestart, s.GetSelectionEnd())
            s.reindentLine(dedent_only=True)
        s.EndUndoAction()

class PythonFoldingReindentMixin(ReindentBase):
    def getReindentColumn(self, linenum, linestart, pos, before, col, ind):
        """Reindent the specified line to the correct level.

        Given a line, use Scintilla's built-in folding and a whole
        bunch of heuristics based on the previous lines to determine
        the indention level of the current line.
        """
        # folding says this should be the current indention.  The
        # limitation of Scintilla's folding logic, though, is that
        # folding tells the indention position of the line as it is,
        # not as it should be for pythonic consistancy.  For instance,
        # using GetFoldColumn on each line in the following code:
        #
        # if blah:
        #      stuff = 0
        #          things = 1
        #
        # reports fold levels of 0, 4, and 8, even though for valid
        # python the 3rd line should be at fold level 4.  So, we're
        # forced to add a whole bunch of additional logic to figure
        # out which indention level should be used.
        fold = self.GetFoldColumn(linenum)

        # get indention of previous (non-blank) line
        prev, prevline = self.GetPrevLineIndentation(linenum)
        if fold>=prev:
            # OK, line is indented with respect to the previous line,
            # so we need to honor the fact that it is indented.
            # However, it may still be indented too much or too
            # little.

            # FIXME: this doesn't handle comments
            line = self.GetLine(prevline).rstrip()
            print "previous line %d = %s" % (prevline, line)
            if line.endswith(':'):
                fold = prev + self.GetIndent()
            else:
                fold = prev
        elif fold > prev - self.GetIndent():
            # line is partially indented, but not at the usual indent
            # level.  We force this to be indented to match the indent
            # level
            fold = prev

        # get line without indention
        line = self.GetLine(linenum)[before-linestart:]
        dprint(line)

        # the keywords elif or else should be unindented if the
        # previous line is at the same level
        style = self.GetStyleAt(before)
        dprint("linenum=%d cursor=%d before=%d style=%d ind=%s fold=%s line=%s" % (linenum, pos, before, style, ind, fold, repr(line)))
        if linenum>0 and style==wx.stc.STC_P_WORD and (line.startswith('else') or line.startswith('elif') or line.startswith('except') or line.startswith('finally')):
            dprint("prev = %s" % prev)
            if prev == ind:
                fold-=self.GetIndent()

        return fold


class PyPEElectricReturnMixin(debugmixin):
    debuglevel = 0
    
    def findIndent(self, linenum):
        linestart = self.PositionFromLine(linenum)
        lineend = self.GetLineEndPosition(linenum)
        line = self.GetTextRange(linestart, lineend)
        ind = self.GetLineIndentation(linenum)
        assert self.dprint("line (%d-%d) = %s" % (linestart, lineend, repr(line)))
        xtra = 0
        colon = ord(':')
        
        if (line.find(':')>-1):
            assert self.dprint("found a ':'")
            for i in xrange(linestart, lineend):
                styl = self.GetStyleAt(i)
                assert self.dprint("pos=%d char=%s style=%d" % (i, repr(self.GetCharAt(i)), styl))
                if not xtra:
                    if (styl==10) and (self.GetCharAt(i) == colon):
                        xtra = 1
                elif (styl == 1):
                    assert self.dprint("in comment")
                    #it is a comment, ignore the character
                    pass
                elif (styl == 0) and (self.GetCharAt(i) in [ord(i) for i in ' \t\r\n']):
                    #is not a comment, but is the space before a comment
                    #or the end of a line, ignore the character
                    pass
                else:
                    #this is not a comment or some innocuous other character
                    #this is a docstring or otherwise, no additional indent
                    xtra = 0
                    #commenting the break fixes stuff like this
                    # for i in blah[:]:
                    #break
            if xtra:
                #This deals with ending single and multi-line definitions properly.
                while linenum >= 0:
                    found = []
                    for i in ['def', 'class', 'if', 'else', 'elif', 'while',
                            'for', 'try', 'except', 'finally', 'with', 'cdef']:
                        a = line.find(i)
                        if (a > -1):
                            found.append(a)
                    #assert self.dprint('fnd', found)
                    if found: found = min(found)
                    else:     found = -1
                    if (found > -1) and\
                    (self.GetStyleAt(self.GetLineEndPosition(linenum)-len(line)+found)==5) and\
                    (self.GetLineIndentation(linenum) == found):
                        ind = self.GetLineIndentation(linenum)
                        break
                    linenum -= 1
                    line = self.GetLine(linenum)
        #if we were to do indentation for ()[]{}, it would be here
        if not xtra:
            #yep, right here.
            fnd = 0
            for i in "(){}[]":
                if (line.find(i) > -1):
                    fnd = 1
                    break
            if fnd:
                seq = []
                #assert self.dprint("finding stuff")
                for i in "(){}[]":
                    a = line.find(i)
                    start = 0
                    while a > -1:
                        start += a+1
                        if self.GetStyleAt(start+linestart-1)==10:
                            seq.append((start, i))
                        a = line[start:].find(i)
                seq.sort()
                cl = {')':'(', ']': '[', '}': '{',
                    '(':'',  '[': '',  '{': ''}
                stk = []
                #assert self.dprint("making tree")
                for po, ch in seq:
                    #assert self.dprint(ch,)
                    if not cl[ch]:
                        #standard opening
                        stk.append((po, ch))
                    elif stk:
                        if cl[ch] == stk[-1][1]:
                            #proper closing of something
                            stk.pop()
                        else:
                            #probably a syntax error
                            #does it matter what is done?
                            stk = []
                            break
                    else:
                        # Probably closing something on another line,
                        # should probably find the indent level of the
                        # opening, but that would require checking
                        # multiple previous items for the opening
                        # item.  single-line dedent.
                        stk = []
                        break
                if stk:
                    #assert self.dprint("stack remaining", stk)
                    ind = stk[-1][0]
        if not xtra:
            ls = line.lstrip()
            if (ls[:6] == 'return') or (ls[:4] == 'pass') or (ls[:5] == 'break') or (ls[:8] == 'continue'):
                xtra = -1

        dprint("indent = %d" % int(ind+xtra*self.GetIndent()))
        return max(ind+xtra*self.GetIndent(), 0)


class IDLEReindentMixin(ReindentBase):
    def getReindentColumn(self, linenum, linestart, pos, before, col, ind):
        """Reindent the specified line to the correct level.

        Given a line, IDLE's parsing module to find the correct indention level
        """
        # Use the current line number, which will find the indention based on
        # the previous line
        indent, extra = self.findIndent(linenum, True)
        
        # The text begins at indpos; check some special cases to see if there
        # should be a dedent
        style = self.GetStyleAt(before)
        end = self.GetLineEndPosition(linenum)
        cmd = self.GetTextRange(before, end)
        #dprint("checking %s" % cmd)
        if linenum>0 and style==wx.stc.STC_P_WORD and (cmd.startswith('else') or cmd.startswith('elif') or cmd.startswith('except') or cmd.startswith('finally')):
            #dprint("Found a dedent: %s" % cmd)
            if extra != "block dedent":
                # If we aren't right after a return or something that already
                # caused a dedent, dedent it
                indent -= self.GetIndent()
        return indent

# Helper functions required by IDLE's PyParse routine
def is_char_in_string(stc, pos):
    """Return True if the position is within a string"""
    style = stc.GetStyleAt(pos)
    #dprint("style %d at pos %d" % (style, pos))
    if style == 3 or style == 7 or style == 6 or style == 4:
        return True
    return False

def build_char_in_string_func(stc, startindex):
    """Factory to create a specific is_char_in_string function that also
    includes an offset.
    """
    def inner(offset, _startindex=startindex, _stc=stc, _icis=is_char_in_string):
        #dprint("offset=%d, startindex=%d" % (offset, _startindex))
        return _icis(_stc, _startindex + offset)
    return inner

class IDLEElectricReturnMixin(debugmixin):
    debuglevel = 0
    
    def findIndent(self, linenum, extra=None):
        """Find what indentation of the line should be based on previous lines
        
        Gets indentation of what the line containing pos should be, not taking
        into account any dedenting as a result of compound blocks like else,
        finally, etc.
        
        linenum: line number to find indentation
        
        extra: include extra syntactic info as a result of the parsing; whether
        the previous block included a return and was dedented, for instance.
        """
        indentwidth = self.GetIndent()
        tabwidth = 87
        indent = self.GetLineIndentation(linenum)
        y = PyParse.Parser(indentwidth, tabwidth)
        # FIXME: context line hack straight from IDLE
        for context in [50, 500, 5000000]:
            firstline = linenum - context
            if firstline < 0:
                firstline = 0
            start = self.PositionFromLine(firstline)
            end = self.PositionFromLine(linenum)
            rawtext = self.GetTextRange(start, end)+"\n"
            y.set_str(rawtext)
            bod = y.find_good_parse_start(build_char_in_string_func(self, start))
            if bod is not None or firstline == 0:
                break
        #dprint(rawtext)
        self.dprint("bod = %s" % bod)
        y.set_lo(bod or 0)

        c = y.get_continuation_type()
        self.dprint("continuation type: %s" % c)
        extra_data = None
        if c != PyParse.C_NONE:
            # The current stmt hasn't ended yet.
            if c == PyParse.C_STRING_FIRST_LINE:
                # after the first line of a string; do not indent at all
                print "C_STRING_FIRST_LINE"
                pass
            elif c == PyParse.C_STRING_NEXT_LINES:
                # inside a string which started before this line;
                # just mimic the current indent
                #text.insert("insert", indent)
                print "C_STRING_NEXT_LINES"
                pass
            elif c == PyParse.C_BRACKET:
                # line up with the first (if any) element of the
                # last open bracket structure; else indent one
                # level beyond the indent of the line with the
                # last open bracket
                print "C_BRACKET"
                #self.reindent_to(y.compute_bracket_indent())
                indent = y.compute_bracket_indent()
            elif c == PyParse.C_BACKSLASH:
                # if more than one line in this stmt already, just
                # mimic the current indent; else if initial line
                # has a start on an assignment stmt, indent to
                # beyond leftmost =; else to beyond first chunk of
                # non-whitespace on initial line
                if y.get_num_lines_in_stmt() > 1:
                    pass
                else:
                    indent = y.compute_backslash_indent()
            else:
                assert 0, "bogus continuation type %r" % (c,)
                
        else:
            # This line starts a brand new stmt; indent relative to
            # indentation of initial line of closest preceding
            # interesting stmt.
            indentstr = y.get_base_indent_string()
            indent = len(indentstr.expandtabs(tabwidth))
        
            if y.is_block_opener():
                self.dprint("block opener")
                indent += indentwidth
                extra_data = "block opener"
            elif indent and y.is_block_closer():
                self.dprint("block dedent")
                indent = ((indent-1)//indentwidth) * indentwidth
                extra_data = "block dedent"
        self.dprint("indent = %d" % indent)
        if extra:
            return (indent, extra_data)
        return indent


class PythonParagraphMixin(StandardParagraphMixin):
    def findParagraphStart(self, linenum, info):
        """Check to see if a previous line should be included in the
        paragraph match.
        """
        leader, line, trailer = self.splitCommentLine(self.GetLine(linenum))
        self.dprint(line)
        if leader != info.leader_pattern or len(line.strip())==0:
            return False
        stripped = line.strip()
        if stripped == "'''" or stripped == '"""':
            # triple quotes on line by themselves: don't include
            return False
        info.addStartLine(linenum, line)
        
        # Triple quotes embedded in the string are included, but then
        # we're done
        if line.startswith("'''") or line.startswith('"""'):
            return False
        return True
    
    def findParagraphEnd(self, linenum, info):
        """Check to see if a following line should be included in the
        paragraph match.
        """
        leader, line, trailer = self.splitCommentLine(self.GetLine(linenum))
        self.dprint(line)
        if leader != info.leader_pattern or len(line.strip())==0:
            return False
        stripped = line.strip()
        if stripped == "'''" or stripped == '"""':
            # triple quotes on line by themselves: don't include
            return False
        info.addEndLine(linenum, line)
        
        # A triple quote at the end of the line will be included in the
        # word wrap, but this ends the search
        if line.startswith("'''") or line.startswith('"""'):
            return False
        line = line.rstrip()
        if line.endswith("'''") or line.endswith('"""'):
            return False
        return True


class PythonSTC(IDLEElectricReturnMixin, IDLEReindentMixin,
                PythonParagraphMixin, FundamentalSTC):
                    
    def isStyleString(self, style):
        return style == 3 or style == 7 or style == 6 or style == 4
        
    def isStyleComment(self, style):
        return style == 1

class PythonMode(JobControlMixin, FundamentalMode):
    keyword='Python'
    icon='icons/py.png'
    regex="\.(py|pyx)$"

    stc_viewer_class = PythonSTC

    default_classprefs = (
        )


class PythonPlugin(IPeppyPlugin):
    def aboutFiles(self):
        return {'sample.py': _sample_file}
    
    def getMajorModes(self):
        yield PythonMode

    def getActions(self):
        return [SamplePython, ElectricColon]
