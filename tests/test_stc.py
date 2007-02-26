import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcinterface import PeppyBaseSTC

from nose.tools import *

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

class TestBasic(object):
   def setUp(self):
       self.stc = getSTC()

   def testInsert(self):
       self.stc.SetText('blah')
       self.stc.InsertText(2, 'AHBL')
       eq_(self.stc.GetText(), 'blAHBLah')

class TestColumns(object):
   def setUp(self):
       self.count = 10
       self.mid = self.count/2
       self.stc = getSTC('columns', self.count)

   def testLines(self):
       eq_(self.stc.GetLineCount(), self.count+1)
       eq_(self.stc.GetLine(0), '0000-0123456789\n')
       eq_(self.stc.GetLine(self.mid), '%04d-0123456789\n' % (self.mid))
       eq_(self.stc.GetLine(self.count-1), '%04d-0123456789\n' % (self.count-1))
       eq_(self.stc.GetLine(self.count), '')

   def testInsert(self):
       pos = self.stc.PositionFromLine(self.mid)
       self.stc.InsertText(pos, 'spam')
       eq_(self.stc.GetLine(self.mid), 'spam%04d-0123456789\n' % (self.mid))

   def testInsertMulti(self):
       pos = self.stc.PositionFromLine(self.mid)
       self.stc.InsertText(pos, 'spam\nspam')
       eq_(self.stc.GetLine(self.mid), 'spam\n')
       eq_(self.stc.GetLine(self.mid + 1), 'spam%04d-0123456789\n' % (self.mid))

class TestPasteAtColumn(object):
   def setUp(self):
       self.count = 10
       self.mid = self.count/2
       self.stc = getSTC('columns', self.count)
       
   def testInsert(self):
      self.stc.SetSelection(5,10)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetLine(0), '%04d-abc0123456789\n' % (0))
      eq_(self.stc.GetLine(1), '%04d-abc0123456789\n' % (1))
      eq_(self.stc.GetLine(2), '%04d-abc0123456789\n' % (2))
      eq_(self.stc.GetLine(3), '%04d-0123456789\n' % (3))


