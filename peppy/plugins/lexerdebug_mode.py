# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Lexer colorization debugging

Major mode for trying to figure out how Scintilla styles the modes,
and what Scintilla style goes which what text element.
"""

import os,struct
import keyword
from cStringIO import StringIO

import wx

from peppy.menu import *
from peppy.major import *
from peppy.actions.minibuffer import *
from peppy.fundamental import FundamentalMode


_colors = [
'fore:#FFC0CB',
'fore:#DC143C',
'fore:#FF1493',
'fore:#DA70D6',
'fore:#FF00FF',
'fore:#8B008B',
'fore:#9400D3',
'fore:#7B68EE',

'fore:#0000FF',
'fore:#6495ED',
'fore:#1E90FF',
'fore:#00BFFF',
'fore:#5F9EA0',
'fore:#00FFFF',
'fore:#008080',
'fore:#00FA9A',

'fore:#2E8B57',
'fore:#98FB98',
'fore:#32CD32',
'fore:#00ff00',
'fore:#228B22',
'fore:#9ACD32',
'fore:#FFFF00',
'fore:#808000',

'fore:#BDB76B',
'fore:#FFD700',
'fore:#DAA520',
'fore:#FFA500',
'fore:#DEB887',
'fore:#D2691E',
'fore:#A0522D',
'fore:#FA8072',
]

_debug_boa_style_names = {}
_debug_lexer_styles = {}
for i in range(32):
    _debug_boa_style_names[i]="style%d" % i
    _debug_lexer_styles[i]=_colors[i]
_debug_lexer_styles.update({0: '',
                            1: 'fore:%(comment-col)s,italic',
                            wx.stc.STC_STYLE_DEFAULT: 'face:%(mono)s,size:%(size)d',
                            wx.stc.STC_STYLE_LINENUMBER: 'face:%(ln-font)s,size:%(ln-size)d',
                            
                            wx.stc.STC_STYLE_BRACEBAD: '',
                            wx.stc.STC_STYLE_BRACELIGHT: '',
                            wx.stc.STC_STYLE_CONTROLCHAR: '',
                            wx.stc.STC_STYLE_INDENTGUIDE: '',
                            })

class LexerDebugMode(FundamentalMode):
    """Major mode for debugging the Scintilla Lexer.

    This is a specialized mode that allows the lexer to be specified
    dynamically, in order to find out how a file is parsed and what
    colors identify the variously lexed components.  Keywords can also
    be set.
    """
    debuglevel = 1
    
    keyword = 'LexerDebug'
    icon = 'icons/bug.png'
    regex = None

    default_classprefs = (
        StrParam('minor_modes', ''),
        IntParam('tab_size', 8),
        IntParam('stc_lexer', wx.stc.STC_LEX_NULL),
        StrParam('stc_keywords', ''),
        ReadOnlyParam('stc_boa_style_names', _debug_boa_style_names),
        ReadOnlyParam('stc_lexer_styles', _debug_lexer_styles),
        BoolParam('stc_boa_use_current_text', True),
        )

    def createWindowPostHook(self):
        self.currentLexer = wx.stc.STC_LEX_NULL
        self.keywords = ""

    def changeLexer(self, lexer):
        assert self.dprint("changing to new lexer %d" % lexer)
        self.currentLexer = lexer
        self.stc.SetLexer(self.currentLexer)
        self.stc.SetKeyWords(0, self.keywords)
        self.stc.StyleClearAll()
        self.stc.Colourise(0, self.stc.GetTextLength())
        assert self.dprint("new lexer = %d" % self.stc.GetLexer())


# cd /opt/wx/src/wxPython-src-2.8.1.1/contrib/src/stc/scintilla/include
# grep SCLEX SciLexer.h |cut -c9-
_stc_lexer_defines = """\
SCLEX_CONTAINER 0
SCLEX_NULL 1
SCLEX_PYTHON 2
SCLEX_CPP 3
SCLEX_HTML 4
SCLEX_XML 5
SCLEX_PERL 6
SCLEX_SQL 7
SCLEX_VB 8
SCLEX_PROPERTIES 9
SCLEX_ERRORLIST 10
SCLEX_MAKEFILE 11
SCLEX_BATCH 12
SCLEX_XCODE 13
SCLEX_LATEX 14
SCLEX_LUA 15
SCLEX_DIFF 16
SCLEX_CONF 17
SCLEX_PASCAL 18
SCLEX_AVE 19
SCLEX_ADA 20
SCLEX_LISP 21
SCLEX_RUBY 22
SCLEX_EIFFEL 23
SCLEX_EIFFELKW 24
SCLEX_TCL 25
SCLEX_NNCRONTAB 26
SCLEX_BULLANT 27
SCLEX_VBSCRIPT 28
SCLEX_BAAN 31
SCLEX_MATLAB 32
SCLEX_SCRIPTOL 33
SCLEX_ASM 34
SCLEX_CPPNOCASE 35
SCLEX_FORTRAN 36
SCLEX_F77 37
SCLEX_CSS 38
SCLEX_POV 39
SCLEX_LOUT 40
SCLEX_ESCRIPT 41
SCLEX_PS 42
SCLEX_NSIS 43
SCLEX_MMIXAL 44
SCLEX_CLW 45
SCLEX_CLWNOCASE 46
SCLEX_LOT 47
SCLEX_YAML 48
SCLEX_TEX 49
SCLEX_METAPOST 50
SCLEX_POWERBASIC 51
SCLEX_FORTH 52
SCLEX_ERLANG 53
SCLEX_OCTAVE 54
SCLEX_MSSQL 55
SCLEX_VERILOG 56
SCLEX_KIX 57
SCLEX_GUI4CLI 58
SCLEX_SPECMAN 59
SCLEX_AU3 60
SCLEX_APDL 61
SCLEX_BASH 62
SCLEX_ASN1 63
SCLEX_VHDL 64
SCLEX_CAML 65
SCLEX_BLITZBASIC 66
SCLEX_PUREBASIC 67
SCLEX_HASKELL 68
SCLEX_PHPSCRIPT 69
SCLEX_TADS3 70
SCLEX_REBOL 71
SCLEX_SMALLTALK 72
SCLEX_FLAGSHIP 73
SCLEX_CSOUND 74
SCLEX_FREEBASIC 75
SCLEX_INNOSETUP 76
SCLEX_OPAL 77
SCLEX_SPICE 78
SCLEX_AUTOMATIC 1000
SCLEX_ASP 29
SCLEX_PHP 30
"""
_stc_lexer = {}
_stc_lexer_num = {}
_stc_lexer_define_map = {}
for line in _stc_lexer_defines.splitlines():
    define, num = line.split()
    define = define[6:]
    num = int(num)
    #dprint("define=%s num=%d" % (define, num))
    if num<1000:
        _stc_lexer_define_map[define] = num

        # save a default value of the name, in case the pretty value
        # doesn't exist below.
        _stc_lexer_num[num] = define
        
#dprint(_stc_lexer_define_map)
    
# cd /opt/wx/src/wxPython-src-2.8.1.1/contrib/src/stc/scintilla/include
# egrep "^lex" Scintilla.iface|cut -c5-|cut -f1 -d " "
_stc_name_mapping_text = """\
Python=SCLEX_PYTHON
Cpp=SCLEX_CPP
Pascal=SCLEX_PASCAL
BullAnt=SCLEX_BULLANT
TCL=SCLEX_TCL
HTML=SCLEX_HTML
XML=SCLEX_XML
ASP=SCLEX_ASP
PHP=SCLEX_PHP
Perl=SCLEX_PERL
Ruby=SCLEX_RUBY
VB=SCLEX_VB
VBScript=SCLEX_VBSCRIPT
PowerBasic=SCLEX_POWERBASIC
Properties=SCLEX_PROPERTIES
LaTeX=SCLEX_LATEX
Lua=SCLEX_LUA
ErrorList=SCLEX_ERRORLIST
Batch=SCLEX_BATCH
MakeFile=SCLEX_MAKEFILE
Diff=SCLEX_DIFF
Conf=SCLEX_CONF
Avenue=SCLEX_AVE
Ada=SCLEX_ADA
Baan=SCLEX_BAAN
Lisp=SCLEX_LISP
Eiffel=SCLEX_EIFFEL
EiffelKW=SCLEX_EIFFELKW
NNCronTab=SCLEX_NNCRONTAB
Forth=SCLEX_FORTH
MatLab=SCLEX_MATLAB
Sol=SCLEX_SCRIPTOL
Asm=SCLEX_ASM
Fortran=SCLEX_FORTRAN
F77=SCLEX_F77
CSS=SCLEX_CSS
POV=SCLEX_POV
LOUT=SCLEX_LOUT
ESCRIPT=SCLEX_ESCRIPT
PS=SCLEX_PS
NSIS=SCLEX_NSIS
MMIXAL=SCLEX_MMIXAL
Clarion=SCLEX_CLW
LOT=SCLEX_LOT
YAML=SCLEX_YAML
TeX=SCLEX_TEX
Metapost=SCLEX_METAPOST
Erlang=SCLEX_ERLANG
Octave=SCLEX_OCTAVE
MSSQL=SCLEX_MSSQL
Verilog=SCLEX_VERILOG
Kix=SCLEX_KIX
Specman=SCLEX_SPECMAN
Au3=SCLEX_AU3
APDL=SCLEX_APDL
Bash=SCLEX_BASH
Asn1=SCLEX_ASN1
VHDL=SCLEX_VHDL
Caml=SCLEX_CAML
Haskell=SCLEX_HASKELL
TADS3=SCLEX_TADS3
Rebol=SCLEX_REBOL
SQL=SCLEX_SQL
Smalltalk=SCLEX_SMALLTALK
FlagShip=SCLEX_FLAGSHIP
Csound=SCLEX_CSOUND
Inno=SCLEX_INNOSETUP
Opal=SCLEX_OPAL
Spice=SCLEX_SPICE
"""
for line in _stc_name_mapping_text.splitlines():
    name, define = line.split('=')
    define = define[6:] # strip off "SCLEX_"
    #dprint("name=%s define=%s" % (name, define))
    if define in _stc_lexer_define_map:
        num = _stc_lexer_define_map[define]
        _stc_lexer_num[num] = name
for num, name in _stc_lexer_num.iteritems():
    _stc_lexer[name] = num
_stc_lexer_names = _stc_lexer.keys()
_stc_lexer_names.sort()
#dprint(_stc_lexer_names)


class LexerSelect(RadioAction):
    debuglevel = 1
    
    name="Lexer Select"
    inline=False
    tooltip="Change lexer"

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)

    def getIndex(self):
        mode = self.frame.getActiveMajorMode()
        if mode is not None:
            assert self.dprint("index=%s, name=%s" % (mode.currentLexer, _stc_lexer_num[mode.currentLexer]))
            return _stc_lexer_names.index(_stc_lexer_num[mode.currentLexer])
        return 0
                                           
    def getItems(self):
        return _stc_lexer_names
    
    def action(self, index=0):
        assert self.dprint("changing to index=%d" % index)
        self.mode.changeLexer(_stc_lexer[_stc_lexer_names[index]])

class LexerKeywords(MinibufferAction):
    """Get a string specifying the lexer keywords.
    
    Use minibuffer to request a string of keywords to be used as the
    lexer's keywords.  Currently only corresponds to the keywordset ==
    0.
    """

    name = "Keywords..."
    tooltip = "Specify the keywords for the lexer"
    minibuffer = TextMinibuffer
    minibuffer_label = "Keywords:"

    def processMinibuffer(self, mode, text):
        """
        Callback function used to set the keywords
        """
        
        # stc counts lines from zero, but displayed starting at 1.
        dprint("keywords = %s" % text)
        mode.keywords = text


class LexerDebugPlugin(IPeppyPlugin):
    """Plugin to register LexerDebug mode and user interface.
    """

    def possibleModes(self):
        yield LexerDebugMode
    
    default_menu=(("LexerDebug",None,Menu(_("Lexer")).after(_("Minor Mode"))),
                  ("LexerDebug",_("Lexer"),MenuItem(LexerKeywords)),
                  ("LexerDebug",_("Lexer"),MenuItem(LexerSelect)),
                  )
    def getMenuItems(self):
        for mode,parentmenu,item in self.default_menu:
            yield (mode,parentmenu,item)

