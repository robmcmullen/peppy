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

_sample_file='''\
import time, sys
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
    print 'blah'
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
        s.ReplaceSelection(":")
        # folding info not automatically updated after a Replace, so
        # do it manually
        linestart = s.PositionFromLine(s.GetCurrentLine())
        s.Colourise(linestart, s.GetSelectionEnd())
        s.reindentLine()
        pass
        

class PythonReindentMixin(ReindentBase):
    def getReindentString(self, linenum, linestart, pos, before, col, ind):
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

        return self.GetIndentString(fold)


class PythonElectricReturnMixin(debugmixin):
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


class PythonSTC(PythonElectricReturnMixin, PythonReindentMixin, FundamentalSTC):
    pass

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
