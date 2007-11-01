import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcinterface import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *
from peppy.debug import *

import PyParse as PyParse

from nose.tools import *

def is_char_in_string(stc, pos):
    style = stc.GetStyleAt(pos)
    if style == 3 or style == 7 or style == 6 or style == 4:
        return True
    return False

def build_char_in_string_func(stc, startindex):
    def inner(offset, _startindex=startindex, _stc=stc, _icis=is_char_in_string):
        return _icis(_stc, _startindex + offset)
    return inner

def getIndentString(num):
    return num*" "

def getIdleIndent(stc, linenum):
    """Gets indentation of what the line containing pos should be, not taking
    into account any dedenting as a result of compound blocks like else,
    finally, etc.
    """
    indentwidth = 4
    tabwidth = 8
    indent = stc.GetLineIndentation(linenum)
    y = PyParse.Parser(indentwidth, tabwidth)
    # FIXME: context line hack straight from IDLE
    for context in [50, 500, 5000000]:
        firstline = linenum - context
        if firstline < 0:
            firstline = 0
        start = stc.PositionFromLine(firstline)
        end = stc.PositionFromLine(linenum)
        rawtext = stc.GetTextRange(start, end)+"\n"
        y.set_str(rawtext)
        bod = y.find_good_parse_start(build_char_in_string_func(stc, start))
        if bod is not None or firstline == 0:
            break
    #dprint(rawtext)
    dprint("bod = %d" % bod)
    y.set_lo(bod or 0)

    c = y.get_continuation_type()
    dprint(c)
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
        return indent

    # This line starts a brand new stmt; indent relative to
    # indentation of initial line of closest preceding
    # interesting stmt.
    indentstr = y.get_base_indent_string()
    indent = len(indentstr.expandtabs(tabwidth))
#    text.insert("insert", indent)
    if y.is_block_opener():
        dprint("block opener")
        indent += indentwidth
#        self.smart_indent_event(event)
    elif indent and y.is_block_closer():
        dprint("block dedent")
#        self.smart_backspace_event(event)
        indent = ((indent-1)//indentwidth) * indentwidth
#    return "break"
    return indent

test_cases = """\
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
        else:
            list = (1, 2, 3|
--

----------------------------------------
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
|
--

----------------------------------------
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!\\
aoeua oeuahoenutha oeuhaoehu asoehus"
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
         # comments in here
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
            return
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
        else:|
--

----------------------------------------
# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
'''FLAASH control mode

Major mode to edit FLAASH config files, run FLAASH, and manage the results.
'''

import os, struct, time, re
from cStringIO import StringIO
import locale

from numpy.core.numerictypes import *

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.filebrowsebutton import FileBrowseButtonWithHistory, DirBrowseButton

from peppy.yapsy.plugins import *
from peppy.iofilter import *
from peppy.menu import *
from peppy.major import *
from peppy.about import SetAbout
from peppy.lib.processmanager import *
from peppy.lib.userparams import *
|if blah:

--

"""

def pyparseit():
    stc = getSTC(stcclass=PythonSTC, lexer=wx.stc.STC_LEX_PYTHON)
    
    tests = splittests(test_cases)
    dprint(len(tests))
    for test in tests:
        prepareSTC(stc, test[0])
    
        indent = getIdleIndent(stc, stc.GetCurrentLine())
        indentstr = getIndentString(indent)
        dprint("indent = '%s'" % indentstr)
        print stc.GetText()
        print indentstr+"^"

if __name__ == "__main__":
    pyparseit()
    