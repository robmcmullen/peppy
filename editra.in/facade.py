# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time

import wx
import wx.stc

from peppy.debug import *
from syntax.synextreg import *
from syntax.syntax import *


class EditraFacade(object):
    singleton_instance = None
    first = True
    
    # Some editra names have historical peppy names that I'm continuing to use
    editra_to_peppy_keywords = {
        'Bash Shell Script': 'Bash',
        'DOT': 'Graphviz',
        'C-Shell Script': 'Csh',
        'CPP': 'C++',
        'Diff File': 'DiffEdit',
        'Korn Shell Script': 'Ksh',
        'Plain Text': 'Text',
        }
    
    stc_lexer_name = {}
    for name in [name for name in dir(wx.stc) if name.startswith("STC_LEX")]:
        lexer = getattr(wx.stc, name)
        stc_lexer_name[lexer] = name


    def __init__(self, config=None):
        """Initialize a syntax manager. If the optional
        value config is set the mapping of extensions to
        lexers will be loaded from a config file.
        @keyword config: path of config file to load file extension config from

        """
        if EditraFacade.first:
            object.__init__(self)
            EditraFacade.first = False
            self._synmgr = SyntaxMgr()
            self._extreg = ExtensionRegister()
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
        syn_data = self._synmgr.SyntaxData(ext)
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
        #dprint(exts)
        return exts
    
    def getExtensionsForLanguage(self, lang):
        exts = self._extreg[lang]
        #dprint(exts)
        return exts
    
    def addExtensionForLanguage(self, lang, ext):
        self._extreg.Associate(lang, ext)
        self.rebuild()
    
    def getPeppyModeKeyword(self, lang):
        try:
            return self.editra_to_peppy_keywords[lang]
        except KeyError:
            return lang
    
    def getPeppyClassName(self, lang):
        lang = self.getPeppyModeKeyword(lang)
        lang = lang.replace("_", "").replace(" ", "").replace("/", "").replace("#", "sharp").replace("++", "PlusPlus")
        if lang[0].isdigit():
            lang = "_" + lang
        return lang
    
    def getPeppyPythonName(self, lang):
        lang = self.getPeppyModeKeyword(lang)
        lang = lang.replace("-", "_").replace(" ", "_").replace("/", "_").replace("#", "sharp").replace("++", "pp")
        if lang[0].isdigit():
            lang = "_" + lang
        return lang
    
    def getPeppyFileName(self, lang):
        lang = self.getPeppyPythonName(lang).lower()
        return lang
    
    def getEditraLanguageSampleText(self, lang):
        """Get the sample text Editra uses in the style dialog
        
        The sample text for each of the Editra languages is stored in the
        editra/tests directory.
        """
        # The editra filename used for sample text is not quite the same as
        # the peppy filename.
        fname = lang.replace(u" ", u"_").replace(u"/", u"_").lower()
        fname = fname.replace('#', 'sharp')
        try:
            import glob
            fname = glob.glob(os.path.join(os.path.dirname(__file__), 'tests',  fname) + ".*")[0]
            fh = open(fname)
            text = fh.read()
        except IndexError:
            text = ""
        return text

    def getEditraCommentChars(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        if COMMENT in syn_data:
            chars = syn_data[COMMENT]
        else:
            chars = []
        # make sure default chars exist
        chars.extend(["", ""])
        return chars[0], chars[1]

    def getEditraSTCLexer(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        return syn_data[LEXER]

    def getEditraSTCLexerName(self, lang):
        lexer = self.getEditraSTCLexer(lang)
        return "wx.stc.%s" % self.stc_lexer_name[lexer]

    def getEditraExtraProperties(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        if PROPERTIES in syn_data:
            return syn_data[PROPERTIES]
        return None

    def getEditraSyntaxSpecs(self, lang):
        syn_data = self.getEditraSyntaxData(lang)
        converted = []
        try:
            specs = syn_data[SYNSPEC]
            for syn in specs:
                # precompute the style number
                #dprint("%s: %s, %s" % (lang, syn[0], syn[1]))
                if isinstance(syn[0], basestring):
                    style_number = getattr(wx.stc, syn[0])
                else:
                    style_number = syn[0]
                converted.append((style_number, syn[1]))
        except KeyError:
            pass
        return converted

    def getEditraLanguageKeywords(self, lang):
        """Change the Editra list-of-tuples keyword description into a dict
        
        The return dict is keyed on the keyword set number.
        """
        syn_data = self.getEditraSyntaxData(lang)
        if KEYWORDS in syn_data:
            keyword_dict = {}
            keywords_list = syn_data[KEYWORDS]
            for keywordset, keywords in keywords_list:
                keyword_dict[keywordset] = keywords
            return keyword_dict
        return {}
