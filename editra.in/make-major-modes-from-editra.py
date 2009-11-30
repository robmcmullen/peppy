#!/usr/bin/env python

import os, shutil, sys, glob, imp
import __builtin__
import ConfigParser
from cStringIO import StringIO
from optparse import OptionParser

import wx.stc

__builtin__._ = str

sys.path.append("..")
from peppy.debug import *
from facade import *


facade = EditraFacade()

class_attr_template = '''    keyword = '%(keyword)s'
    editra_synonym = '%(lang)s'
    stc_lexer_id = %(lexer)s
    start_line_comment = %(start_comment)s
    end_line_comment = %(end_comment)s'''


classprefs_template = '''        StrParam('extensions', '%(extensions)s', fullwidth=True),'''
keyword_set_template = '''        StrParam('keyword_set_%d', unique_keywords[%d], hidden=False, fullwidth=True),'''


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
from peppy.editra.style_specs import unique_keywords

class %(class_name)sMode(FundamentalMode):
    """Stub major mode for editing %(keyword)s files.

    This major mode has been automatically generated and is a boilerplate/
    placeholder major mode.  Enhancements to this mode are appreciated!
    """
%(class_attrs)s
    
    icon = 'icons/page_white.png'
    
    default_classprefs = (
%(classprefs)s
       )


class %(class_name)sModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface for %(keyword)s
    """
   
    def getMajorModes(self):
        yield %(class_name)sMode
'''

# Global lists and dicts using my multiple processes
langs = facade.getAllEditraLanguages()
extra_properties = {}
syntax_style_specs = {}
keywords = {}
stc_lexer_id = {}
for lang in langs:
    keyword = facade.getPeppyModeKeyword(lang)
    #dprint(keyword)
    extra_properties[keyword] = facade.getEditraExtraProperties(lang)
    syntax_style_specs[keyword] = facade.getEditraSyntaxSpecs(lang)
    keywords[keyword] = facade.getEditraLanguageKeywords(lang)
    stc_lexer_id[keyword] = facade.getEditraSTCLexer(lang)

def findCommonKeywords(keywords):
    unique_keywords = []
    unique_id = 0
    keywords_text = {}
    keywords_mapping = {}
    for lang, keyword_dict in keywords.iteritems():
        if lang not in keywords_mapping:
            dprint("adding %s" % lang)
            keywords_mapping[lang] = {}
        try:
            for id, text in keyword_dict.iteritems():
                # keyword_spec is a tuple of int and string
                if text in keywords_text:
                    dprint("found common for %s, %d: %s" % (lang, id, keywords_text[text]))
                    keywords_mapping[lang][id] = keywords_text[text]
                else:
                    keywords_text[text] = unique_id
                    unique_keywords.append(text)
                    keywords_mapping[lang][id] = unique_id
                    unique_id += 1
        except (ValueError, TypeError):
            dprint(lang)
            dprint(keyword_spec_list)
            raise
        except KeyError:
            dprint(keywords_mapping.keys())
            raise
    dprint(keywords_mapping)
    return unique_keywords, keywords_mapping

unique_keywords, keywords_mapping = findCommonKeywords(keywords)



# Processing routines

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
            #dprint("found %s -> %s -> %s" % (lang, module_name, module_path))
            existing.append(lang)
        else:
            #dprint("CREATING %s -> %s -> %s" % (lang, module_name, module_path))
            missing.append(lang)
    return missing, existing

def getEditraInfo(lang):
    module_name = facade.getPeppyFileName(lang)
    syn = facade.getEditraSyntaxData(lang)
    keyword = facade.getPeppyModeKeyword(lang)
    vals = {
        'lang': lang,
        'keyword': keyword,
        'class_name': facade.getPeppyClassName(lang),
        'module_name': module_name,
        'extensions': " ".join(facade.getExtensionsForLanguage(lang)),
        'lexer': facade.getEditraSTCLexerName(lang),
        'start_comment': repr(facade.getEditraCommentChars(lang)[0]),
        'end_comment': repr(facade.getEditraCommentChars(lang)[1]),
        }
    vals['class_attrs'] = class_attr_template % vals
    classprefs = classprefs_template % vals
    order = sorted(keywords_mapping[keyword].iteritems())
    for keyword_set_id, unique_id in order:
        classprefs += "\n" + keyword_set_template % (keyword_set_id, unique_id)
    
    vals['classprefs'] = classprefs
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
    classtext = ClassText(text, lang)
    classtext.replace(vals)
    fh = open(module_path, 'w')
    fh.write(str(classtext))
    fh.close()

class ClassText(object):
    """Gets the class attribute section of the major mode class
    
    """
    def __init__(self, text, lang):
        self.header = ""
        self.class_attrs = ""
        self.classprefs = ""
        self.footer = ""
        self.lang = lang
        self.parse(text)
    
    def __str__(self):
        #return "Class Attribute Section: %s\nClass Preference Section: %s"% (self.class_attrs, self.classprefs)
        return self.header + self.class_attrs + self.classprefs + self.footer
    
    def parse(self, text):
        classmatch = "class %sMode(" % facade.getPeppyClassName(self.lang)
        #dprint(classmatch)
        state = "header"
        for line in text.splitlines(True):
            #dprint(line)
            if state == "header":
                if line.startswith(classmatch):
                    state = "in_class"
                else:
                    self.header += line
            if state == "in_class":
                if line.strip().startswith("keyword =") or line.strip().startswith("keyword="):
                    state = "class_attrs"
                else:
                    self.header += line
            if state == "class_attrs":
                if line.strip().startswith("default_classprefs"):
                    state = "classprefs"
                else:
                    self.class_attrs += line
            if state == "classprefs":
                if line.strip() == ")":
                    state = "footer"
                else:
                    self.classprefs += line
            if state == "footer":
                self.footer += line
    
    def replace(self, vals):
        """Replace any class attributes or classprefs with the new values
        
        """
        self.replaceImports()
        self.replaceClassAttrs(vals)
        self.replaceClassprefs(vals)
    
    def replaceImports(self):
        """Special case to add the unique_keywords dict to the list of imports
        
        In versions prior to r2412, the import statement for unique_keywords
        from peppy.editra.style_specs didn't exist.  Now that keywords can be
        modified by the user, the import statement must be included because
        the StrParams reference the unique_keywords dict to supply defaults
        for the preferences.
        """
        extra = "from peppy.editra.style_specs import unique_keywords"
        try:
            self.header.index(extra)
        except ValueError:
            dprint("Replacing imports for %s" % self.lang)
            index = self.header.index("from peppy.fundamental import")
            self.header = self.header[0:index] + extra + "\n" + self.header[index:]
    
    def replaceClassAttrs(self, vals):
        newattrs = vals['class_attrs']
        keywords = {}
        for attrline in newattrs.splitlines():
            keyword, value = attrline.split("=")
            keyword = keyword.strip()
            keywords[keyword] = attrline
        lines = self.class_attrs.splitlines(True)
        newlines = ""
        for line in lines:
            splitted = line.split("=")
            if len(splitted) > 1 and splitted[0].strip() in keywords:
                # Replace the keyword with the new value
                #newlines += keywords[splitted[0]]
                #del keywords[splitted[0]]
                pass
            else:
                newlines += line
        self.class_attrs = newattrs + "\n" + newlines
    
    def replaceClassprefs(self, vals):
        newprefs = vals['classprefs']
        keywords = set()
        for attrline in newprefs.splitlines():
            keyword, value = attrline.split(",", 1)
            keywords.add(keyword)
        lines = self.classprefs.splitlines(True)
        newlines = ""
        # the default_classprefs should start it out
        newprefs = lines[0] + newprefs
        for line in lines[1:]:
            splitted = line.split(",")
            if len(splitted) > 1 and splitted[0] in keywords:
                pass
            else:
                newlines += line
        self.classprefs = newprefs + "\n" + newlines
        
        

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
    #dprint("Processing sample text")
    langs = facade.getAllEditraLanguages()
    sample_text = {}
    for lang in langs:
        keyword = facade.getPeppyModeKeyword(lang)
        sample_text[keyword] = facade.getEditraLanguageSampleText(lang)
    
    import pprint
    pp = pprint.PrettyPrinter()
    fh = open(filename, "w")
    fh.write("# Generated file containing the sample text for Editra modes\n")
    fh.write("sample_text=")
    fh.write(pp.pformat(sample_text))
    fh.close()

def processStyleSpecs(filename):
    #dprint("Processing style specs")
    import pprint
    pp = pprint.PrettyPrinter()
    fh = open(filename, "w")
    fh.write("# Generated file containing Editra style defaults for those major modes based\n# on Editra style files\n")
    fh.write("\nstc_lexer_id=")
    fh.write(pp.pformat(stc_lexer_id))
    fh.write("\nsyntax_style_specs=")
    fh.write(pp.pformat(syntax_style_specs))
    fh.write("\nextra_properties=")
    fh.write(pp.pformat(extra_properties))
    if keywords_mapping:
        fh.write("\nkeywords_mapping=")
        fh.write(pp.pformat(keywords_mapping))
    fh.write("\nunique_keywords=")
    fh.write(pp.pformat(unique_keywords))
    fh.write("\n")
    fh.close()



if __name__ == "__main__":
    usage="usage: %prog [-s dir] [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-o", action="store", dest="outputdir",
                      default="../peppy/major_modes", help="output directory")
    parser.add_option("--sample-text", action="store", dest="sample_text_file",
                      default="../peppy/editra/sample_text.py", help="dict containing sample text for each editra language")
    parser.add_option("--style-spec", action="store", dest="style_spec_file",
                      default="../peppy/editra/style_specs.py", help="dict containing sample text for each editra language")
    (options, args) = parser.parse_args()

    process(options.outputdir)
    processSampleText(options.sample_text_file)
    processStyleSpecs(options.style_spec_file)
