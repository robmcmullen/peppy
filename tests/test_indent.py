import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import getSTC

from peppy.stcinterface import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *

from nose.tools import *

def prepareSTC(stc, pair):
    before, after = pair
    print "*** before ***\n%s" % before
    cursor = before.find("|")
    stc.SetText(before)

    # change "|" to the cursor
    stc.SetTargetStart(cursor)
    stc.SetTargetEnd(cursor+1)
    stc.ReplaceTarget("")
    stc.GotoPos(cursor)
    
    stc.Colourise(0, stc.GetTextLength())
    stc.showStyle()

def checkSTC(stc, pair):
    stc.showStyle()
    before, after = pair

    # change cursor to "|"
    stc.ReplaceSelection("|")
    text = stc.GetText()
    if after == text:
        print "Matched:\n*** stc ***\n%s\n***\n%s\n***" % (text, after)
        return True
    print "Not matched:\n*** stc ***: repr=%s\n%s\n***\n*** should be ***: repr=%s\n%s\n***" % (repr(text), text, repr(after), after)
    return False

def splittests(text):
    tests = []

    # at least 4 '-' characters delimits a test
    groups = re.split('[\r\n]+-----*[\r\n]+', text)
    print groups
    for test in groups:
        # 2 '-' characters delimits the before and after pair
        pair = re.split('[\r\n]+--[\r\n]+', test)
        if len(pair) == 2:
            tests.append(pair)
    print tests
    return tests
        

class TestFundamentalIndent(StandardReturnMixin, StandardReindentMixin):
    def setUp(self):
        self.stc = getSTC(lexer=wx.stc.STC_LEX_NULL)

    def testReturn(self):
        tests = """\
line at column zero|
--
line at column zero
|
--------
    line at column 4|
--
    line at column 4
    |
--------
line at column zero
    line at column 4|
--
line at column zero
line at column 4
|
--------
line at column zero

    line at column 4|
--
line at column zero

    line at column 4
    |
-------
"""

        for test in splittests(tests):
            prepareSTC(self.stc, test)
            self.electricReturn()
            assert checkSTC(self.stc, test)

class TestPythonIndent(PythonElectricReturnMixin, StandardReturnMixin, PythonReindentMixin):
    def setUp(self):
        self.stc = getSTC(lexer=wx.stc.STC_LEX_PYTHON)
        self.reindentAction = Reindent(self)

    def testReturn(self):
        tests = """\
class blah:|
--
class blah:
    |
--------
class blah:
    def __init__():|
--
class blah:
    def __init__():
        |
--------
"""

        for test in splittests(tests):
            prepareSTC(self.stc, test)
            self.electricReturn()
            assert checkSTC(self.stc, test)
            
    def testReindent(self):
        tests = """\
if blah:
    pass
    else:|
--
if blah:
    pass
else:|
--------
if blah:
  pass|
--
if blah:
    pass|
--------
if blah:
  pa|ss
--
if blah:
    pa|ss
--------
if blah:
  |  pass
--
if blah:
    |pass
--------
if blah:
 | pass
--
if blah:
    |pass
--------
"""

        for test in splittests(tests):
            prepareSTC(self.stc, test)
            self.stc.showStyle()
            self.reindentAction.modify(self)
            self.stc.showStyle()
            assert checkSTC(self.stc, test)
