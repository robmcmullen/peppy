import os,sys,re
import cPickle as pickle

from peppy.plugins.macro import *

from nose.tools import *

class TestMacro(object):
    def testPickle(self):
        macro = PythonScriptableMacro()
        eq_(macro.name, "untitled")
        macro.script = "pass"
        
        data = pickle.dumps(macro)
        eq_(data, "stuff")
