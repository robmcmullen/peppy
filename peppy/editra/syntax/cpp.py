###############################################################################
# Name: cpp.py                                                                #
# Purpose: Define C/CPP syntax for highlighting and other features            #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: cpp.py                                                                #
# @author: Cody Precord                                                       #
#                                                                             #
# SUMMARY:                                                                    #
# Lexter configuration file for C/C++ source files.                           #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: cpp.py 609 2007-10-08 06:54:00Z CodyPrecord $"
__revision__ = "$Revision: 609 $"

#-----------------------------------------------------------------------------#
# Dependencies
import synglob

#-----------------------------------------------------------------------------#

#---- Keyword Specifications ----#

# C Keywords
C_KEYWORDS = ("goto break return continue asm case default if else switch "
              "while for do sizeof typeof ")

# C Types/Structures/Storage Classes
C_TYPES = ("int long short char void signed unsigned float double "
           "size_t ssize_t wchar_t ptrdiff_t sig_atomic_t fpos_t "
           "clock_t time_t va_list jmp_buf FILE DIR div_t ldiv_t "
           "mbstate_t wctrans_t wint_t wctype_t bool complex int8_t "
           "int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t "
           "int_least8_t int_least16_t int_least32_t int_least64_t "
           "uint_fast8_t uint_fast16_t uint_fast32_t uint_fast64_t "
           "intptr_t uintptr_t intmax_t uintmax_t __label__ __complex__ "
           "__volatile__ struct union enum typedef static register auto "
           "volatile extern const inline __attribute__ ")

# C/CPP Documentation Keywords (includes Doxygen keywords)
DOC_KEYWORDS = (2, "TODO FIXME XXX \\author \\brief \\bug \\callgraph "
                   "\\category \\class \\code \\date \\def \\depreciated \\dir "
                   "\\dot \\dotfile \\else \\elseif \\em \\endcode \\enddot "
                   "\\endif \\endverbatim \\example \\exception \\file \\if "
                   "\\ifnot \\image \\include \\link \\mainpage \\name "
                   "\\namespace \\page \\par \\paragraph \\param \\return "
                   "\\retval \\section \\struct \\subpage \\subsection " 
                   "\\subsubsection \\test \\todo \\typedef \\union \\var "
                   "\\verbatim \\version \\warning \\$ \\@ \\~ \\< \\> \\# \\% "
                   "HACK ")

# CPP Keyword Extensions
CPP_KEYWORDS = ("new delete this friend using throw try catch opperator "
                "typeid and bitor or xor compl bitand and_eq or_eq xor_eq "
                "not not_eq const_cast static_cast dynamic_cast "
                "reinterpret_cast true false ")

# CPP Type/Structure/Storage Class Extensions
CPP_TYPES = ("public protected private inline virtual explicit export bool "
             "wchar_t mutable class typename template namespace ")

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [ ('STC_C_DEFAULT', 'default_style'),
                 ('STC_C_COMMENT', 'comment_style'),
                 ('STC_C_COMMENTLINE', 'comment_style'),
                 ('STC_C_COMMENTDOC', 'comment_style'),
                 ('STC_C_COMMENTDOCKEYWORD', 'dockey_style'),
                 ('STC_C_COMMENTDOCKEYWORDERROR', 'error_style'),
                 ('STC_C_COMMENTLINE', 'comment_style'),
                 ('STC_C_COMMENTLINEDOC', 'comment_style'),
                 ('STC_C_CHARACTER', 'char_style'),
                 ('STC_C_GLOBALCLASS', 'global_style'),
                 ('STC_C_IDENTIFIER', 'default_style'),
                 ('STC_C_NUMBER', 'number_style'),
                 ('STC_C_OPERATOR', 'operator_style'),
                 ('STC_C_PREPROCESSOR', 'pre_style'),
                 ('STC_C_REGEX', 'pre_style'),
                 ('STC_C_STRING', 'string_style'),
                 ('STC_C_STRINGEOL', 'stringeol_style'),
                 ('STC_C_UUID', 'pre_style'),
                 ('STC_C_VERBATIM', "number2_style"),
                 ('STC_C_WORD', 'keyword_style'),
                 ('STC_C_WORD2', 'keyword2_style') ]

#---- Extra Properties ----#
FOLD = ("fold", "1")
FOLD_PRE = ("styling.within.preprocessor", "0")
FOLD_COM = ("fold.comment", "1")
FOLD_COMP = ("fold.compact", "1")
FOLD_ELSE = ("fold.at.else", "0")
#------------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @param lang_id: used to select specific subset of keywords

    """
    keywords = list()
    kw1_str = [C_KEYWORDS]
    kw2_str = [C_TYPES]
    if lang_id == synglob.ID_LANG_CPP:
        kw1_str.append(CPP_KEYWORDS)
        kw2_str.append(CPP_TYPES)
    keywords.append((0, " ".join(kw1_str)))
    keywords.append((1, " ".join(kw2_str)))
    keywords.append(DOC_KEYWORDS)
    return keywords

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @param lang_id: used for selecting a specific subset of syntax specs

    """
    return SYNTAX_ITEMS

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @param lang_id: used to select a specific set of properties

    """
    return [FOLD, FOLD_PRE]

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @param lang_id: used to select a specific subset of comment pattern(s)

    """
    if lang_id == synglob.ID_LANG_CPP:
        return [u'//']
    else:
        return [u'/*', u'*/']

#---- End Required Functions ----#

#---- Syntax Modules Internal Functions ----#
def KeywordString():
    """Returns the specified Keyword String
    @note: not used by most modules

    """
    return None

#---- End Syntax Modules Internal Functions ----#
