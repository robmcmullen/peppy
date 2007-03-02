import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcinterface import *

from tests.mock_wx import getSTC

from nose.tools import *

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


class STCProxyTest(STCProxy):
   def GetText(self):
      return "BLAH!!!"

   def CanEdit(self):
      return False

   def CanUndo(self):
      return 5

class TestProxy(object):
   def setUp(self):
      self.stc = STCProxyTest(getSTC())

   def testProxy(self):
      eq_(self.stc.GetText(), 'BLAH!!!')
      eq_(self.stc.CanEdit(), False)
      eq_(self.stc.CanUndo(), 5)
      eq_(self.stc.GetTextLength(), 0)
