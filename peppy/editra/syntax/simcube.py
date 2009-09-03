# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Lexer for simcube scripts

Based on the sh.py lexer for shell scripts.
"""

import synglob

COMM_KEYWORDS = (0, "samples lines bands datatype output_scale "
                 "load input_scale background square "
                 "output")

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [ ('STC_SH_DEFAULT', 'default_style'),
                 ('STC_SH_BACKTICKS', 'scalar_style'),
                 ('STC_SH_CHARACTER', 'char_style'),
                 ('STC_SH_COMMENTLINE', 'comment_style'),
                 ('STC_SH_ERROR', 'error_style'),
                 ('STC_SH_HERE_DELIM', 'here_style'),
                 ('STC_SH_HERE_Q', 'here_style'),
                 ('STC_SH_IDENTIFIER', 'default_style'),
                 ('STC_SH_NUMBER', 'number_style'),
                 ('STC_SH_OPERATOR', 'operator_style'),
                 ('STC_SH_PARAM', 'scalar_style'),
                 ('STC_SH_SCALAR', 'scalar_style'),
                 ('STC_SH_STRING', 'string_style'),
                 ('STC_SH_WORD', 'keyword_style') ]

#---- Extra Properties ----#
FOLD = ("fold", "1")
FLD_COMMENT = ("fold.comment", "1")
FLD_COMPACT = ("fold.compact", "0")

#------------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @param lang_id: used to select specific subset of keywords

    """
    return [COMM_KEYWORDS]

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @param lang_id: used for selecting a specific subset of syntax specs

    """
    return SYNTAX_ITEMS

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @param lang_id: used to select a specific set of properties

    """
    return [FOLD, FLD_COMMENT, FLD_COMPACT]

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @param lang_id: used to select a specific subset of comment pattern(s)

    """
    return [u'#']
#---- End Required Functions ----#

#---- Syntax Modules Internal Functions ----#
def KeywordString():
    """Returns the specified Keyword String
    @note: not used by most modules

    """
    return None

#---- End Syntax Modules Internal Functions ----#
