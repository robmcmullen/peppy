# -*- mode:Python;  cursor-type: (bar. 1)-*-
import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcbase import *
from peppy.lib.kateutil import *

from tests.mock_wx import getPlainSTC

from nose.tools import *

class TestEmacs(object):
    def testKateVars(self):
        modestring='kate: var1 val1;'
        eq_('val1',kateParseLine(modestring)['var1'])
        modestring='kate: var1 val1; var2 val2;'
        eq_('val1',kateParseLine(modestring)['var1'])
        eq_('val2',kateParseLine(modestring)['var2'])

    tests = [
    ('kate: space-indent on; indent-width 2; replace-tabs on;', [('GetIndent', 2)]),
    ('kate: tab-width 4; indent-width 4;', [('GetIndent', 4), ('GetTabWidth', 4)]),
    ('kate: show-tabs on;', [('GetViewWhiteSpace', 1)]),
    ]

    def setUp(self):
        self.stc = getPlainSTC()
        
    def checkSettings(self, test):
        self.stc.SetText(test[0])
        applyKateVariables(self.stc, [test[0]])
        for fcn, val in test[1]:
            eq_((fcn, getattr(self.stc, fcn)()), (fcn, val))

    def testSettings(self):
        for test in self.tests:
            yield self.checkSettings, test
