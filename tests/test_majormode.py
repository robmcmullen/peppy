import os,sys,re

from peppy.major import *

from nose.tools import *

class TestEmacsMode:
    def testMode(self):
        eq_(None,parseEmacs('#!/nothing/here')[0])
        eq_('C++',parseEmacs('-*-C++-*-')[0])
        eq_('C++',parseEmacs('-*- C++ -*-')[0])
        eq_('C++',parseEmacs('-*-C++ -*-')[0])
        eq_('C++',parseEmacs('-*-  C++-*-')[0])
        eq_('C++',parseEmacs('#!/nothing/here -*-C++-*-')[0])
        eq_('C++',parseEmacs('#!/nothing/here\n-*-C++-*-')[0])
        eq_('Python',parseEmacs('#!/nothing/here\n-*-Python-*-')[0])

    def testModeNoVars(self):
        eq_(None,parseEmacs('#!/nothing/here')[0])
        eq_('C++',parseEmacs('-*-mode:C++-*-')[0])
        eq_('C++',parseEmacs('-*- mode:C++-*-')[0])
        eq_('C++',parseEmacs('-*- mode:C++  -*-')[0])
        eq_('C++',parseEmacs('#!/nothing/here -*-mode:C++-*-')[0])
        eq_('C++',parseEmacs('#!/nothing/here\n  -*-   mode:C++  -*-')[0])
        eq_('Python',parseEmacs('-*- mode:Python-*-')[0])

    def testModeVars(self):
        eq_(None,parseEmacs('#!/nothing/here')[0])
        modestring='-*-mode:C++; var1:val1-*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        modestring='-*-mode:C++; var1:val1; var2:val2;-*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
        modestring='-*- mode:C++; var1:val1; var2:val2-*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
        modestring='-*- mode:C++ ; var1:val1; var2:val2 -*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
        modestring='#!/nothing/here -*-mode:C++; var1:val1; var2:val2-*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
        modestring='#!/nothing/here -*-   mode:C++  ; var1:val1; var2:val2;  -*-'
        eq_('C++',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
        modestring='-*- mode:Python; var1:val1; var2:val2; -*-'
        eq_('Python',parseEmacs(modestring)[0])
        eq_('val1',parseEmacs(modestring)[1]['var1'])
        eq_('val2',parseEmacs(modestring)[1]['var2'])
            
class MockMode(MajorMode):
    keyword = "mock"
    regex = "\.mock$"
    emacs_synonyms = "mach"

class MockPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)

    def getMajorModes(self):
        yield MockMode
    
class TestMatcherBase:
    def setUp(self):
        comp_mgr=ComponentManager()
        self.base=MockPlugin(comp_mgr)
        self.driver=MajorModeMatcherDriver(comp_mgr)

    def testEmacs(self):
        for mode in self.base.getMajorModes():
            eq_(MockMode, mode)
        eq_(MockMode, self.driver.scanEmacs("-*- mock -*-"))
        eq_(MockMode, self.driver.scanEmacs("-*- mach -*-"))
        eq_(None, self.driver.scanEmacs("-*- mawck -*-"))
        
    def testShell(self):
        eq_(MockMode, self.driver.scanShell("#!/usr/bin/mock"))
        eq_(MockMode, self.driver.scanShell("#!/usr/bin/env mock"))
        eq_(MockMode, self.driver.scanShell("#!/usr/bin/mock.exe"))
        eq_(MockMode, self.driver.scanShell("#!/usr/bin/env mock.exe"))
        eq_(None, self.driver.scanShell("#!/usr/bin/mach"))
        eq_(None, self.driver.scanShell("#!/usr/bin/env -a_mockingbird"))
        eq_(None, self.driver.scanShell("#!/usr/bin/mocking.exe"))
        eq_(None, self.driver.scanShell("#!/usr/bin/env mocking.exe"))
        eq_(None, self.driver.scanShell("#!/usr/bin/amock"))
        eq_(None, self.driver.scanShell("#!/usr/bin/env amock"))
        eq_(None, self.driver.scanShell("#!/usr/bin/env mach"))
        eq_(None, self.driver.scanShell("#!/usr/bin/env -a_machine"))
