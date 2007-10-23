import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcinterface import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *

from nose.tools import *

class TestFundamentalIndent(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer=wx.stc.STC_LEX_NULL)

    def checkReturn(self, pair):
        prepareSTC(self.stc, pair)
        self.stc.electricReturn()
        assert checkSTC(self.stc, pair)

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

class TestPythonIndent(PythonElectricReturnMixin, StandardReturnMixin, PythonReindentMixin):
    def setUp(self):
        self.stc = getSTC(stcclass=PythonSTC, lexer=wx.stc.STC_LEX_PYTHON)
        self.reindentAction = Reindent(self)

    def getActiveMajorMode(self):
        """dummy method to satisfy new action requirements"""
        return self

    def checkReturn(self, pair):
        prepareSTC(self.stc, pair)
        self.stc.electricReturn()
        assert checkSTC(self.stc, pair)

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
        prepareSTC(self.stc, pair)
        #self.stc.showStyle()
        self.reindentAction.action()
        #self.stc.showStyle()
        assert checkSTC(self.stc, pair)

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
"""

        for test in splittests(tests):
            yield self.checkReindentAction, test
