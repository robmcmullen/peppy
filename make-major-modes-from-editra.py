#!/usr/bin/env python

import os, shutil, sys, glob, imp
import __builtin__
import ConfigParser
from cStringIO import StringIO
from optparse import OptionParser

__builtin__._ = str

from peppy.debug import *
from peppy.editra.facade import *


facade = EditraFacade()

template = '''# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""%(lang)s programming language editing support.

Major mode for editing %(lang)s files.

Supporting actions and minor modes should go here only if they are uniquely
applicable to this major mode and can't be used in other major modes.  If
actions can be used with multiple major modes, they should be put in a
separate plugin in the peppy/plugins directory.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

class %(class_name)sMode(FundamentalMode):
    """Stub major mode for editing %(keyword)s files.

    This major mode has been automatically generated and is a boilerplate/
    placeholder major mode.  Enhancements to this mode are appreciated!
    """
    keyword = '%(keyword)s'
    editra_synonym = '%(lang)s'
    
    icon = 'icons/page_white.png'
    
    default_classprefs = (
        StrParam('extensions', '%(extensions)s', fullwidth=True),
       )


class %(class_name)sModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface for %(keyword)s
    """
   
    def getMajorModes(self):
        yield %(class_name)sMode
'''


def process(destdir):
    missing, existing = getDefinedModes(destdir)
    for mode in missing:
        convertEditraMode(destdir, mode)
    for mode in existing:
        updateEditraMode(destdir, mode)

def getDefinedModes(destdir):
    langs = facade.getAllEditraLanguages()
    missing = []
    existing = []
    for lang in langs:
        module_name = facade.getPeppyFileName(lang)
        module_path = os.path.join(destdir, module_name + ".py")
        if os.path.exists(module_path):
            dprint("found %s -> %s -> %s" % (lang, module_name, module_path))
            existing.append(lang)
        else:
            dprint("CREATING %s -> %s -> %s" % (lang, module_name, module_path))
            missing.append(lang)
    return missing, existing

def getEditraInfo(lang):
    module_name = facade.getPeppyFileName(lang)
    
    vals = {
        'lang': lang,
        'keyword': facade.getPeppyModeKeyword(lang),
        'class_name': facade.getPeppyClassName(lang),
        'module_name': module_name,
        'extensions': " ".join(facade.getExtensionsForLanguage(lang)),
        }
    return module_name, vals

def convertEditraMode(destdir, lang):
    module_name, vals = getEditraInfo(lang)
    module_path = os.path.join(destdir, module_name + ".py")
    text = template % vals
    #print(text)
    fh = open(module_path, 'w')
    fh.write(text)
    fh.close()
    generatePluginFile(destdir, lang)

def updateEditraMode(destdir, lang):
    module_name, vals = getEditraInfo(lang)
    module_path = os.path.join(destdir, module_name + ".py")
    fh = open(module_path, 'r')
    text = fh.read()
    fh.close()

def generatePluginFile(destdir, lang):
    module_name = facade.getPeppyFileName(lang)
    plugin_path = os.path.join(destdir, module_name + ".peppy-plugin")
    
    conf = ConfigParser.ConfigParser()
    conf.add_section("Core")
    conf.set("Core", "Name", "%s Mode" % facade.getPeppyModeKeyword(lang))
    conf.set("Core", "Module", module_name)
    conf.add_section("Documentation")
    conf.set("Documentation", "Author", "Rob McMullen")
    conf.set("Documentation", "Version", "0.1")
    conf.set("Documentation", "Website", "http://www.flipturn.org/peppy")
    conf.set("Documentation", "Description", "Major mode for editing %s files" % facade.getPeppyModeKeyword(lang))
    
    fh = open(plugin_path, "w")
    conf.write(fh)

def processSampleText(filename):
    dprint("Processing sample text")
    missing, existing = getDefinedModes("")
    sample_text = {}
    for lang in missing:
        sample_text[lang] = facade.getEditraLanguageSampleText(lang)
    for lang in existing:
        sample_text[lang] = facade.getEditraLanguageSampleText(lang)
    
    import pprint
    pp = pprint.PrettyPrinter()
    fh = open(filename, "w")
    fh.write("# Generated file containing the sample text for Editra modes\n")
    fh.write("sample_text=")
    fh.write(pp.pformat(sample_text))
    fh.close()


if __name__ == "__main__":
    usage="usage: %prog [-s dir] [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-o", action="store", dest="outputdir",
                      default="peppy/major_modes", help="output directory")
    parser.add_option("--sample-text", action="store", dest="sample_text_file",
                      default="peppy/editra/sample_text.py", help="dict containing sample text for each editra language")
    (options, args) = parser.parse_args()

    process(options.outputdir)
    processSampleText(options.sample_text_file)
