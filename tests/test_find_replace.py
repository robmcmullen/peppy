import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.find_replace import *

from nose.tools import *

class TestFind(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="None")
        self.stc.SetText("line 0\nline 1\nline 2\nline 3\nblah blah blah\nstuff\nthings")
        self.settings = FindSettings()
        self.service = FindService(self.stc, self.settings)
    
    def testFindNext(self):
        self.service.setFindString("line")
        output = self.service.doFindNext()
        dprint(output)
        assert output == (0,0)
        output = self.service.doFindNext()
        dprint(output)
        assert output == (7,4)
        output = self.service.doFindNext()
        dprint(output)
        assert output == (14,11)
        output = self.service.doFindNext()
        dprint(output)
        assert output == (21,18)
        output = self.service.doFindNext()
        dprint(output)
        assert output == (-1,25)
    
    def testFindPrevious(self):
        self.stc.GotoPos(1000)
        self.service.setFindString("line")
        output = self.service.doFindPrev()
        dprint(output)
        assert output == (21,55)
        output = self.service.doFindPrev()
        dprint(output)
        assert output == (14,21)
        output = self.service.doFindPrev()
        dprint(output)
        assert output == (7,14)
        output = self.service.doFindPrev()
        dprint(output)
        assert output == (0,7)
        output = self.service.doFindPrev()
        dprint(output)
        assert output == (-1,0)


class TestFindWildcard(TestFind):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="None")
        self.stc.SetText("line 0\nline 1\nline 2\nline 3\nblah blah blah\nstuff\nthings")
        self.settings = FindSettings()
        self.service = FindWildcardService(self.stc, self.settings)


class TestFindRegex(TestFind):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="None")
        self.stc.SetText("line 0\nline 1\nline 2\nline 3\nblah blah blah\nstuff\nthings")
        self.settings = FindSettings()
        self.service = FindRegexService(self.stc, self.settings)
