import os,sys,re
import __builtin__
from cStringIO import StringIO

import wx
import wx.stc

from peppy.debug import *
logfh = sys.stderr

from peppy.stcinterface import PeppyBaseSTC

class MockApp(wx.App):
    def getConfigFilePath(self, file):
        return None
    def GetLog(self):
        return dprint

class MockWX(object):
    app = MockApp()
    frame = wx.Frame(None, -1)

class MockSTC(PeppyBaseSTC):
    pass

__builtin__._ = str
    

def getSTC(init=None, stcclass=MockSTC, count=1, lexer="Python", tab_size=4, use_tabs=False):
    stc = stcclass(MockWX.frame)
    #stc.SetLexer(lexer)
    stc.ConfigureLexer(lexer)
#    if lexer == wx.stc.STC_LEX_PYTHON:
#        # FIXME: this is a duplicate of the keyword string from
#        # PythonMode.  Find a way to NotRepeatMyself instead of this.
#        stc.SetKeyWords(0, 'and as assert break class continue def del elif else except exec finally for from global if import in is lambda not or pass print raise return try while True False None self')

    stc.SetText("")
    stc.SetEOLMode(wx.stc.STC_EOL_LF)
    stc.SetProperty("fold", "1")
    stc.SetIndent(tab_size)
    stc.SetUseTabs(use_tabs)   
    if init == 'py':
        stc.SetText("python source goes here")
    elif init == 'columns':
        for i in range(count):
            stc.AddText('%04d-0123456789\n' % i)
    stc.Colourise(0, stc.GetTextLength())
    return stc

def prepareSTC(stc, *pair):
    before = pair[0]
    print "*** before *** repr=%s\n%s" % (repr(before), before)
    cursor = before.find("|")
    stc.SetText(before)

    # change "|" to the cursor
    stc.SetTargetStart(cursor)
    stc.SetTargetEnd(cursor+1)
    stc.ReplaceTarget("")
    stc.GotoPos(cursor)
    
    stc.Colourise(0, stc.GetTextLength())
    stc.showStyle()

def checkSTC(stc, *pair):
    stc.showStyle()
    before = pair[0]
    after = pair[1]

    # change cursor to "|"
    stc.ReplaceSelection("|")
    text = stc.GetText()
    if after == text:
        print "Matched:\n*** stc ***\n%s\n***\n%s\n***" % (text, after)
        return True
    print "Not matched:\n*** stc ***: repr=%s\n%s\n***\n*** should be ***: repr=%s\n%s\n***" % (repr(text), text, repr(after), after)
    return False

def splittests(text):
    tests = []

    # at least 4 '-' characters delimits a test
    groups = re.split('[\r\n]+-----*[\r\n]+', text)
    print groups
    for test in groups:
        # 2 '-' characters delimits the before and after pair
        pair = re.split('[\r\n]+--[\r\n]+', test)
        if len(pair) == 2:
            tests.append(pair)
    print tests
    return tests

def splittestdict(text):
    tests = []

    # at least 4 '-' characters delimits a test
    test_groups = re.split('[\r\n]+-----*[\r\n]+', text)
    dprint(test_groups)
    for test in test_groups:
        # 2 '-' characters delimits the before and after pair
        groups = re.split('([\r\n]+)(--\s*(\S+)).*[\r\n]+', test)
        dprint(groups)
        block = {}
        block['source'] = groups[0] + groups[1]
        count = 2
        while count < len(groups):
            if groups[count].startswith('--'):
                count += 1
                key = groups[count]
                count += 1
                block[key] = groups[count]
                count += 1
                if count < len(groups):
                    # If there's a return character, add it
                    block[key] += groups[count]
                    count += 1
            else:
                block['text'] = groups[count]
                count += 1
                if count < len(groups):
                    # If there's a return character, add it
                    block['text'] += groups[count]
                    count += 1
        tests.append(block)
    print tests
    return tests
