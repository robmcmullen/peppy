import os,sys,re
from cStringIO import StringIO

import wx.stc
from mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.python_mode import *
from peppy.plugins.text_transforms import *
from peppy.debug import *

import peppy.lib.PyParse as PyParse

from nose.tools import *


test_cases = """\
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
        else:
            list = (1, 2, 3|
--

----------------------------------------
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
|
--

----------------------------------------
class blah:
    def stuff:
        if blah:
            stuff = "BLAH!!!!\\
aoeua oeuahoenutha oeuhaoehu asoehus"
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
         # comments in here
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
            return
|
--

----------------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
          class:
          def:
    '''
    def stuff:
        if blah:
            stuff = "BLAH!!!!"
        else:|
--

----------------------------------------
# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://peppy.flipturn.org for more info
'''FLAASH control mode

Major mode to edit FLAASH config files, run FLAASH, and manage the results.
'''

import os, struct, time, re
from cStringIO import StringIO
import locale

from numpy.core.numerictypes import *

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.filebrowsebutton import FileBrowseButtonWithHistory, DirBrowseButton

from peppy.yapsy.plugins import *
from peppy.iofilter import *
from peppy.menu import *
from peppy.major import *
from peppy.about import SetAbout
from peppy.lib.processmanager import *
from peppy.lib.userparams import *
|if blah:

--

---------------------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
    blaoeuaoeua
|
    '''
--

----------------------
class blah:
    '''euanoe usnahoeunahoesnuhaoe
      blaoeuaoeua

|
    '''
--

------------------
class blah:
    stuff = "aoeuaoeu\\
aoeu aoeuhsa oesun aonsehu asoeu\\
|
--

"""

def pyparseit():
    '''
    inside triple quotes
    '''
    stc = getSTC(stcclass=PythonMode, lexer="Python")
    
    tests = splittests(test_cases)
    dprint(len(tests))
    for test in tests:
        prepareSTC(stc, test[0])
    
        indent = stc.findIndent(stc.GetCurrentLine())
        indentstr = stc.GetIndentString(indent)
        dprint("indent = '%s'" % indentstr)
        print stc.GetText()
        print indentstr+"^"

if __name__ == "__main__":
    pyparseit()
    