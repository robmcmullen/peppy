import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcbase import *

from tests.mock_wx import getSTC

from nose.tools import *

def insertColumns(stc, count):
    for index in range(0, count):
        stc.AppendText('%04d-0123456789\n' % (index))

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
       self.stc = getSTC()
       insertColumns(self.stc, self.count)

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

class TestPasteAtColumn1(object):
   def setUp(self):
       self.count = 10
       self.mid = self.count/2
       self.stc = getSTC()
       insertColumns(self.stc, self.count)

   def testInsert(self):
      self.stc.SetSelection(5,10)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetLine(0), '%04d-abc0123456789\n' % (0))
      eq_(self.stc.GetLine(1), '%04d-abc0123456789\n' % (1))
      eq_(self.stc.GetLine(2), '%04d-abc0123456789\n' % (2))
      eq_(self.stc.GetLine(3), '%04d-0123456789\n' % (3))


class TestPasteAtColumn2(object):
   def setUp(self):
      self.stc = getSTC()
      self.stc.SetText("""\
123
123456
1234
12345678
12""")

   def test1(self):
      self.stc.SetSelection(2, 2)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
12abc3
12abc3456
12abc34
12345678
12""")
      
   def test2(self):
      self.stc.SetSelection(18, 18)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
123
123456
1234
12abc345678
12abc
  abc""")

   def test3(self):
      self.stc.SetSelection(20, 20)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
123
123456
1234
1234abc5678
12  abc
    abc""")

class TestPasteAtColumn3(object):
   def setUp(self):
      self.stc = getSTC()
      self.stc.SetText("""\
123
123456

12345678
12""")

   def test1(self):
      self.stc.SetSelection(2, 2)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
12abc3
12abc3456
  abc
12345678
12""")
      
   def test2(self):
      self.stc.SetSelection(11, 11)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
123
123456
abc
abc12345678
abc12""")
      
   def test2(self):
      self.stc.SetSelection(12, 12)
      self.stc.PasteAtColumn("abc\nabc\nabc")
      eq_(self.stc.GetText(),"""\
123
123456

abc12345678
abc12
abc""")


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
