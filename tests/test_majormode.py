import os,sys,re

from peppy.major import *

from nose.tools import *

class TestEmacsMode:
    def setUp(self):
        comp_mgr=ComponentManager()
        self.driver=MajorModeMatcherDriver(comp_mgr)

    def testMode(self):
        test=self.driver.parseEmacs
        eq_(None,test('#!/nothing/here'))
        eq_('C++',test('-*-C++-*-')[0])
        eq_('C++',test('-*- C++ -*-')[0])
        eq_('C++',test('-*-C++ -*-')[0])
        eq_('C++',test('-*-  C++-*-')[0])
        eq_('C++',test('#!/nothing/here -*-C++-*-')[0])
        eq_('C++',test('#!/nothing/here\n-*-C++-*-')[0])
        eq_('Python',test('#!/nothing/here\n-*-Python-*-')[0])

    def testModeNoVars(self):
        test=self.driver.parseEmacs
        eq_(None,test('#!/nothing/here'))
        eq_('C++',test('-*-mode:C++-*-')[0])
        eq_('C++',test('-*- mode:C++-*-')[0])
        eq_('C++',test('-*- mode:C++  -*-')[0])
        eq_('C++',test('#!/nothing/here -*-mode:C++-*-')[0])
        eq_('C++',test('#!/nothing/here\n  -*-   mode:C++  -*-')[0])
        eq_('Python',test('-*- mode:Python-*-')[0])

    def testModeVars(self):
        test=self.driver.parseEmacs
        eq_(None,test('#!/nothing/here'))
        modestring='-*-mode:C++; var1:val1-*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        modestring='-*-mode:C++; var1:val1; var2:val2;-*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
        modestring='-*- mode:C++; var1:val1; var2:val2-*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
        modestring='-*- mode:C++ ; var1:val1; var2:val2 -*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
        modestring='#!/nothing/here -*-mode:C++; var1:val1; var2:val2-*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
        modestring='#!/nothing/here -*-   mode:C++  ; var1:val1; var2:val2;  -*-'
        eq_('C++',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
        modestring='-*- mode:Python; var1:val1; var2:val2; -*-'
        eq_('Python',test(modestring)[0])
        eq_('val1',test(modestring)[1]['var1'])
        eq_('val2',test(modestring)[1]['var2'])
            
class MockMode(MajorMode):
    keyword = "mock"
    regex = "\.mock$"

class MockPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)

    def possibleModes(self):
        yield MockMode

    def possibleEmacsMappings(self):
        yield ('mach',MockMode)
    
class TestMatcherBase:
    def setUp(self):
        comp_mgr=ComponentManager()
        self.base=MockPlugin(comp_mgr)

    def testEmacs(self):
        for mode in self.base.possibleModes():
            eq_(MockMode, mode)
        eq_(MockMode, self.base.scanEmacs("mock","").view)
        eq_(MockMode, self.base.scanEmacs("mach","").view)
        eq_(None, self.base.scanEmacs("mawck",""))
        
    def testShell(self):
        eq_(MockMode, self.base.scanShell("#!/usr/bin/mock").view)
        eq_(MockMode, self.base.scanShell("#!/usr/bin/env mock").view)
        eq_(MockMode, self.base.scanShell("#!/usr/bin/mock.exe").view)
        eq_(MockMode, self.base.scanShell("#!/usr/bin/env mock.exe").view)
        eq_(None, self.base.scanShell("#!/usr/bin/mach"))
        eq_(None, self.base.scanShell("#!/usr/bin/env -a_mockingbird"))
        eq_(None, self.base.scanShell("#!/usr/bin/mocking.exe"))
        eq_(None, self.base.scanShell("#!/usr/bin/env mocking.exe"))
        eq_(None, self.base.scanShell("#!/usr/bin/amock"))
        eq_(None, self.base.scanShell("#!/usr/bin/env amock"))
        eq_(None, self.base.scanShell("#!/usr/bin/env mach"))
        eq_(None, self.base.scanShell("#!/usr/bin/env -a_machine"))
