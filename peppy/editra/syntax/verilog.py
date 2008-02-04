###############################################################################
# Name: verilog.py                                                            #
# Purpose: Configuration module for Verilog HDL language                      #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2007 Cody Precord <staff@editra.org>                         #
# Licence: wxWindows Licence                                                  #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: verilog.py                                                            #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# Lexer configuration module for Verilog Hardware Description Language        #
#                                                                             #
# @todo:                                                                      #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: verilog.py 49390 2007-10-24 11:46:23Z CJP $"
__revision__ = "$Revision: 49390 $"

#-----------------------------------------------------------------------------#
import synglob

#-----------------------------------------------------------------------------#

#---- Keyword Definitions ----#
KEYWORDS = (0, "always and assign attribute begin buf bufif0 bufif1 case casex "
               "casez cmos deassign default defparam disable edge else end "
               "endattribute endcase endfunction endmodule endprimitive "
               "endspecify endtable endtask event for force forever fork "
               "function highz0 highz1 if ifnone initial inout input integer "
               "join medium module large macromodule nand negedge nmos nor not "
               "notif0 notif1 or output parameter pmos posedge primitive pull0 "
               "pull1 pulldown pullup rcmos real realtime reg release repeat "
               "rnmos rpmos rtran rtranif0 rtranif1 scalared signed small "
               "specify specparam strength strong0 strong1 supply0 supply1 "
               "table task time tran tranif0 tranif1 tri tri0 tri1 triand "
               "trior trireg unsigned vectored wait wand weak0 weak1 while "
               "wire wor xnor xor")

KEYWORDS2 = (1, "")

TASKS = (2, "$display $displayb $displayh $displayo $monitor $monitorb "
            "$monitorh $monitoro $monitoroff $monitoron $strobe $strobeb "
            "$strobeh $strobeo $write $writeb $writeh $writeo $fclose "
            "$fdisplay $fdisplayb $fdisplayh $fdisplayo $ferror $fflush $fgetc "
            "$fgets $fmonitor $fmonitorb $fmonitorh $fmonitoro $fopen $fread "
            "$fscanf $fseek $fstrobe $fstrobeb $fstrobeh $fstrobeo $ftell "
            "$fwrite $fwriteb $fwriteh $fwriteo $readmemb $readmemh $rewind "
            "$sdf_annotate $sformat $sscanf $swrite $swriteb $swriteh $swriteo "
            "$ungetc $printtimescale $timeformat $finish $stop "
            "$async$and$array $async$nand$array $async$nor$array "
            "$async$or$array $sync$and$array $sync$nand$array $sync$nor$array "
            "$sync$or$array $async$and$plane $async$nand$plane "
            "$async$nor$plane $async$or$plane $sync$and$plane $sync$nand$plane "
            "$sync$nor$plane $sync$or$plane $q_add $q_exam $q_full "
            "$q_initialize $q_remove $realtime $stime $time $bitstoreal "
            "$realtobits $itor $rtoi $signed $unsigned $dist_chi_square "
            "$dist_erlang $dist_exponential $dist_normal $dist_poisson $dist_t "
            "$dist_uniform $random $test$plusargs $value$plusargs $dumpall "
            "$dumpfile $dumpflush $dumplimit $dumpoff $dumpon $dumpports "
            "$dumpportsall $dumpportsflush $dumpportslimit $dumpportsoff "
            "$dumpportson $dumpvars")

USER_KW = (3, "")

#---- End Keyword Definitions ----#

#---- Syntax Style Specs ----#
SYNTAX_ITEMS = [('STC_V_COMMENT', 'comment_style'),
                ('STC_V_COMMENTLINE', 'comment_style'),
                ('STC_V_COMMENTLINEBANG', 'comment_style'),
                ('STC_V_DEFAULT', 'default_style'),
                ('STC_V_IDENTIFIER', 'default_style'),
                ('STC_V_NUMBER', 'number_style'),
                ('STC_V_OPERATOR', 'operator_style'),
                ('STC_V_PREPROCESSOR', 'pre_style'),
                ('STC_V_STRING', 'string_style'),
                ('STC_V_STRINGEOL', 'stringeol_style'),
                ('STC_V_USER', 'default_style'),
                ('STC_V_WORD', 'keyword_style'),
                ('STC_V_WORD2', 'default_style'),
                ('STC_V_WORD3', 'scalar_style')]

#---- Extra Properties ----#
FOLD = ("fold", "1")
FOLD_CMT = ("fold.comment", "1")
FOLD_PRE = ("fold.preprocessor", "1")
FOLD_COMP = ("fold.compact", "1")
FOLD_ELSE = ("fold.at.else", "0")
FOLD_MOD = ("fold.verilog.flags", "0")

#-----------------------------------------------------------------------------#

#---- Required Module Functions ----#
def Keywords(lang_id=0):
    """Returns Specified Keywords List
    @keyword lang_id: used to select specific subset of keywords

    """
    if lang_id == synglob.ID_LANG_VERILOG:
        return [KEYWORDS, KEYWORDS2, TASKS]
    else:
        return list()

def SyntaxSpec(lang_id=0):
    """Syntax Specifications
    @keyword lang_id: used for selecting a specific subset of syntax specs

    """
    if lang_id == synglob.ID_LANG_VERILOG:
        return SYNTAX_ITEMS
    else:
        return list()

def Properties(lang_id=0):
    """Returns a list of Extra Properties to set
    @keyword lang_id: used to select a specific set of properties

    """
    if lang_id == synglob.ID_LANG_VERILOG:
        return [FOLD]
    else:
        return list()

def CommentPattern(lang_id=0):
    """Returns a list of characters used to comment a block of code
    @keyword lang_id: used to select a specific subset of comment pattern(s)

    """
    if lang_id == synglob.ID_LANG_VERILOG:
        return [u'//']
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
