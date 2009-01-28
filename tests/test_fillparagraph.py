import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *

from nose.tools import *

class TestFundamentalCommentDelimiters(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="None")
    
    def testCommentDelim(self):
        eq_(("", "blah blah", ""), self.stc.splitCommentLine("blah blah"))
        eq_(("", "blah blah   ", ""), self.stc.splitCommentLine("blah blah   "))
        eq_(("  ", "blah blah   ", ""), self.stc.splitCommentLine("  blah blah   "))


class TestPythonCommentDelimiters(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="Python")
    
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
        self.stc = getSTC(stcclass=FundamentalMode, lexer="C")
    
    def testCommentDelim(self):
        eq_(("/*", "blah blah", "*/"), self.stc.splitCommentLine("/*blah blah*/"))
        eq_(("/*", "blah blah   ", "*/"), self.stc.splitCommentLine("/*blah blah   */"))
        eq_(("  /*", "blah blah", "*/  "), self.stc.splitCommentLine("  /*blah blah*/  "))
        eq_(("  /*", "  blah blah  ", "*/  "), self.stc.splitCommentLine("  /*  blah blah  */  "))

class DumClassPrefs(object):
    edge_column = 80
    
class TestFundamentalFill(object):
    lexer = "None"
    stcclass = FundamentalMode
    
    def setUp(self):
        self.stc = getSTC(stcclass=self.stcclass, lexer=self.lexer)
        self.wrap = FillParagraphOrRegion(self.stc.frame)
        self.classprefs = DumClassPrefs
        
    def getActiveMajorMode(self):
        return self
        
    def checkFind(self, test):
        prepareSTC(self.stc, test['source'])
        info = self.stc.findParagraph(self.stc.GetCurrentPos())
        dprint(info.getLines())
        shouldbe = test['lines'].splitlines()
        eq_(shouldbe, info.getLines())
        self.wrap.action()
        assert checkSTC(self.stc, test['source'], test['fill'])

    def testFind(self):
        tests = """\
  line
  at
  column|
  two
-- lines
line
at
column
two
-- fill
  line at column two|
------
line at column zero
  line
  at
  column|
  two
-- lines
line
at
column
two
-- fill
line at column zero
  line at column two|
------
line at column zero
  line
  at
    column|
    four
-- lines
column
four
-- fill
line at column zero
  line
  at
    column four|
------
line at column zero
  line
  at
    column
    four|
-- lines
column
four
-- fill
line at column zero
  line
  at
    column four|
------
  line
  at
    column
    four|
line at column zero
-- lines
column
four
-- fill
  line
  at
    column four|
line at column zero
"""

        for test in splittestdict(tests):
            yield self.checkFind, test

class TestPythonFill(TestFundamentalFill):
    lexer = "Python"
    stcclass = FundamentalMode
    
    def testPythonFind(self):
        tests = """\
# line
# at
# column|
# two
-- lines
 line
 at
 column
 two
-- fill
# line at column two|
------
line at column zero
  #line
  #at
  #column|
  #two
-- lines
line
at
column
two
-- fill
line at column zero
  # line at column two|
------
line at column zero
  line
  at
    ## column|
    ## four
-- lines
 column
 four
-- fill
line at column zero
  line
  at
    ## column four|
------
line at column zero
  line
  at
    '''column
    four|
    '''
-- lines
'''column
four
-- fill
line at column zero
  line
  at
    '''column four|
    '''
------
  line
  at
    '''
    column
    four|
    '''
    another line at column four
-- lines
column
four
-- fill
  line
  at
    '''
    column four|
    '''
    another line at column four
"""

        for test in splittestdict(tests):
            yield self.checkFind, test
