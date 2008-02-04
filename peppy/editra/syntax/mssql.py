###############################################################################
# Name: mssql.py                                                              #
# Purpose: Define Microsoft SQL syntax for highlighting and other features    #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: mssql.py                                                              #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# Lexer configuration module for Microsoft SQL.                               #
#                                                                             #
# @todo: too many to list                                                     #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: mssql.py 49250 2007-10-20 02:40:49Z CJP $"
__revision__ = "$Revision: 49250 $"

#-----------------------------------------------------------------------------#
# Dependancies

#-----------------------------------------------------------------------------#

#---- Keyword Specifications ----#

# Data Types
MSSQL_DAT = (0, "")
# System Tables
MSSQL_SYS = (1, "")
# Global Variables
MSSQL_GLOB = (2, "")
# Functions
MSSQL_FUNC = (3, "")
# System Stored Procedures
MSSQL_SYSP = (4, "")
# Operators
MSSQL_OPS = (5, "")

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [ ('STC_MSSQL_DEFAULT', 'default_style'),
                 ('STC_MSSQL_COMMENT', 'comment_style'),
                 ('STC_MSSQL_COLUMN_NAME', 'keyword_style'),
                 ('STC_MSSQL_COLUMN_NAME_2', 'keyword_style'),
                 ('STC_MSSQL_DATATYPE', 'keyword2_style'),
                 ('STC_MSSQL_DEFAULT_PREF_DATATYPE', 'class_style'),
                 ('STC_MSSQL_FUNCTION', 'keyword3_style'),
                 ('STC_MSSQL_GLOBAL_VARIABLE', 'global_style'),
                 ('STC_MSSQL_IDENTIFIER', 'default_style'),
                 ('STC_MSSQL_LINE_COMMENT', 'comment_style'),
                 ('STC_MSSQL_NUMBER', 'number_style'),
                 ('STC_MSSQL_OPERATOR', 'operator_style'),
                 ('STC_MSSQL_STATEMENT', 'keyword_style'),
                 ('STC_MSSQL_STORED_PROCEDURE', 'scalar2_style'),
                 ('STC_MSSQL_STRING', 'string_style'),
                 ('STC_MSSQL_SYSTABLE', 'keyword4_style'),
                 ('STC_MSSQL_VARIABLE', 'scalar_style') ]

#---- Extra Properties ----#
FOLD = ("fold", "1")
FOLD_COMMENT = ("fold.comment", "1")
FOLD_COMPACT = ("fold.compact", "1")

#-----------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @param lang_id: used to select specific subset of keywords

    """
    return list()

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @param lang_id: used for selecting a specific subset of syntax specs

    """
    return SYNTAX_ITEMS

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @param lang_id: used to select a specific set of properties

    """
    return [FOLD]

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @param lang_id: used to select a specific subset of comment pattern(s)

    """
    return [u'--']
#---- End Required Module Functions ----#

#---- Syntax Modules Internal Functions ----#
def KeywordString():
    """Returns the specified Keyword String
    @note: not used by most modules

    """
    return None

#---- End Syntax Modules Internal Functions ----#
