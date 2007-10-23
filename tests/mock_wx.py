import os,sys,re
import __builtin__
from cStringIO import StringIO

import wx
import wx.stc

import peppy.debug
peppy.debug.logfh = sys.stdout

from peppy.stcinterface import PeppyBaseSTC

class MockApp(wx.App):
    def getConfigFilePath(self, file):
        return None
    def GetLog(self):
        return lambda x: True

class MockWX(object):
    app = MockApp()
    frame = wx.Frame(None, -1)

class MockSTC(PeppyBaseSTC):
    pass

__builtin__._ = str
    

def getSTC(init=None, stcclass=MockSTC, count=1, lexer=wx.stc.STC_LEX_PYTHON, tab_size=4, use_tabs=False):
    stc = stcclass(MockWX.frame)
    stc.SetLexer(lexer)
    if lexer == wx.stc.STC_LEX_PYTHON:
        # FIXME: this is a duplicate of the keyword string from
        # PythonMode.  Find a way to NotRepeatMyself instead of this.
        stc.SetKeyWords(0, 'and as assert break class continue def del elif else except exec finally for from global if import in is lambda not or pass print raise return try while True False None self')

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
