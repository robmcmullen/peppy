###############################################################################
# Name: synglob.py                                                            #
# Purpose: Acts as a registration point for all supported languages.          #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: synglob.py                                                            #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# Provides configuration and basic API functionality to all the syntax        #
# modules. It also acts more or less as a configuration file for the syntax   #
# managment code.                                                             #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: synglob.py 51489 2008-02-01 10:17:24Z CJP $"
__revision__ = "$Revision: 51489 $"

#-----------------------------------------------------------------------------#
# Dependencies
import wx
import wx.stc as stc

# The language identifiers and the EXT_MAP have been moved out of this
# module in order to be independent of Editra and wx, but they are
# still needed here...
from synextreg import *

#-----------------------------------------------------------------------------#

# Maps file types to syntax definitions
LANG_MAP = {LANG_68K    : (ID_LANG_68K,    stc.STC_LEX_ASM,      'asm68k'),
            LANG_ADA    : (ID_LANG_ADA,    stc.STC_LEX_ADA,      'ada'),
            LANG_APACHE : (ID_LANG_APACHE, stc.STC_LEX_CONF,     'apache'),
            LANG_BASH   : (ID_LANG_BASH,   stc.STC_LEX_BASH,     'sh'),
            LANG_BATCH  : (ID_LANG_BATCH,  stc.STC_LEX_BATCH,    'batch'),
            LANG_BOO    : (ID_LANG_BOO,    stc.STC_LEX_PYTHON,   'boo'),
            LANG_C      : (ID_LANG_C,      stc.STC_LEX_CPP,      'cpp'),
            LANG_CAML   : (ID_LANG_CAML,   stc.STC_LEX_CAML,     'caml'),
            LANG_COLDFUSION : (ID_LANG_COLDFUSION, stc.STC_LEX_HTML, 'html'),
            LANG_CPP    : (ID_LANG_CPP,    stc.STC_LEX_CPP,      'cpp'),
            LANG_CSH    : (ID_LANG_CSH,    stc.STC_LEX_BASH,     'sh'),
            LANG_CSS    : (ID_LANG_CSS,    stc.STC_LEX_CSS,      'css'),
            LANG_D      : (ID_LANG_D,      stc.STC_LEX_CPP,      'd'),
            LANG_DIFF   : (ID_LANG_DIFF,   stc.STC_LEX_DIFF,     'diff'),
            LANG_DOT    : (ID_LANG_DOT,    stc.STC_LEX_CPP,      'dot'),
            LANG_EDJE   : (ID_LANG_EDJE,   stc.STC_LEX_CPP,      'edje'),
            LANG_EIFFEL : (ID_LANG_EIFFEL, stc.STC_LEX_EIFFEL,   'eiffel'),
            LANG_ERLANG : (ID_LANG_ERLANG, stc.STC_LEX_ERLANG,   'erlang'),
            LANG_ESS    : (ID_LANG_ESS,    stc.STC_LEX_CSS,      'editra_ss'),
            LANG_F77    : (ID_LANG_F77,    stc.STC_LEX_F77,      'fortran'),
            LANG_F95    : (ID_LANG_F95,    stc.STC_LEX_FORTRAN,  'fortran'),
            LANG_FERITE : (ID_LANG_FERITE, stc.STC_LEX_CPP,      'ferite'),
            LANG_FLAGSHIP: (ID_LANG_FLAGSHIP, stc.STC_LEX_FLAGSHIP, 'flagship'),
            LANG_GUI4CLI : (ID_LANG_GUI4CLI, stc.STC_LEX_GUI4CLI, 'gui4cli'),
            LANG_HASKELL : (ID_LANG_HASKELL, stc.STC_LEX_HASKELL, 'haskell'),
            LANG_HAXE   : (ID_LANG_HAXE, stc.STC_LEX_CPP,        'haxe'),
            LANG_HTML   : (ID_LANG_HTML,   stc.STC_LEX_HTML,     'html'),
            LANG_INNO   : (ID_LANG_INNO,   stc.STC_LEX_INNOSETUP, 'inno'),
            LANG_JAVA   : (ID_LANG_JAVA,   stc.STC_LEX_CPP,      'java'),
            LANG_JS     : (ID_LANG_JS,     stc.STC_LEX_CPP,      'javascript'),
            LANG_KIX    : (ID_LANG_KIX,    stc.STC_LEX_KIX,      'kix'),
            LANG_KSH    : (ID_LANG_KSH,    stc.STC_LEX_BASH,     'sh'),
            LANG_LATEX  : (ID_LANG_LATEX,  stc.STC_LEX_LATEX,    'latex'),
            LANG_LISP   : (ID_LANG_LISP,   stc.STC_LEX_LISP,     'lisp'),
            LANG_LOUT   : (ID_LANG_LOUT,   stc.STC_LEX_LOUT,     'lout'),
            LANG_LUA    : (ID_LANG_LUA,    stc.STC_LEX_LUA,      'lua'),
            LANG_MAKE   : (ID_LANG_MAKE,   stc.STC_LEX_MAKEFILE, 'make'),
            LANG_MASM   : (ID_LANG_MASM,   stc.STC_LEX_ASM,      'masm'),
            LANG_MATLAB : (ID_LANG_MATLAB, stc.STC_LEX_MATLAB,   'matlab'),
            LANG_MSSQL  : (ID_LANG_MSSQL,  stc.STC_LEX_MSSQL,    'mssql'),
            LANG_NASM   : (ID_LANG_NASM,   stc.STC_LEX_ASM,      'nasm'),
            LANG_NSIS   : (ID_LANG_NSIS,   stc.STC_LEX_NSIS,     'nsis'),
            LANG_OCTAVE : (ID_LANG_OCTAVE, stc.STC_LEX_OCTAVE,   'matlab'),
            LANG_PASCAL : (ID_LANG_PASCAL, stc.STC_LEX_PASCAL,   'pascal'),
            LANG_PERL   : (ID_LANG_PERL,   stc.STC_LEX_PERL,     'perl'),
            LANG_PHP    : (ID_LANG_PHP,    stc.STC_LEX_HTML,     'php'),
            LANG_PIKE   : (ID_LANG_PIKE,   stc.STC_LEX_CPP,      'pike'),
            LANG_PLSQL  : (ID_LANG_PLSQL,  stc.STC_LEX_SQL,      'sql'),
            LANG_PROPS  : (ID_LANG_PROPS,  stc.STC_LEX_PROPERTIES, 'props'),
            LANG_PS     : (ID_LANG_PS,     stc.STC_LEX_PS,       'postscript'),
            LANG_PYTHON : (ID_LANG_PYTHON, stc.STC_LEX_PYTHON,   'python'),
            LANG_RUBY   : (ID_LANG_RUBY,   stc.STC_LEX_RUBY,     'ruby'),
            LANG_SQL    : (ID_LANG_SQL,    stc.STC_LEX_SQL,      'sql'),
            LANG_ST     : (ID_LANG_ST,     stc.STC_LEX_SMALLTALK, 'smalltalk'),
            LANG_TCL    : (ID_LANG_TCL,    stc.STC_LEX_TCL,      'tcl'),
            LANG_TXT    : (ID_LANG_TXT,    stc.STC_LEX_NULL,     None),
            LANG_VB     : (ID_LANG_VB,     stc.STC_LEX_VB,       'visualbasic'),
            LANG_VERILOG: (ID_LANG_VERILOG, stc.STC_LEX_VERILOG, 'verilog'),
            LANG_VHDL   : (ID_LANG_VHDL,   stc.STC_LEX_VHDL,     'vhdl'),
            LANG_XML    : (ID_LANG_XML,    stc.STC_LEX_XML,      'xml'),
            LANG_YAML   : (ID_LANG_YAML,   stc.STC_LEX_YAML,     'yaml')
            }

# Maps language ID's to File Types
# Used when manually setting lexer from a menu/dialog
# TODO maybe dynamically generate this on the fly to remove the need
#      to update it for each new language.
ID_MAP = {ID_LANG_68K    : LANG_68K,    ID_LANG_ADA   : LANG_ADA,
          ID_LANG_APACHE : LANG_APACHE, ID_LANG_ASM   : LANG_ASM,
          ID_LANG_BASH   : LANG_BASH,   ID_LANG_BATCH : LANG_BATCH,
          ID_LANG_BOO    : LANG_BOO,    ID_LANG_C     : LANG_C,
          ID_LANG_CAML  : LANG_CAML,    ID_LANG_COLDFUSION : LANG_COLDFUSION,
          ID_LANG_CPP    : LANG_CPP,    ID_LANG_CSH   : LANG_CSH, 
          ID_LANG_CSS    : LANG_CSS,    ID_LANG_D     : LANG_D,
          ID_LANG_DIFF   : LANG_DIFF,   ID_LANG_DOT    : LANG_DOT,
          ID_LANG_EDJE   : LANG_EDJE,   ID_LANG_EIFFEL : LANG_EIFFEL,
          ID_LANG_ERLANG : LANG_ERLANG, ID_LANG_ESS    : LANG_ESS,
          ID_LANG_F77    : LANG_F77,    ID_LANG_F95   : LANG_F95,
          ID_LANG_FERITE : LANG_FERITE, ID_LANG_FLAGSHIP : LANG_FLAGSHIP,
          ID_LANG_GUI4CLI : LANG_GUI4CLI, ID_LANG_HASKELL : LANG_HASKELL,
          ID_LANG_HAXE   : LANG_HAXE,    ID_LANG_HTML  : LANG_HTML,
          ID_LANG_INNO   : LANG_INNO,   ID_LANG_JAVA  : LANG_JAVA,
          ID_LANG_JS     : LANG_JS,     ID_LANG_KIX   : LANG_KIX,
          ID_LANG_KSH    : LANG_KSH,    ID_LANG_LATEX : LANG_LATEX,
          ID_LANG_LISP   : LANG_LISP,   ID_LANG_LOUT  : LANG_LOUT,
          ID_LANG_LUA    : LANG_LUA,    ID_LANG_MAKE  : LANG_MAKE,
          ID_LANG_MASM   : LANG_MASM,   ID_LANG_MATLAB : LANG_MATLAB,
          ID_LANG_MSSQL  : LANG_MSSQL,  ID_LANG_NASM  : LANG_MASM,
          ID_LANG_NSIS   : LANG_NSIS,   ID_LANG_OCTAVE : LANG_OCTAVE,
          ID_LANG_PASCAL : LANG_PASCAL, ID_LANG_PERL   : LANG_PERL,
          ID_LANG_PHP    : LANG_PHP,    ID_LANG_PIKE   : LANG_PIKE,
          ID_LANG_PROPS  : LANG_PROPS,  ID_LANG_PS     : LANG_PS,
          ID_LANG_PLSQL  : LANG_PLSQL,  ID_LANG_PYTHON : LANG_PYTHON,
          ID_LANG_RUBY   : LANG_RUBY,   ID_LANG_SQL    : LANG_SQL,
          ID_LANG_ST     : LANG_ST,     ID_LANG_VB     : LANG_VB,
          ID_LANG_VERILOG : LANG_VERILOG, ID_LANG_VHDL : LANG_VHDL,
          ID_LANG_TCL    : LANG_TCL,    ID_LANG_TXT    : LANG_TXT,
          ID_LANG_XML    : LANG_XML,    ID_LANG_YAML   : LANG_YAML
}
