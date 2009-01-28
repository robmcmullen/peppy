import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.c_mode import *
from peppy.plugins.text_transforms import *

from nose.tools import *


class DumClassPrefs(object):
    edge_column = 80
    
class TestCFill(object):
    lexer = "C"
    stcclass = CMode
    
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
        tests = u"""\
stuff
/* aoeuaoeu |
 * aouoeuaoeu
*/
-- lines
aoeuaoeu
aouoeuaoeu

-- fill
stuff
/* aoeuaoeu aouoeuaoeu
*/|
------------------------------------
/* zwmzwvmzwvm
 * snthsnthsnth
 */|
void func();
-- lines
zwmzwvmzwvm
snthsnthsnth

-- fill
/* zwmzwvmzwvm snthsnthsnth
*/|
void func();
"""

        for test in splittestdict(tests):
            yield self.checkFind, test
