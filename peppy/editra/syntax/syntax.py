###############################################################################
# Name: syntax.py                                                             #
# Purpose: Manage and dynamically load/provide syntax on request from editor. #
#          Also manages the mappings of file extensions to lexers.            #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: syntax.py                                                             #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# Toolkit for managing the importing of syntax modules and providing the data #
# to the requesting text control.                                             #
#                                                                             #
# DETAIL:                                                                     #
# Since in Python Modules are only loaded once and maintain a single instance #
# across a single program. This module is used as a storage place for         #
# checking what syntax has already been loaded to facilitate a speedup of     #
# setting lexer values.                                                       #
#                                                                             #
# The use of this system also keeps the program from preloading all syntax    #
# data for all supported languages. The use of Python modules for the config  #
# files was made because Python is dynamic so why not use that feature to     #
# dynamically load configuration data. Since they are Python modules they can #
# also supply some basic functions for this module to use in loading different#
# dialects of a particular language.                                          #
#                                                                             #
# One of the driving reasons to move to this system was that the user of the  #
# editor is unlikely to be editting source files for all supported languages  #
# at one time, so there is no need to preload all data for all languages when #
# the editor starts up. Also in the long run this will be a much easier to    #
# maintain and enhance component of the editor than having all this data      #
# crammed into the text control class. The separation of data from control    #
# will also allow for user customization and modification to highlighting     #
# styles.                                                                     #
#                                                                             #
# METHODS:                                                                    #
# - IsModLoaded: Check if specified syntax module has been loaded.            #
# - SyntaxData: Returns the required syntax/lexer related data for setting up #
#               and configuring the lexer for a particular language.          #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: syntax.py 609 2007-10-08 06:54:00Z CodyPrecord $"
__revision__ = "$Revision: 609 $"

#-----------------------------------------------------------------------------#
# Dependencies
import wx
import os
import sys
import synglob

#-----------------------------------------------------------------------------#
# Data Objects / Constants

# Used to index the tuple returned by getting data from EXT_REG
LANG_ID    = 0
LEXER_ID   = 1
MODULE     = 2

# Constants for getting values from SyntaxData's return dictionary
KEYWORDS   = 0    # Keyword set(s)
LEXER      = 1    # Lexer to use
SYNSPEC    = 2    # Highligter specs
PROPERTIES = 3    # Extra Properties
LANGUAGE   = 4    # Language ID
COMMENT    = 5    # Gets the comment characters pattern

_ = wx.GetTranslation
#-----------------------------------------------------------------------------#

class SyntaxMgr(object):
    """Class Object for managing loaded syntax data. The manager
    is only created once as a singleton and shared amongst all
    editor windows
    @status: initial implimentation

    """
    instance = None
    first = True
    def __init__(self, config=None):
        """Initialize a syntax manager. If the optional
        value config is set the mapping of extensions to
        lexers will be loaded from a config file.
        @keyword config: path of config file to load file extension config from

        """
        if self.first:
            object.__init__(self)
            self.first = False
            self._extreg = ExtensionRegister()
            self._config = config
            if self._config:
                self._extreg.LoadFromConfig(self._config)
            else:
                self._extreg.LoadDefault()
            self._loaded = dict()

    def __new__(cls, *args, **kargs):
        """Ensure only a single instance is shared amongst
        all objects.
        @return: class instance

        """
        if not cls.instance:
            cls.instance = object.__new__(cls, *args, **kargs)
        return cls.instance

    def _ExtToMod(self, ext):
        """Gets the name of the module that is is associated
        with the given extension or None in the event that there
        is no association or that the association is plain text.
        @param ext: extension string to lookup module for

        """
        ftype = self._extreg.FileTypeFromExt(ext)
        lexdat = synglob.LANG_MAP.get(ftype)
        mod = None
        if lexdat:
            mod = lexdat[2]
        return mod

    def GetLangId(self, ext):
        """Gets the language Id that is associated with the file
        extension.
        @param ext: extension to get lang id for

        """
        ftype = self._extreg.FileTypeFromExt(ext)
        return synglob.LANG_MAP[ftype][0]

    def IsModLoaded(self, modname):
        """Checks if a module has already been loaded
        @param modname: name of module to lookup

        """
        if modname in sys.modules or modname in self._loaded:
            return True
        else:
            return False

    def LoadModule(self, modname):
        """Dynamically loads a module by name. The loading is only
        done if the modules data set is not already being managed
        @param modname: name of syntax module to load

        """
        if modname == None:
            return False
        if not self.IsModLoaded(modname):
            try:
                self._loaded[modname] = __import__(modname, globals(), 
                                                   locals(), [''])
            except ImportError:
                return False
        return True

    def SaveState(self):
        """Saves the current configuration state of the manager to
        disk for use in other sessions.
        @return: whether save was successful or not

        """
        if not self._config or not os.path.exists(self._config):
            return False
        path = os.path.join(self._config, self._extreg.config)
        file_h = file(path, "wb")
        file_h.write(str(self._extreg))
        file_h.close()
        return True

    def SyntaxData(self, ext):
        """Fetches the language data based on a file extention string.
        The file extension is used to look up the default lexer actions from the
        EXT_REG dictionary (@see L{synglob.py}).
        @param ext: a string representing the file extension
        @return: Returns a Dictionary of Lexer Config Data

        """
        # The Return Value
        syn_data = dict()
        lex_cfg = synglob.LANG_MAP[self._extreg.FileTypeFromExt(ext)]

        syn_data[LEXER] = lex_cfg[LEXER_ID]
        if lex_cfg[LANG_ID] == synglob.ID_LANG_TXT:
            syn_data[LANGUAGE] = lex_cfg[LANG_ID]

        # Check if module is loaded and load if necessary
        if not self.LoadModule(lex_cfg[MODULE]):
            # Bail out as nothing else can be done at this point
            return syn_data

        # This little bit of code fetches the keyword/syntax 
        # spec set(s) from the specified module
        mod = self._loaded[lex_cfg[MODULE]]  #HACK
        syn_data[KEYWORDS] = mod.Keywords(lex_cfg[LANG_ID])
        syn_data[SYNSPEC] = mod.SyntaxSpec(lex_cfg[LANG_ID])
        syn_data[PROPERTIES] = mod.Properties(lex_cfg[LANG_ID])
        syn_data[LANGUAGE] = lex_cfg[LANG_ID]
        syn_data[COMMENT] = mod.CommentPattern(lex_cfg[LANG_ID])
        return syn_data

#-----------------------------------------------------------------------------#

class ExtensionRegister(dict):
    """A data storage class for managing mappings of
    file types to file extentions. The register is created
    as a singleton.
    @status: initial implimentation

    """
    instance = None
    first = True
    config = u'synmap'
    def __init__(self):
        """Initializes the register"""
        if self.first:
            self.first = False
            self.LoadDefault()

    def __new__(cls, *args, **kargs):
        """Maintain only a single instance of this object
        @return: instance of this class

        """
        if not cls.instance:
            cls.instance = dict.__new__(cls, *args, **kargs)
        return cls.instance

    def __missing__(self, key):
        """Return the default value if an item is not found
        @return: txt extension for plain text

        """
        return u'txt'

    def __setitem__(self, i, y):
        """Ensures that only one filetype is associated with an extension
        at one time. The behavior is that more recent settings override
        and remove associations from older settings.
        @param i: key to set
        @param y: value to set

        """
        if not isinstance(y, list):
            raise TypeError, "Extension Register Expects a List"
        for key, val in self.iteritems():
            for item in y:
                if item in val:
                    val.pop(val.index(item))
        y.sort()
        dict.__setitem__(self, i, [x.strip() for x in y])

    def __str__(self):
        """Converts the Register to a string that is formatted
        for output to a config file.
        @return the register as a string

        """
        keys = self.keys()
        keys.sort()
        tmp = list()
        for key in keys:
            tmp.append("%s=%s" % (key, u':'.join(self.__getitem__(key))))
        return os.linesep.join(tmp)

    def Associate(self, ftype, ext):
        """Associate a given file type with the given file extension(s).
        The ext parameter can be a string of space separated extensions
        to allow for multiple associations at once.
        @param ftype: file type description string
        @param ext: file extension to associate
        
        """
        assoc = self.get(ftype, None)
        exts = ext.strip().split()
        if assoc:
            for x in exts:
                if x not in assoc:
                    assoc.append(x)
        else:
            assoc = list(set(exts))
        assoc.sort()
        self.__setitem__(ftype, assoc)

    def Disassociate(self, ftype, ext):
        """Disassociate a file type with a given extension or space
        separated list of extensions.
        @param ftype: filetype description string
        @param ext: extension to disassociate

        """
        to_drop = ext.strip().split()
        assoc = self.get(ftype, None)
        if assoc:
            for item in to_drop:
                if item in assoc:
                    assoc.pop([assoc.index(item)])
            self.__setitem__(ftype, assoc)
        else:
            pass

    def FileTypeFromExt(self, ext):
        """Returns the file type that is associated with
        the extension. If no association is found Plain Text
        will be returned by default.
        @param ext: extension to lookup

        """
        for key, val in self.iteritems():
            if ext in val:
                return key
        return synglob.LANG_TXT

    def GetAllExtensions(self):
        """Returns a sorted list of all extensions registered
        @return: list of all registered extensions

        """
        ext = list()
        for extension in self.values():
            ext.extend(extension) 
        ext.sort()
        return ext

    def LoadDefault(self):
        """Loads the default settings
        @postcondition: sets dictionary back to default installation state

        """
        self.clear()
        for key in synglob.EXT_MAP:
            self.__setitem__(synglob.EXT_MAP[key], key.split())

    def LoadFromConfig(self, config):
        """Load the extention register with values from a config file
        @param config: path to config file to load settings from

        """
        path = os.path.join(config, self.config)
        if not os.path.exists(path):
            self.LoadDefault()
        else:
            file_h = file(path, "rb")
            lines = file_h.readlines()
            file_h.close()
            for line in lines:
                tmp = line.split(u'=')
                if len(tmp) != 2:
                    continue
                ftype = tmp[0].strip()
                exts = tmp[1].split(u':')
                self.__setitem__(ftype, exts)

    def SetAssociation(self, ftype, ext):
        """Like Associate but overrides any current settings instead of
        just adding to them.
        @param ftype: File type description string
        @param ext: file extension to set

        """
        self.__setitem__(ftype, list(set(ext.split())))

#-----------------------------------------------------------------------------#

def GenLexerMenu():
    """Generates a menu of available syntax configurations
    @return: alphabetically ordered menu of of all lexer settings
    @rtype: wx.Menu

    """
    lex_menu = wx.Menu()
    f_types = dict()
    for key in synglob.LANG_MAP:
        f_types[key] = synglob.LANG_MAP[key][LANG_ID]
    f_order = list(f_types)
    f_order.sort()

    for lang in f_order:
        lex_menu.Append(f_types[lang], lang, 
                         _("Switch Lexer to %s") % lang, wx.ITEM_CHECK)
    return lex_menu

def GenFileFilters():
    """Generates a list of file filters
    @return: list of all file filters based on exentsion associations

    """
    extreg = ExtensionRegister()
    # Convert extension list into a formated string
    f_dict = dict()
    for key, val in extreg.iteritems():
        val.sort()
        f_dict[key] = u";*." + u";*.".join(val)

    # Build the final list of properly formated strings
    filters = list()
    for key in f_dict:
        tmp = u" (%s)|%s|" % (f_dict[key][1:], f_dict[key][1:])
        filters.append(key + tmp)
    filters.sort()
    filters.insert(0, u"All Files (*.*)|*.*|")
    filters[-1] = filters[-1][:-1] # IMPORTANT trim last '|' from item in list
    return filters

def GetFileExtensions():
    """Gets a sorted list of all file extensions the editor is configured
    to handle.
    @return: all registered file extensions

    """
    extreg = ExtensionRegister()
    return extreg.GetAllExtensions()

def GetLexerList():
    """Gets a list of unique file lexer configurations available
    @return: list of all lexer identifiers

    """ 
    f_types = dict()
    for key, val in synglob.LANG_MAP.iteritems():
        f_types[key] = val[LANG_ID]
    f_order = list(f_types)
    f_order.sort()
    return f_order

def SyntaxIds():
    """Gets a list of all Syntax Ids and returns it
    @return: list of all syntax language ids

    """
    s_glob = dir(synglob)
    syn_ids = list()
    for item in s_glob:
        if item.startswith("ID_LANG"):
            syn_ids.append(item)
    
    # Fetch actual values
    ret_ids = list()
    for syn_id in syn_ids:
        ret_ids.append(getattr(synglob, syn_id))

    return ret_ids

def GetExtFromId(ext_id):
    """Takes a language ID and fetches an appropriate file extension string
    @param extId: language id to get extension for
    @return: file extension
    @rtype: string

    """
    extreg = ExtensionRegister()
    ftype = synglob.ID_MAP.get(ext_id, synglob.ID_MAP[synglob.ID_LANG_TXT])
    return extreg[ftype][0]
