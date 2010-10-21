import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.major_modes.python import *
from peppy.plugins.text_transforms import *
from peppy.debug import *

from nose.tools import *

class TestFundamentalUnicode(object):
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="Plain Text")
        self.utf8 = '# -*- coding: UTF-8 -*-\naacute:\xc3\xa1 ntilde:\xc3\xb1'
        self.utf8_bom = '\xef\xbb\xbf\naacute:\xc3\xa1 ntilde:\xc3\xb1'
        self.latin1= '# -*- coding: latin-1 -*-\n' + ''.join([chr(i) for i in range(160, 255)])
        self.latin1_unmarked= ''.join([chr(i) for i in range(160, 255)])

    def testUTF8(self):
        text = self.utf8
        self.stc.encoding, self.stc.refstc.bom = detectEncoding(text)
        print self.stc.encoding
        self.stc.decodeText(text)
        self.stc.prepareEncoding()
        assert text == self.stc.refstc.encoded
    
    def testUTF8BOM(self):
        text = self.utf8_bom
        self.stc.encoding, self.stc.refstc.bom = detectEncoding(text)
        print self.stc.encoding
        self.stc.decodeText(text)
        self.stc.prepareEncoding()
        assert text == self.stc.refstc.encoded
    
    def testChangeLatin(self):
        self.stc.refstc.encoding, self.stc.refstc.bom = detectEncoding(self.utf8)
        print self.stc.refstc.encoding
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
        self.stc.refstc.encoding, self.stc.refstc.bom = detectEncoding(self.latin1)
        print repr(self.latin1)
        utf8 = unicode(self.latin1, "iso-8859-1").encode('utf-8')
        print repr(utf8)
        print repr(utf8.decode('utf-8'))
        print repr(self.latin1.decode('latin-1'))
        self.stc.decodeText(self.latin1)
        print repr(self.stc.GetText())
        print self.stc.refstc.encoding
        self.stc.prepareEncoding()
        print "encoded: " + repr(self.stc.refstc.encoded)
        assert self.latin1 == self.stc.refstc.encoded

    def testLatin1Unmarked(self):
        self.stc.refstc.encoding, self.stc.refstc.bom = detectEncoding(self.latin1_unmarked)
        print repr(self.latin1_unmarked)
        utf8 = self.latin1_unmarked.decode('latin-1')
        print repr(utf8)
        print repr(utf8.encode('latin-1'))
        assert utf8.encode('latin-1') == self.latin1_unmarked
        self.stc.decodeText(self.latin1_unmarked)
        print repr(self.stc.GetText())
        # There's no encoding marker in the text, so there shouldn't be an
        # encoding listed
        assert self.stc.refstc.encoding == None
        self.stc.prepareEncoding()
        print "encoded: " + repr(self.stc.refstc.encoded)
        assert self.latin1_unmarked == self.stc.refstc.encoded
