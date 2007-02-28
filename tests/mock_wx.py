import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcinterface import PeppyBaseSTC

class MockWX(object):
   app = wx.PySimpleApp()
   frame = wx.Frame(None, -1)

MockSTC = PeppyBaseSTC(MockWX.frame)

def getSTC(init=None, count=1):
   MockSTC.SetText("")
   if init == 'py':
       MockSTC.SetText("python source goes here")
   elif init == 'columns':
       for i in range(count):
           MockSTC.AddText('%04d-0123456789\n' % i)
   return MockSTC
