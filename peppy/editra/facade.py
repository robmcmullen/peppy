# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time

import wx
import wx.stc

from peppy.editra import *
import peppy.editra.util as util
from peppy.debug import *


class EditraFacade(object):
    singleton_instance = None
    first = True
    
    # Some editra names have historical peppy names that I'm continuing to use
    editra_to_peppy_modenames = {
        'Bash Shell Script': 'Bash',
        'DOT': 'Graphviz',
        'C-Shell Script': 'Csh',
        'Diff File': 'Diff',
        'Korn Shell Script': 'Ksh',
        'Plain Text': 'Text',
        }

    def __init__(self, config=None):
        """Initialize a syntax manager. If the optional
        value config is set the mapping of extensions to
        lexers will be loaded from a config file.
        @keyword config: path of config file to load file extension config from

        """
        if EditraFacade.first:
            object.__init__(self)
            EditraFacade.first = False
            self._synmgr = syntax.SyntaxMgr()
            self._extreg = synextreg.ExtensionRegister()
            self.LOG = dprint
            self.rebuild()

    def __new__(cls, config=None):
        """Ensure only a single instance is shared amongst
        all objects.
        @return: class instance

        """
        if cls.singleton_instance is None:
            cls.singleton_instance = object.__new__(cls)
        return cls.singleton_instance
    
    def rebuild(self):
        # Editra maintains a canonical list of languages that it supports that
        # doesn't exactly map to peppy.  However, this canonical list should be
        # used in place of the peppy keyword when directly referencing Editra
        # languages.
        self.canonical_langs = []
        
        # _synmgr._extreg is an ExtensionRegister instance that is a dictionary
        # from the Editra pretty name to the extension list supported by that
        # name.  Editra doesn't provide a direct mapping from the pretty name to
        # the primary extension, however, so this is created here.
        self.editra_lang_to_ext = {}
        self.editra_ext_to_lang = {}
        
        for lang, exts in self._extreg.iteritems():
            if lang == "XML":
                print("%s: %s" % (lang, exts))
            self.canonical_langs.append(lang)
            self.editra_lang_to_ext[lang] = exts[0]
            self.editra_lang_to_ext[lang.replace(' ', '_')] = exts[0]
            for ext in exts:
                self.editra_ext_to_lang[ext] = lang
        self.canonical_langs.sort()
    
    def getEditraExtFromLang(self, lang):
        """Get the Editra extension given the keyword of the major mode
        
        Editra uses the filename extension as the basis for most of its
        lookups, but also has a pretty-printing name.  For instance, 'Python'
        is the pretty name of python mode, but Editra uses "py" as its main
        designator for the mode internally.
        """
        return self.editra_lang_to_ext.get(lang, lang)

    def getEditraSyntaxData(self, lang):
        """Get the Editra syntax data given the keyword of the major mode
        
        This method gets the syntax data based on the peppy keyword, which is
        designed to be the same as the Editra pretty-printing mode in most
        cases.
        """
        ext = self.getEditraExtFromLang(lang)
        #dprint("after: %s" % ext)
        syn_data = self.SyntaxData(ext)
        return syn_data

    def getEditraSyntaxProperties(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        try:
            props = syn_data[syntax.PROPERTIES]
        except KeyError:
            #self.LOG("[stc] [exception] No Extra Properties to Set")
            props = []
        return props
    
    def isEditraLanguage(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        lexer = syn_data[syntax.LEXER]
        return lexer != wx.stc.STC_LEX_NULL
    
    def getAllEditraLanguages(self):
        exts = self.canonical_langs
        dprint(exts)
        return exts
    
    def getExtensionsForLanguage(self, lang):
        exts = self._extreg[lang]
        dprint(exts)
        return exts
    
    def addExtensionForLanguage(self, lang, ext):
        self._extreg.Associate(lang, ext)
        self.rebuild()
    
    def getPeppyModeKeyword(self, lang):
        try:
            return self.editra_to_peppy_modenames[lang]
        except KeyError:
            return lang
    
    def getPeppyClassName(self, lang):
        lang = self.getPeppyModeKeyword(lang)
        lang = lang.replace("_", "").replace(" ", "").replace("/", "")
        return lang
    
    def getPeppyPythonName(self, lang):
        lang = self.getPeppyModeKeyword(lang)
        lang = lang.replace("-", "_").replace(" ", "_").replace("/", "_").replace("#", "sharp")
        return lang
    
    def getPeppyFileName(self, lang):
        lang = self.getPeppyPythonName(lang).lower()
        return lang
