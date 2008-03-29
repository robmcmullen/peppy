import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.debug import *

from nose.tools import *

class TestFundamentalIndent(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="Plain Text")
        self.autoindent = BasicAutoindent()

    def checkReturn(self, pair):
        dprint(pair)
        prepareSTC(self.stc, pair[0])
        dprint("after prepareSTC")
        self.autoindent.processReturn(self.stc)
        dprint("after electricReturn")
        assert checkSTC(self.stc, pair[0], pair[1])

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
--------
line at column zero

    line at column 4
    |
--
line at column zero

    line at column 4
    
    |
--------
line at column zero

    line at column 4


back at column zero|
--
line at column zero

    line at column 4


back at column zero
|
-------
"""

        for test in splittests(tests):
            yield self.checkReturn, test

class TestPythonIndent(object):
    def setUp(self):
        self.stc = getSTC(stcclass=PythonMode, lexer="Python")
        self.autoindent = PythonAutoindent()
        #print self.stc

    def getActiveMajorMode(self):
        """dummy method to satisfy new action requirements"""
        return self

    def checkReturn(self, pair):
        dprint(pair)
        prepareSTC(self.stc, pair[0])
        self.autoindent.processReturn(self.stc)
        assert checkSTC(self.stc, pair[0], pair[1])

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
class blah:
    def __init__():
        |
--
class blah:
    def __init__():
        
        |
--------
"""

        for test in splittests(tests):
            yield self.checkReturn, test

    def checkReindentAction(self, pair):
        dprint(pair)
        prepareSTC(self.stc, pair[0])
        #self.stc.showStyle()
        self.autoindent.processTab(self.stc)
        #self.stc.showStyle()
        assert checkSTC(self.stc, pair[0], pair[1])

    def testReindentAction(self):
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
if blah:
  |            pass
--
if blah:
    |pass
--------
blank lines between if and the indented region
if blah:



  |            pass
--
blank lines between if and the indented region
if blah:



    |pass
--------
blank lines have whitespace in them
if blah:
         

                       
  |            pass
--
blank lines have whitespace in them
if blah:
         

                       
    |pass
--------
blank lines have whitespace in them
        if blah:
         

                       
  |            pass
--
blank lines have whitespace in them
        if blah:
         

                       
            |pass
--------
if blah:
    stuff
  |            pass
--
if blah:
    stuff
    |pass
--------
if blah:
    stuff
  |pass
--
if blah:
    stuff
    |pass
--------
class Blah
    def func(self):
        if True:
            if True:
                pass
            elif True:
                pass
        # this comment sets a new baseline, and else will be dedented from here
|else:
--
class Blah
    def func(self):
        if True:
            if True:
                pass
            elif True:
                pass
        # this comment sets a new baseline, and else will be dedented from here
    |else:
--------
"""

        for test in splittests(tests):
            yield self.checkReindentAction, test
