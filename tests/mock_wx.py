import os,sys,re
import __builtin__
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcinterface import PeppyBaseSTC

class MockWX(object):
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1)

MockSTC = PeppyBaseSTC(MockWX.frame)

__builtin__._ = str
    

def getSTC(init=None, count=1, lexer=wx.stc.STC_LEX_PYTHON, tab_size=4, use_tabs=False):
    MockSTC.SetLexer(lexer)
    if lexer == wx.stc.STC_LEX_PYTHON:
        # FIXME: this is a duplicate of the keyword string from
        # PythonMode.  Find a way to NotRepeatMyself instead of this.
        MockSTC.SetKeyWords(0, 'and as assert break class continue def del elif else except exec finally for from global if import in is lambda not or pass print raise return try while True False None self')

    MockSTC.SetText("")
    MockSTC.SetEOLMode(wx.stc.STC_EOL_LF)
    MockSTC.SetProperty("fold", "1")
    MockSTC.SetIndent(tab_size)
    MockSTC.SetUseTabs(use_tabs)   
    if init == 'py':
        MockSTC.SetText("python source goes here")
    elif init == 'columns':
        for i in range(count):
            MockSTC.AddText('%04d-0123456789\n' % i)
    MockSTC.Colourise(0, MockSTC.GetTextLength())
    return MockSTC
