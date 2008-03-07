# -*- mode:Python;  cursor-type: (bar. 1)-*-
import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcbase import *
from peppy.lib.emacsutil import *

from tests.mock_wx import getPlainSTC

from nose.tools import *

class TestEmacs(object):
    def testMode(self):
        eq_('C++',parseModeline('-*-C++-*-')[0])
        eq_('C++',parseModeline('-*- C++ -*-')[0])
        eq_('C++',parseModeline('-*-C++ -*-')[0])
        eq_('C++',parseModeline('-*-  C++-*-')[0])
        eq_('Python',parseModeline('-*-Python-*-')[0])
        eq_('Python',parseModeline('-*- Python -*-')[0])

    def testModeNoVars(self):
        eq_('C++',parseModeline('-*-mode:C++-*-')[0])
        eq_('C++',parseModeline('-*- mode:C++-*-')[0])
        eq_('C++',parseModeline('-*- mode:C++  -*-')[0])
        eq_('Python',parseModeline('-*- mode:Python-*-')[0])

    def testModeVars(self):
        modestring='-*-mode:C++; var1:val1-*-'
        eq_('C++',parseModeline(modestring)[0])
        eq_('val1',parseModeline(modestring)[1]['var1'])
        modestring='-*-mode:C++; var1:val1; var2:val2;-*-'
        eq_('C++',parseModeline(modestring)[0])
        eq_('val1',parseModeline(modestring)[1]['var1'])
        eq_('val2',parseModeline(modestring)[1]['var2'])
        modestring='-*- mode: C++; var1:val1; var2:val2-*-'
        eq_('C++',parseModeline(modestring)[0])
        eq_('val1',parseModeline(modestring)[1]['var1'])
        eq_('val2',parseModeline(modestring)[1]['var2'])
        modestring='-*- mode: C++ ; var1:val1; var2:val2 -*-'
        eq_('C++',parseModeline(modestring)[0])
        eq_('val1',parseModeline(modestring)[1]['var1'])
        eq_('val2',parseModeline(modestring)[1]['var2'])
        modestring='-*- mode:Python; var1:val1; var2:val2; -*-'
        eq_('Python',parseModeline(modestring)[0])
        eq_('val1',parseModeline(modestring)[1]['var1'])
        eq_('val2',parseModeline(modestring)[1]['var2'])
