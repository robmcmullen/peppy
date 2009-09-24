# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""

"""

import os, sys, re, copy
from cStringIO import StringIO

from peppy.editra.facade import *

from nose.tools import *

class testEditraLanguages(object):
    def setup(self):
        self.facade = EditraFacade()
        self.facade._extreg.LoadDefault()

    def testLangs(self):
        langs = self.facade.getAllEditraLanguages()

    def testPython(self):
        exts = self.facade.getExtensionsForLanguage("Python")
        assert "py" in exts
        assert "python" in exts

    def testXML(self):
        exts = self.facade.getExtensionsForLanguage("XML")
        assert "xml" in exts
        assert "xul" in exts

    def testAddXMLExtension(self):
        exts = self.facade.getExtensionsForLanguage("XML")
        print(exts)
        print(self.facade._extreg["XML"])
        self.facade.addExtensionForLanguage("XML", "abcxml")
        exts = self.facade.getExtensionsForLanguage("XML")
        print(exts)
        print(self.facade._extreg["XML"])
        assert "xml" in exts
        assert "xul" in exts
        assert "abcxml" in exts

    def testPeppyKeywords(self):
        mapping = {
            "Bash Shell Script": "Bash",
            "C#": "C#",
            "DOT": "Graphviz",
            "Makefile": "Makefile",
            "Objective C": "Objective C",
            "Tcl/Tk": "Tcl/Tk",
            }
        for editra, peppy in mapping.iteritems():
            eq_(peppy, self.facade.getPeppyModeKeyword(editra))

    def testPeppyFileNames(self):
        mapping = {
            "Bash Shell Script": "bash",
            "C#": "csharp",
            "DOT": "graphviz",
            "Makefile": "makefile",
            "Objective C": "objective_c",
            "Tcl/Tk": "tcl_tk",
            }
        for editra, peppy in mapping.iteritems():
            eq_(peppy, self.facade.getPeppyFileName(editra))
 
 
