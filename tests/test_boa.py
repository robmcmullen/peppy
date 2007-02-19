import os,sys,re
from cStringIO import StringIO

from peppy.boa import *

from nose.tools import *

class TestBoaConfig:
    def testDefaultConfig(self):
        fh = StringIO()
        writeUserConfigFile(fh)
        text = fh.getvalue()
        assert len(text)>0
        assert text.find('common.defs.mac')>=0
        assert text.find('common.defs.msw')>=0
        assert text.find('common.defs.gtk')>=0
