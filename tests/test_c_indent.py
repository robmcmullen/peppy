import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.cpp_mode import *
from peppy.debug import *

from nose.tools import *

# NOTE: Scintilla will not properly fold the last line in the file if it does
# not end in a return

class TestCPPIndent(object):
    def setUp(self):
        #CPlusPlusMode.debuglevel = 1
        self.stc = getSTC(stcclass=CPlusPlusMode, lexer="CPP")
        self.autoindent = CStyleAutoindent()
        CStyleAutoindent.debuglevel = 1
        print "folding=%s" % self.stc.GetProperty("fold")
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
if (blah) {|

--
if (blah) {
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
if (blah) {
       |

--
if (blah) {
    |

--------
"""

        for test in splittests(tests):
            yield self.checkReindentAction, test
