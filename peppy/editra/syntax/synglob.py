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
# Profides configuration and basic API functionality to all the syntax        #
# modules. It also acts more or less as a configuration file for the syntax   #
# managment code.                                                             #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: synglob.py 609 2007-10-08 06:54:00Z CodyPrecord $"
__revision__ = "$Revision: 609 $"

#-----------------------------------------------------------------------------#
# Dependencies
import wx
import wx.stc as stc

#-----------------------------------------------------------------------------#

#---- Language Identifiers Keys ----#
# Used for specifying what dialect/keyword set to load for a specific lexer

#---- Use LEX_NULL ----#
ID_LANG_TXT  = wx.NewId()
LANG_TXT = u'Plain Text'

#---- Use LEX_ADA ----#
ID_LANG_ADA = wx.NewId()
LANG_ADA = u'Ada'

#---- Use LEX_ASM ----#
ID_LANG_ASM  = wx.NewId()
LANG_ASM = u'Assembly Code'
ID_LANG_68K  = wx.NewId()
LANG_68K = u'68k Assembly'
ID_LANG_MASM = wx.NewId()
LANG_MASM = u'MASM'
ID_LANG_NASM = wx.NewId()
LANG_NASM = u'Netwide Assembler'

# Use LEX_BASH
ID_LANG_BOURNE = wx.NewId()
LANG_BOURNE = u'Bourne Shell Script'
ID_LANG_BASH   = wx.NewId()
LANG_BASH = u'Bash Shell Script'
ID_LANG_CSH    = wx.NewId()
LANG_CSH = u'C-Shell Script'
ID_LANG_KSH    = wx.NewId()
LANG_KSH = u'Korn Shell Script'

# Use LEX_CAML
ID_LANG_CAML = wx.NewId()
LANG_CAML = u'Caml'

# Use LEX_CONF
ID_LANG_APACHE = wx.NewId()
LANG_APACHE = u'Apache Conf'

# Use LEX_CPP
ID_LANG_C    = wx.NewId()
LANG_C = u'C'
ID_LANG_CPP  = wx.NewId()
LANG_CPP = u'CPP'
ID_LANG_D = wx.NewId()
LANG_D = u'D'
ID_LANG_JAVA = wx.NewId()
LANG_JAVA = u'Java'

# Use LEX_CSS
ID_LANG_CSS = wx.NewId()
LANG_CSS = u'Cascading Style Sheet'
ID_LANG_ESS = wx.NewId()
LANG_ESS = u'Editra Style Sheet'

# Use LEX_EIFFEL
ID_LANG_EIFFEL = wx.NewId()
LANG_EIFFEL = u"Eiffel"

# Use LEX_ERLANG
ID_LANG_ERLANG = wx.NewId()
LANG_ERLANG = u'Erlang'

# Use LEX_FLAGSHIP
ID_LANG_FLAGSHIP = wx.NewId()
LANG_FLAGSHIP = u'FlagShip'

# Use LEX_F77
ID_LANG_F77 = wx.NewId()
LANG_F77 = u'Fortran 77'

# Use LEX_FORTRAN
ID_LANG_F95 = wx.NewId()
LANG_F95 = u'Fortran 95'

# Use LEX_HASKELL
ID_LANG_HASKELL = wx.NewId()
LANG_HASKELL = u'Haskell'

# Use LEX_HTML
ID_LANG_COLDFUSION = wx.NewId()
LANG_COLDFUSION = u'ColdFusion'
ID_LANG_HTML = wx.NewId()
LANG_HTML = u'HTML'
ID_LANG_JS   = wx.NewId()
LANG_JS = u'JavaScript'
ID_LANG_VBS  = wx.NewId()
LANG_VBS = u'VB Script'
ID_LANG_PHP  = wx.NewId()
LANG_PHP = u'PHP'
ID_LANG_XML  = wx.NewId()
LANG_XML = u'XML'
ID_LANG_SGML = wx.NewId()

# Use LEX_LISP
ID_LANG_LISP = wx.NewId()
LANG_LISP = u'Lisp'

# Use LEX_LOUT
ID_LANG_LOUT = wx.NewId()
LANG_LOUT = u'Lout'

# Use LEX_LUA
ID_LANG_LUA = wx.NewId()
LANG_LUA = u'Lua'

# Use LEX_MSSQL (Microsoft SQL)
ID_LANG_MSSQL = wx.NewId()
LANG_MSSQL = u'Microsoft SQL'

# Use LEX_NSIS
ID_LANG_NSIS = wx.NewId()
LANG_NSIS = u'Nullsoft Installer Script'

# Use LEX_PASCAL
ID_LANG_PASCAL = wx.NewId()
LANG_PASCAL = u'Pascal'

# Use LEX_PERL
ID_LANG_PERL = wx.NewId()
LANG_PERL = u'Perl'

# Use LEX_PS
ID_LANG_PS = wx.NewId()
LANG_PS = u'Postscript'

# Use LEX_PYTHON 
ID_LANG_PYTHON = wx.NewId()
LANG_PYTHON = u'Python'

# Use LEX_MATLAB
ID_LANG_MATLAB = wx.NewId()
LANG_MATLAB = u"Matlab"

# Use LEX_RUBY
ID_LANG_RUBY = wx.NewId()
LANG_RUBY = u'Ruby'

# Use LEX_SMALLTALK
ID_LANG_ST = wx.NewId()
LANG_ST = u'Smalltalk'

# Use LEX_SQL (PL/SQL, SQL*Plus)
ID_LANG_SQL = wx.NewId()
LANG_SQL = u'SQL'

# Use LEX_TCL
ID_LANG_TCL  = wx.NewId()
LANG_TCL = u'Tcl/Tk'

# Use LEX_TEX
ID_LANG_TEX = wx.NewId()
LANG_TEX = u'Tex'
ID_LANG_LATEX = wx.NewId()
LANG_LATEX = u'LaTeX'

# Use LEX_VB
ID_LANG_VB = wx.NewId()
LANG_VB = u'Visual Basic'

# Use LEX_VHDL
ID_LANG_VHDL = wx.NewId()
LANG_VHDL = u'VHDL'

# Use LEX_OCTAVE
ID_LANG_OCTAVE = wx.NewId()
LANG_OCTAVE = u'Octave'

# Use LEX_OTHER (Batch, Diff, Makefile)
ID_LANG_BATCH = wx.NewId()
LANG_BATCH = u'DOS Batch Script'
ID_LANG_DIFF = wx.NewId()
LANG_DIFF = u'Diff File'
ID_LANG_MAKE  = wx.NewId()
LANG_MAKE = u'Makefile'
ID_LANG_PROPS = wx.NewId()
LANG_PROPS = u'Properties'

# Use LEX_YAML
ID_LANG_YAML = wx.NewId()
LANG_YAML = u'YAML'

#---- End Language Identifier Keys ----#

# Default extensions to file type map
EXT_MAP = {
           '68k'                : LANG_68K,
           'ada adb ads a'      : LANG_ADA,
           'conf htaccess'      : LANG_APACHE,
           'bsh sh configure'   : LANG_BASH,
           'bat cmd'            : LANG_BATCH,
           'c h'                : LANG_C,
           'ml mli'             : LANG_CAML,
           'cfm cfc cfml dbm'   : LANG_COLDFUSION,
           'cc c++ cpp cxx hh h++ hpp hxx' : LANG_CPP,
           'csh'                : LANG_CSH,
           'css'                : LANG_CSS,
           'd'                  : LANG_D,
           'patch diff'         : LANG_DIFF,
           'e'                  : LANG_EIFFEL,
           'erl'                : LANG_ERLANG,
           'ess'                : LANG_ESS,
           'prg'                : LANG_FLAGSHIP,
           'f for'              : LANG_F77,
           'f90 f95 f2k fpp'    : LANG_F95,
           'hs'                 : LANG_HASKELL,
           'htm html shtm shtml xhtml' : LANG_HTML,
           'java'               : LANG_JAVA,
           'js'                 : LANG_JS,
           'ksh'                : LANG_KSH,
           'aux tex sty'        : LANG_LATEX,
           'cl lisp lsp'        : LANG_LISP,
           'lt'                 : LANG_LOUT,
           'lua'                : LANG_LUA,
           'mak makefile'       : LANG_MAKE,
           'asm masm'           : LANG_MASM,
           'm matlab'           : LANG_MATLAB,
           'mssql'              : LANG_MSSQL,
           'nasm'               : LANG_NASM,
           'nsi'                : LANG_NSIS,
           'oct octave'         : LANG_OCTAVE,
           'dfm dpk dpr inc p pas pp' : LANG_PASCAL,
           'cgi pl pm pod'      : LANG_PERL,
           'php php3 phtml phtm' : LANG_PHP,
           'ini inf reg url cfg cnf' : LANG_PROPS,
           'ai ps'              : LANG_PS,
           'py pyw python'      : LANG_PYTHON,
           'rb rbw rbx'         : LANG_RUBY,
           'sql'                : LANG_SQL,
           'st'                 : LANG_ST,
           'itcl tcl tk'        : LANG_TCL,
           'txt'                : LANG_TXT,
           'bas cls ctl frm vb' : LANG_VB,
           'vh vhdl'            : LANG_VHDL,
           'axl dtd plist rdf svg xml xrc xsd xsl xslt xul' : LANG_XML,
           'yaml yml'           : LANG_YAML,
          }

# Maps file types to syntax definitions
LANG_MAP = {LANG_68K    : (ID_LANG_68K,    stc.STC_LEX_ASM,      'asm68k'),
            LANG_ADA    : (ID_LANG_ADA,    stc.STC_LEX_ADA,      'ada'),
            LANG_APACHE : (ID_LANG_APACHE, stc.STC_LEX_CONF,     'apache'),
            LANG_BASH   : (ID_LANG_BASH,   stc.STC_LEX_BASH,     'sh'),
            LANG_BATCH  : (ID_LANG_BATCH,  stc.STC_LEX_BATCH,    'batch'),
            LANG_C      : (ID_LANG_C,      stc.STC_LEX_CPP,      'cpp'),
            LANG_CAML   : (ID_LANG_CAML,   stc.STC_LEX_CAML,     'caml'),
            LANG_COLDFUSION : (ID_LANG_COLDFUSION, stc.STC_LEX_HTML, 'html'),
            LANG_CPP    : (ID_LANG_CPP,    stc.STC_LEX_CPP,      'cpp'),
            LANG_CSH    : (ID_LANG_CSH,    stc.STC_LEX_BASH,     'sh'),
            LANG_CSS    : (ID_LANG_CSS,    stc.STC_LEX_CSS,      'css'),
            LANG_D      : (ID_LANG_D,      stc.STC_LEX_CPP,      'd'),
            LANG_DIFF   : (ID_LANG_DIFF,   stc.STC_LEX_DIFF,     'diff'),
            LANG_EIFFEL : (ID_LANG_EIFFEL, stc.STC_LEX_EIFFEL,   'eiffel'),
            LANG_ERLANG : (ID_LANG_ERLANG, stc.STC_LEX_ERLANG,   'erlang'),
            LANG_ESS    : (ID_LANG_ESS,    stc.STC_LEX_CSS,      'editra_ss'),
            LANG_F77    : (ID_LANG_F77,    stc.STC_LEX_F77,      'fortran'),
            LANG_F95    : (ID_LANG_F95,    stc.STC_LEX_FORTRAN,  'fortran'),
            LANG_FLAGSHIP: (ID_LANG_FLAGSHIP, stc.STC_LEX_FLAGSHIP, 'flagship'),
            LANG_HASKELL : (ID_LANG_HASKELL, stc.STC_LEX_HASKELL, 'haskell'),
            LANG_HTML   : (ID_LANG_HTML,   stc.STC_LEX_HTML,     'html'),
            LANG_JAVA   : (ID_LANG_JAVA,   stc.STC_LEX_CPP,      'java'),
            LANG_JS     : (ID_LANG_JS,     stc.STC_LEX_CPP,      'javascript'), 
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
            LANG_PROPS  : (ID_LANG_PROPS,  stc.STC_LEX_PROPERTIES, 'props'),
            LANG_PS     : (ID_LANG_PS,     stc.STC_LEX_PS,       'postscript'),
            LANG_PYTHON : (ID_LANG_PYTHON, stc.STC_LEX_PYTHON,   'python'),
            LANG_RUBY   : (ID_LANG_RUBY,   stc.STC_LEX_RUBY,     'ruby'),
            LANG_SQL    : (ID_LANG_SQL,    stc.STC_LEX_SQL,      'sql'),
            LANG_ST     : (ID_LANG_ST,     stc.STC_LEX_SMALLTALK, 'smalltalk'),
            LANG_TCL    : (ID_LANG_TCL,    stc.STC_LEX_TCL,      'tcl'),
            LANG_TXT    : (ID_LANG_TXT,    stc.STC_LEX_NULL,     None),
            LANG_VB     : (ID_LANG_VB,     stc.STC_LEX_VB,       'visualbasic'),
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
          ID_LANG_BASH  : LANG_BASH,    ID_LANG_BATCH : LANG_BATCH,  
          ID_LANG_C      : LANG_C,      ID_LANG_CAML  : LANG_CAML,
          ID_LANG_COLDFUSION : LANG_COLDFUSION,
          ID_LANG_CPP    : LANG_CPP,    ID_LANG_CSH   : LANG_CSH, 
          ID_LANG_CSS    : LANG_CSS,    ID_LANG_D     : LANG_D,
          ID_LANG_DIFF   : LANG_DIFF,   ID_LANG_EIFFEL : LANG_EIFFEL, 
          ID_LANG_ERLANG : LANG_ERLANG, ID_LANG_ESS    : LANG_ESS,
          ID_LANG_F77    : LANG_F77,    ID_LANG_F95   : LANG_F95,
          ID_LANG_FLAGSHIP : LANG_FLAGSHIP, ID_LANG_HASKELL : LANG_HASKELL,
          ID_LANG_HTML   : LANG_HTML,   ID_LANG_JAVA  : LANG_JAVA, 
          ID_LANG_JS     : LANG_JS,     ID_LANG_KSH   : LANG_KSH,
          ID_LANG_LATEX  : LANG_LATEX,  ID_LANG_LISP  : LANG_LISP, 
          ID_LANG_LOUT   : LANG_LOUT,   ID_LANG_LUA   : LANG_LUA,
          ID_LANG_MAKE   : LANG_MAKE,   ID_LANG_MASM  : LANG_MASM,
          ID_LANG_MATLAB : LANG_MATLAB, ID_LANG_MSSQL  : LANG_MSSQL,  
          ID_LANG_NASM  : LANG_MASM,    ID_LANG_NSIS   : LANG_NSIS,   
          ID_LANG_OCTAVE : LANG_OCTAVE, ID_LANG_PASCAL : LANG_PASCAL, 
          ID_LANG_PERL   : LANG_PERL,   ID_LANG_PHP    : LANG_PHP,
          ID_LANG_PROPS  : LANG_PROPS,
          ID_LANG_PS     : LANG_PS,     ID_LANG_PYTHON : LANG_PYTHON,
          ID_LANG_RUBY   : LANG_RUBY,   ID_LANG_SQL    : LANG_SQL,
          ID_LANG_ST     : LANG_ST,     ID_LANG_VB     : LANG_VB,
          ID_LANG_VHDL   : LANG_VHDL,   ID_LANG_TCL    : LANG_TCL,
          ID_LANG_TXT    : LANG_TXT,    ID_LANG_XML    : LANG_XML,
          ID_LANG_YAML   : LANG_YAML
}
