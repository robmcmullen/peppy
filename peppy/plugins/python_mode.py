# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Python major mode.
"""

import os,struct
import keyword

import wx
import wx.stc

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.major import *
from peppy.fundamental import *
from peppy.actions.base import *
from peppy.paragraph import *

from peppy.lib.autoindent import BasicAutoindent
import peppy.lib.PyParse as PyParse


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

class PythonAutoindent(BasicAutoindent):
    def findIndent(self, stc, linenum):
        """Find proper indentation of the current Python source line.
        
        This uses IDLE's python parsing routine to find the indent level of the
        specified line based on the python code that comes before it.
        
        @param linenum: line number
        @return: integer indicating number of columns to indent.
        """
        indentwidth = stc.GetIndent()
        tabwidth = 87
        indent = stc.GetLineIndentation(linenum)
        y = PyParse.Parser(indentwidth, tabwidth)
        # FIXME: context line hack straight from IDLE
        for context in [50, 500, 5000000]:
            firstline = linenum - context
            if firstline < 0:
                firstline = 0
            start = stc.PositionFromLine(firstline)
            
            # end is the position before the first character of the line, so
            # we're looking at the code up to the start of the current line.
            end = stc.PositionFromLine(linenum)
            rawtext = stc.GetTextRange(start, end)
            
            # Handle two issues with this loop.  1: Remove comments that start
            # at column zero so they don't affect the indenting.  2: PyParse
            # is hardcoded for "\n" style newlines only, so by splitting the
            # lines here we can change whatever the newlines are into "\n"
            # characters.
            lines = []
            for line in rawtext.splitlines():
                if len(line) > 0:
                    if line[0] != '#':
                        lines.append(line)
            lines.append('') # include a blank line at the end
            rawtext = "\n".join(lines)
            y.set_str(rawtext)
            
            bod = y.find_good_parse_start(build_char_in_string_func(stc, start))
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
                s = stc.GetStyleAt(end)
                if s == 6 or s == 7:
                    # Inside a triple quoted string (TQS)
                    self.dprint("C_STRING_FIRST_LINE in TQS")
                    indentstr = y.get_base_indent_string()
                    indent = len(indentstr.expandtabs(tabwidth))
                else:
                    # after the first line of a string; do not indent at all
                    self.dprint("C_STRING_FIRST_LINE")
                pass
            elif c == PyParse.C_STRING_NEXT_LINES:
                # inside a string which started before this line;
                # just mimic the current indent
                #text.insert("insert", indent)
                s = stc.GetStyleAt(end)
                if s == 6 or s == 7:
                    # Inside a triple quoted string (TQS)
                    self.dprint("C_STRING_NEXT_LINES in TQS")
                    indentstr = y.get_base_indent_string()
                    indent = len(indentstr.expandtabs(tabwidth))
                else:
                    # FIXME: Does this ever happen without being in a TQS???
                    self.dprint("C_STRING_NEXT_LINES")
            elif c == PyParse.C_BRACKET:
                # line up with the first (if any) element of the
                # last open bracket structure; else indent one
                # level beyond the indent of the line with the
                # last open bracket
                self.dprint("C_BRACKET")
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
        
        # check some special cases to see if they line should be dedented by
        # a level
        before = stc.GetLineIndentPosition(linenum)
        style = stc.GetStyleAt(before)
        end = stc.GetLineEndPosition(linenum)
        cmd = stc.GetTextRange(before, end)
        #dprint("checking %s" % cmd)
        if linenum>0 and style==wx.stc.STC_P_WORD and (cmd.startswith('else') or cmd.startswith('elif') or cmd.startswith('except') or cmd.startswith('finally')):
            self.dprint("Found a dedent: %s" % cmd)
            if extra_data != "block dedent":
                # If we aren't right after a return or something that already
                # caused a dedent, dedent it
                indent -= indentwidth
        return indent

    def electricChar(self, stc, uchar):
        """Reindent the line and insert a newline when special chars are typed.
        
        For python mode, a colon should reindent the line (for example, after
        an else statement, it should dedent it one level)
        """
        if uchar == u':':
            pos = stc.GetCurrentPos()
            s = stc.GetStyleAt(pos)
            if not stc.isStyleComment(s) and not stc.isStyleString(s):
                stc.BeginUndoAction()
                start, end = stc.GetSelection()
                if start == end:
                    stc.AddText(uchar)
                else:
                    stc.ReplaceSelection(uchar)
                self.reindentLine(stc, dedent_only=True)
                stc.EndUndoAction()
                return True
        return False


class PythonParagraph(ParagraphInfo):
    def findParagraphStart(self, linenum):
        """Check to see if a previous line should be included in the
        paragraph match.
        """
        leader, line, trailer = self.s.splitCommentLine(self.s.GetLine(linenum))
        self.dprint(line)
        if leader != self.leader_pattern or len(line.strip())==0:
            return False
        stripped = line.strip()
        if stripped == "'''" or stripped == '"""':
            # triple quotes on line by themselves: don't include
            return False
        self.addStartLine(linenum, line)
        
        # Triple quotes embedded in the string are included, but then
        # we're done
        if line.startswith("'''") or line.startswith('"""'):
            return False
        return True
    
    def findParagraphEnd(self, linenum):
        """Check to see if a following line should be included in the
        paragraph match.
        """
        leader, line, trailer = self.s.splitCommentLine(self.s.GetLine(linenum))
        self.dprint(line)
        if leader != self.leader_pattern or len(line.strip())==0:
            return False
        stripped = line.strip()
        if stripped == "'''" or stripped == '"""':
            # triple quotes on line by themselves: don't include
            return False
        self.addEndLine(linenum, line)
        
        # A triple quote at the end of the line will be included in the
        # word wrap, but this ends the search
        if line.startswith("'''") or line.startswith('"""'):
            return False
        line = line.rstrip()
        if line.endswith("'''") or line.endswith('"""'):
            return False
        return True


class PythonMode(SimpleFoldFunctionMatchMixin, FundamentalMode):
    keyword='Python'
    icon='icons/py.png'
    regex="\.(py|pyx)$"
    
    fold_function_match = ["def ", "class "]

    default_classprefs = (
        )

    autoindent = PythonAutoindent()
    paragraph_cls = PythonParagraph
    
    def bangpathModificationHook(self, path):
        """Make sure the '-u' flag is included in the python argument"""
        if '-u' not in path:
            path += " -u"
        self.dprint(path)
        return path



class PythonErrorMode(FundamentalMode):
    keyword = "Python Error"
    icon='icons/error.png'
    
    default_classprefs = (
        BoolParam('line_numbers', False),
        )

    @classmethod
    def verifyMagic(cls, header):
        return header.find("Traceback (most recent call last):") >= 0
    
    @classmethod
    def isErrorMode(cls):
        return True


class PythonPlugin(IPeppyPlugin):
    def aboutFiles(self):
        return {'sample.py': _sample_file}
    
    def getMajorModes(self):
        yield PythonMode
        yield PythonErrorMode

    def getActions(self):
        return [SamplePython]
