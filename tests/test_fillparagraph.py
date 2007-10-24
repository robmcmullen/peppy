import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcinterface import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *

from nose.tools import *

class TestFundamentalCommentDelimiters(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer="None")
    
    def testCommentDelim(self):
        eq_(("", "blah blah", ""), self.stc.splitCommentLine("blah blah"))
        eq_(("", "blah blah   ", ""), self.stc.splitCommentLine("blah blah   "))
        eq_(("  ", "blah blah   ", ""), self.stc.splitCommentLine("  blah blah   "))


class TestPythonCommentDelimiters(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer="Python")
    
    def testCommentDelim(self):
        eq_(("#", "blah blah", ""), self.stc.splitCommentLine("#blah blah"))
        eq_(("#", "blah blah   ", ""), self.stc.splitCommentLine("#blah blah   "))
        eq_(("  #", "blah blah   ", ""), self.stc.splitCommentLine("  #blah blah   "))
        eq_(("  #", "  blah blah   ", ""), self.stc.splitCommentLine("  #  blah blah   "))
        eq_(("##", "blah blah", ""), self.stc.splitCommentLine("##blah blah"))
        eq_(("###", "blah blah   ", ""), self.stc.splitCommentLine("###blah blah   "))
        eq_(("###", "  blah blah   ", ""), self.stc.splitCommentLine("###  blah blah   "))
        eq_(("  ##", "blah blah   ", ""), self.stc.splitCommentLine("  ##blah blah   "))
        eq_(("  ##", "  blah blah   ", ""), self.stc.splitCommentLine("  ##  blah blah   "))


class TestCCommentDelimiters(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer="C")
    
    def testCommentDelim(self):
        eq_(("/*", "blah blah", "*/"), self.stc.splitCommentLine("/*blah blah*/"))
        eq_(("/*", "blah blah   ", "*/"), self.stc.splitCommentLine("/*blah blah   */"))
        eq_(("  /*", "blah blah", "*/  "), self.stc.splitCommentLine("  /*blah blah*/  "))
        eq_(("  /*", "  blah blah  ", "*/  "), self.stc.splitCommentLine("  /*  blah blah  */  "))


class TestFundamentalFill(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer="None")
    
    def checkFind(self, pair):
        prepareSTC(self.stc, pair)
        lines = self.stc.findParagraph(self.stc.GetCurrentPos())
        print lines
        assert checkSTC(self.stc, pair)

    def testReturn(self):
        tests = """\
line at column zero
  line at column one|
--
line at column zero
line at column one|
---------
line at column zero
  line at column one|
  line at column two
--
line at column zero
  line at column one|
  line at column two
"""

        for test in splittests(tests):
            yield self.checkFind, test
