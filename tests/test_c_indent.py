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

    def SKIPPEDtestReturn(self):
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
switch (blah) {
  case 0:
     |

--
switch (blah) {
  case 0:
    |

--------
switch (blah) {
  case 0: //extra
     |

--
switch (blah) {
  case 0: //extra
    |

--------
switch (func(blah,
        stuff)) {
  case 0:
    printf("stuff");
    case 1:|

--
switch (func(blah,
        stuff)) {
  case 0:
    printf("stuff");
  case 1:|

--------
switch (func(blah,
        stuff)) {
  case 0:
    printf("stuff");
    case 1: //extra|

--
switch (func(blah,
        stuff)) {
  case 0:
    printf("stuff");
  case 1: //extra|

--------
class A::public B {
  private:
    int blah;
    public:|

--
class A::public B {
  private:
    int blah;
  public:|

--------
void main(void)
    {|

--
void main(void)
{|

--------
"""

        for test in splittests(tests):
            yield self.checkReindentAction, test

    def testInsideStatement(self):
        prepareSTC(self.stc, "print|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "print(stuff)|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "for (i=0|\n")
        pos = self.stc.GetCurrentPos()
        assert self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "for (i=0;|\n")
        pos = self.stc.GetCurrentPos()
        assert self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "for (i=0; i<5|\n")
        pos = self.stc.GetCurrentPos()
        assert self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "for (i=0; i<5;|\n")
        pos = self.stc.GetCurrentPos()
        assert self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "for (i=0| i<5;\n")
        pos = self.stc.GetCurrentPos()
        assert self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "if (blah) stuff|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "if (blah)\n    stuff|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "stuff;\nstuff;\nif (blah(blah,\n    blah))\n    stuff|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
        prepareSTC(self.stc, "if (blah(blah,\n    blah))\n    stuff|\n")
        pos = self.stc.GetCurrentPos()
        assert not self.autoindent.isInsideStatement(self.stc, pos)
