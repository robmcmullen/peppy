import os,sys,re

from peppy.lib.bufferedreader import *

from nose.tools import *

from utils import *

class TestBufferedReplacementReader:
    def setup(self):
        self.fh = open(localfile('data/samplefile.txt'), 'rb')
        self.s = '0123456789'
        self.b = BufferedReplacementReader(self.fh, self.s)
        
    def test_basic(self):
        eq_('01', self.b.read(2))
        eq_('2345', self.b.read(4))
        eq_('6789klmnop', self.b.read(10))
        
    def test_seek(self):
        eq_('01', self.b.read(2))
        eq_('2345', self.b.read(4))
        self.b.seek(0)
        eq_('01', self.b.read(2))
        eq_('2345', self.b.read(4))
        eq_('6789klmnop', self.b.read(10))
        self.b.seek(1)
        eq_('1', self.b.read(1))
        eq_('2345', self.b.read(4))
        eq_('6789klmnop', self.b.read(10))
        self.b.seek(len(self.s))
        eq_('klmnop', self.b.read(6))
        
class TestBufferedReader:
    def setup(self):
        self.fh = open(localfile('data/samplefile.txt'), 'rb')
        self.b = BufferedReader(self.fh, 10)
        
    def test_basic(self):
        eq_('ab', self.b.read(2))
        eq_('cdef', self.b.read(4))
        eq_('ghijklmnop', self.b.read(10))
        
    def test_seek(self):
        eq_('ab', self.b.read(2))
        eq_('cdef', self.b.read(4))
        self.b.seek(0)
        eq_('ab', self.b.read(2))
        eq_('cdef', self.b.read(4))
        eq_('ghijklmnop', self.b.read(10))
        self.b.seek(1)
        eq_('b', self.b.read(1))
        eq_('cdef', self.b.read(4))
        eq_('ghijklmnop', self.b.read(10))
        self.b.seek(self.b.len)
        eq_('klmnop', self.b.read(6))
