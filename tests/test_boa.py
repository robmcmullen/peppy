import os,sys,re
from cStringIO import StringIO

from peppy.boa import *

from nose.tools import *

class wxConfigAdapter(object):
    def __init__(self):
        self.fh=StringIO()

    def SetPath(self, path):
        pass

    def Write(self, key, value):
        self.fh.write("%s=%s\n" % (key,value))

    def getvalue(self):
        return self.fh.getvalue()

class TestBoaConfig:
    def testDefaultConfig(self):
        fh = wxConfigAdapter()
        writeUserConfigFile(fh)
        text = fh.getvalue()
        print text
        assert len(text)>0
        assert text.find('common.defs.mac')>=0
        assert text.find('common.defs.msw')>=0
        assert text.find('common.defs.gtk')>=0
