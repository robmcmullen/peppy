"""
Testing dynamic class creation used in the chatbots plugin to create
an Action for each chatbot present in the nltk_lite toolkit.
"""

import os, sys, re, copy
from cStringIO import StringIO

from nose.tools import *

class testHexMatch(object):
    def setup(self):
        self.re = re.compile("(0[xX][0-9a-fA-F]+)")
        self.hre = re.compile("[0-9a-fA-F]+h")

    def testMatch(self):
        eq_("0x0", self.re.match("0x0").group(1))
        eq_("0x0ff", self.re.match("0x0ff").group(1))
        eq_("0xba5e", self.re.match("0xba5e").group(1))
        eq_("0X0", self.re.match("0X0").group(1))
        eq_("0X0ff", self.re.match("0X0ff").group(1))
        eq_("0Xba5e", self.re.match("0Xba5e").group(1))
        eq_(None, self.re.match("allyourbase"))
        
        # FIXME: don't know that the following is the desired behavior
        eq_("0xbe", self.re.match("0xbelongtous").group(1))
        
    def testSub(self):
        eq_("0x1", self.hre.sub(lambda s: "0x%s" % s.group(0)[:-1], "1h"))
        eq_("0xff", self.hre.sub(lambda s: "0x%s" % s.group(0)[:-1], "ffh"))
        eq_("0x1 0x2 0xff 0xffff 0x12 55 0x89", self.hre.sub(lambda s: "0x%s" % s.group(0)[:-1], "1h 2h ffh 0xffff 12h 55 0x89"))
