###############################################################################
# Name: sql.py                                                                #
# Purpose: Define SQL syntax for highlighting and other features              #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: sql.py                                                                #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# Lexer configuration module for Oracle SQL                                   #
#                                                                             #
# @todo: Only Comment/Number highlight seems to work right now                #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: sql.py 609 2007-10-08 06:54:00Z CodyPrecord $"
__revision__ = "$Revision: 609 $"

#-----------------------------------------------------------------------------#
# Dependancies
import synglob
#-----------------------------------------------------------------------------#

#---- Keyword Specifications ----#

# SQL Keywords
SQL_KW = (0, "abort access accessed add after all alter and any as asc "
             "attribute audit authorization avg base_table before between by "
             "cascade cast check cluster clusters colauth column comment "
             "compress connect constraint crash create current data database "
             "data_base dba default delay delete desc distinct drop dual else "
             "exclusive exists extends extract file force foreign from grant "
             "group having heap identified identifier immediate in including "
             "increment index indexes initial insert instead intersect into "
             "invalidate is isolation key library like lock maxextents minus "
             "mode modify multiset nested noaudit nocompress not nowait of off "
             "offline on online operator option or order organization pctfree "
             "primary prior private privileges public quota release rename "
             "replace resource revoke rollback row rowlabel rows schema select "
             "separate session set share size space start store successful "
             "synonym sysdate table tables tablespace temporary to treat "
             "trigger truncate uid union unique unlimited update use user "
             "validate values view whenever where with true false null")

# SQL DB Objects (Types)
SQL_DBO = (1, "anydata anytype bfile binary_integer blob boolean byte char "
              "character clob cursor date day dec decimal double long number "
              "dsinterval_unconstrained float hour int integer interval lob "
              "minute mlslabel month natural naturaln nchar nchar_cs nclob "
              "numeric nvarchar pls_int pls_integer positive positiven table "
              "raw real record second signtype smallint string sys_refcursor "
              "time timestamp timestamp_unconstrained zone precision "
              "timestamp_ltz_unconstrained urowid varchar varchar2 year "
              "yminterval_unconstrained timestamp_tz_unconstrained ")
# SQL PLDoc
SQL_PLD = (2, "TODO param author since return see deprecated")

# SQL Plus
SQL_PLUS = (3, "acc~ept a~ppend archive log attribute bre~ak bti~tle c~hange "
               "col~umn comp~ute conn~ect copy def~ine del desc~ribe pau~se "
               "e~dit exec~ute exit get help ho~st i~nput l~ist passw~ord "
               "pri~nt pro~mpt quit recover rem~ark repf~ooter reph~eader r~un "
               "sav~e set sho~w shutdown spo~ol sta~rt startup store timi~ng "
               "undef~ine var~iable whenever oserror whenever sqlerror cl~ear "
               "disc~onnect ti~tle ")

# SQL User KW1 (PL/SQL Functions)
SQL_UKW1 = (4, "abs acos add_months ascii asciistr asin atan atan2 bfilename "
               "bitand ceil chartorowid chr coalesce commit commit_cm compose "
               "concat convert cos cosh count cube current_date current_time "
               "current_timestamp dbtimezone decode decompose deref dump "
               "empty_blob empty_clob exists exp floor from_tz getbnd glb "
               "greatest greatest_lb grouping hextoraw initcap nstr instr2 "
               "instr4 instrb instrc isnchar last_day least least_ub length "
               "length2 length4 lengthb lengthc ln localtime localtimestamp "
               "log lower lpad ltrim lub make_ref max min mod months_between "
               "nchartorowid nchr new_time next_day nhextoraw nls_initcap "
               "nls_charset_decl_len nls_charset_id nls_charset_name round "
               "nls_lower nlssort nls_upper nullfn nullif numtodsinterval "
               "numtoyminterval nvl power raise_application_error rawtohex "
               "rawtonhex ref reftohex replace rollback_nr rollback_sv rollup "
               "rowidtochar rowidtonchar rowlabel rpad rtrim savepoint soundex "
               "sessiontimezone setbnd set_transaction_use sign sin sinh "
               "sqlcode sqlerrm sqrt stddev substr substr2 substr4 substrb "
               "substrc sum sys_at_time_zone sys_context sysdate to_date "
               "sys_extract_utc sys_guid sys_literaltodate sys_over__di"
               "sys_literaltodsinterval sys_literaltotime sys_over__tt "
               "sys_literaltotimestamp sys_literaltotztime sys_over__id"
               "sys_literaltotztimestamp sys_literaltoyminterval sys_over__dd "
               "sys_over_iid sys_over_iit sys_over__it sys_over__ti to_number "
               "systimestamp tan tanh to_anylob to_blob to_char to_clob "
               "to_dsinterval to_label to_multi_byte to_nchar to_nclob uid "
               "to_raw to_single_byte to_time to_timestamp to_timestamp_tz "
               "to_time_tz to_yminterval translate treat trim trunc tz_offset "
               "unistr upper urowid user userenv value variance vsize work xor")

# SQL User KW2 (PL/SQL Exceptions)
SQL_UKW2 = (5, "access_into_null case_not_found collection_is_null "
               "cursor_already_open dup_val_on_index invalid_cursor "
               "login_denied no_data_found not_logged_on program_error "
               "rowtype_mismatch self_is_null storage_error invalid_number"
               "subscript_outside_limit sys_invalid_rowid timeout_on_resource "
               "too_many_rows value_error zero_divide  subscript_beyond_count ")

# SQL User KW3
SQL_UKW3 = (6, "")

# SQL User KW4
SQL_UKW4 = (7, "")

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [ ('STC_SQL_DEFAULT', 'default_style'),
                 ('STC_SQL_CHARACTER', 'char_style'),
                 ('STC_SQL_COMMENT', 'comment_style'),
                 ('STC_SQL_COMMENTDOC', 'comment_style'),
                 ('STC_SQL_COMMENTDOCKEYWORD', 'dockey_style'),
                 ('STC_SQL_COMMENTDOCKEYWORDERROR', 'error_style'),
                 ('STC_SQL_COMMENTLINE', 'comment_style'),
                 ('STC_SQL_COMMENTLINEDOC', 'comment_style'),
                 ('STC_SQL_IDENTIFIER', 'default_style'),
                 ('STC_SQL_NUMBER', 'number_style'),
                 ('STC_SQL_OPERATOR', 'operator_style'),
                 ('STC_SQL_QUOTEDIDENTIFIER', 'default_style'),
                 ('STC_SQL_SQLPLUS', 'scalar_style'),
                 ('STC_SQL_SQLPLUS_COMMENT', 'comment_style'),
                 ('STC_SQL_SQLPLUS_PROMPT', 'default_style'),
                 ('STC_SQL_STRING', 'string_style'),
                 ('STC_SQL_USER1', 'funct_style'),
                 ('STC_SQL_USER2', 'number2_style'),
                 ('STC_SQL_USER3', 'default_style'),
                 ('STC_SQL_USER4', 'default_style'),
                 ('STC_SQL_WORD', 'keyword_style'),
                 ('STC_SQL_WORD2', 'keyword2_style') ]

#---- Extra Properties ----#
FOLD = ("fold", "1")
FLD_COMMENT = ("fold.comment", "0")
FLD_COMPACT = ("fold.compact", "0")
FLD_SQL_OB = ("fold.sql.only.begin", "0")
#-----------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @param lang_id: used to select specific subset of keywords

    """
    if lang_id == synglob.ID_LANG_SQL:
        return [SQL_KW, SQL_DBO, SQL_PLD, SQL_PLUS, SQL_UKW1, SQL_UKW2]
    else:
        return list()

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @param lang_id: used for selecting a specific subset of syntax specs

    """
    if lang_id == synglob.ID_LANG_SQL:
        return SYNTAX_ITEMS
    else:
        return list()

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @param lang_id: used to select a specific set of properties

    """
    if lang_id == synglob.ID_LANG_SQL:
        return [FOLD]
    else:
        return list()

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @param lang_id: used to select a specific subset of comment pattern(s)

    """
    if lang_id == synglob.ID_LANG_SQL:
        return [u'--']
    else:
        return list()
#---- End Required Module Functions ----#

#---- Syntax Modules Internal Functions ----#
def KeywordString():
    """Returns the specified Keyword String
    @note: not used by most modules

    """
    return None

#---- End Syntax Modules Internal Functions ----#
