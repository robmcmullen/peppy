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

class DumClassPrefs(object):
    edge_column = 80
    
class TestFundamentalFill(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalSTC, lexer="None")
        self.wrap = FillParagraphOrRegion(self)
        self.classprefs = DumClassPrefs
        
    def getActiveMajorMode(self):
        return self
        
    def checkFind(self, test):
        prepareSTC(self.stc, test['source'])
        prefix, lines, start, end = self.stc.findParagraph(self.stc.GetCurrentPos())
        dprint(lines)
        shouldbe = test['lines'].splitlines()
        eq_(shouldbe, lines)
        self.wrap.action()
        assert checkSTC(self.stc, test['source'], test['fill'])

    def testFind(self):
        tests = """\
line at column zero
  line
  at
  column|
  one
-- lines
line
at
column
one
-- fill
line at column zero
  line at column one|
"""

        for test in splittestdict(tests):
            yield self.checkFind, test
