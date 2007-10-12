###############################################################################
# Name: python.py                                                             #
# Purpose: Define Python syntax for highlighting and other features           #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: python.py                                                             #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# @summary: Lexer configuration module for Python.                            #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: python.py 609 2007-10-08 06:54:00Z CodyPrecord $"
__revision__ = "$Revision: 609 $"

#-----------------------------------------------------------------------------#
# Dependancies
import keyword

#-----------------------------------------------------------------------------#

#---- Keyword Specifications ----#

# Python Keywords
KEYWORDS = keyword.kwlist
KEYWORDS.extend(['True', 'False', 'None', 'self'])
PY_KW = (0, " ".join(KEYWORDS))

# Highlighted Identifiers
PY_ID = (1, "")

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [ ('STC_P_DEFAULT', 'default_style'),
                 ('STC_P_CHARACTER', 'char_style'),
                 ('STC_P_CLASSNAME', 'class_style'),
                 ('STC_P_COMMENTBLOCK', 'comment_style'),
                 ('STC_P_COMMENTLINE', 'comment_style'),
                 ('STC_P_DECORATOR', 'default_style'),
                 ('STC_P_DEFNAME', 'keyword3_style'),
                 ('STC_P_IDENTIFIER', 'default_style'),
                 ('STC_P_NUMBER', 'number_style'),
                 ('STC_P_OPERATOR', 'operator_style'),
                 ('STC_P_STRING', 'string_style'),
                 ('STC_P_STRINGEOL', 'stringeol_style'),
                 ('STC_P_TRIPLE', 'string_style'),
                 ('STC_P_TRIPLEDOUBLE', 'string_style'),
                 ('STC_P_WORD', 'keyword_style'),
                 ('STC_P_WORD2', 'default_style')]

#---- Extra Properties ----#
FOLD = ("fold", "1")
TIMMY = ("tab.timmy.whinge.level", "1") # Mark Inconsistant indentation

#-----------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @param lang_id: used to select specific subset of keywords

    """
    return [PY_KW]

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @param lang_id: used for selecting a specific subset of syntax specs

    """
    return SYNTAX_ITEMS

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @param lang_id: used to select a specific set of properties

    """
    return [FOLD, TIMMY]

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @param lang_id: used to select a specific subset of comment pattern(s)

    """
    return [u'#']

#---- End Required Module Functions ----#

#---- Syntax Modules Internal Functions ----#
def KeywordString():
    """Returns the specified Keyword String
    @note: not used by most modules

    """
    return PY_KW[1]

#---- End Syntax Modules Internal Functions ----#

#-----------------------------------------------------------------------------#
