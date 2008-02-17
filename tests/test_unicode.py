import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *
from peppy.debug import *

from nose.tools import *

class TestFundamentalUnicode(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="Plain Text")
        self.utf8 = '# -*- coding: UTF-8 -*-\naacute:\xc3\xa1 ntilde:\xc3\xb1'
        self.latin1= '# -*- coding: latin-1 -*-\n' + ''.join([chr(i) for i in range(160, 255)])

    def testUTF8(self):
        self.stc.encoding = detectEncoding(self.utf8)
        print self.stc.encoding
        self.stc.decodeText(self.utf8)
        self.stc.prepareEncoding()
        assert self.utf8 == self.stc.refstc.encoded
    
    def testChangeLatin(self):
        self.stc.encoding = detectEncoding(self.utf8)
        print self.stc.encoding
        self.stc.decodeText(self.utf8)
        unicode1 = self.stc.GetLine(1)
        print repr(unicode1)
        start = self.stc.FindText(0, self.stc.GetLength(), 'UTF-8')
        self.stc.SetTargetStart(start)
        self.stc.SetTargetEnd(start+5)
        self.stc.ReplaceTarget('latin-1')
        self.stc.prepareEncoding()
        print self.stc.refstc.encoded
        unicode2 = self.stc.GetLine(1)
        print repr(unicode2)
        assert unicode1 == unicode2

    def testLatin1(self):
        self.stc.encoding = detectEncoding(self.latin1)
        print repr(self.latin1)
        utf8 = unicode(self.latin1, "iso-8859-1").encode('utf-8')
        print repr(utf8)
        print repr(utf8.decode('utf-8'))
        print repr(self.latin1.decode('latin-1'))
        self.stc.decodeText(self.latin1)
        print repr(self.stc.GetText())
        self.stc.prepareEncoding()
        print "encoded: " + repr(self.stc.refstc.encoded)
        assert self.latin1 == self.stc.refstc.encoded