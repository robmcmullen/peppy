from peppy.editra.syntax import syntax
from peppy.editra.syntax import synglob
from peppy.editra.syntax import synextreg
from peppy.editra import ed_style

StyleItem = ed_style.StyleItem
NullStyleItem = ed_style.NullStyleItem

def PeppyDefaultStyleDictionaryCopy():
    """Get a new copy of the peppy default styles dict.
    
    """
    def_dict = \
        {'brace_good' : StyleItem("#000000", "#75FFA3,bold"),
         'brace_bad'  : StyleItem(back="#FF0090,bold"),
         'calltip'    : StyleItem("#404040", "#FFFFB8"),
         'ctrl_char'  : StyleItem("#000000"),
         'line_num'   : StyleItem(back="#C0C0C0", face="%(secondary)s", \
                                  size="%(size3)d"),
         'array_style': StyleItem("#EE8B02,bold", face="%(secondary)s"),
         'btick_style': StyleItem("#8959F6,bold", size="%(size)d"),
         'default_style': StyleItem("#000000", "#F6F6F6", \
                                    "%(primary)s", "%(size)d"),
         'char_style' : StyleItem("#FF3AFF"),
         'class_style' : StyleItem("#0000FF,bold"),
         'class2_style' : StyleItem("#2E8B57,bold"),
         'comment_style' : StyleItem("#FF0000,bold"),
         'decor_style' : StyleItem("#BA0EEA italic", face="%(secondary)s"),
         'directive_style' : StyleItem("#0000FF,bold", face="%(secondary)s"),
         'dockey_style' : StyleItem("#0000FF"),
         'error_style' : StyleItem("#DD0101,bold", face="%(secondary)s"),
         'funct_style' : StyleItem("#008B8B,italic"),
         'global_style' : StyleItem("#007F7F,bold", face="%(secondary)s"),
         'guide_style' : StyleItem("#838383"),
         'here_style' : StyleItem("#CA61CA,bold", face="%(secondary)s"),
         'ideol_style' : StyleItem("#E0C0E0", face="%(secondary)s"),
         'keyword_style' : StyleItem("#000000,bold"),
         'keyword2_style' : StyleItem("#2E8B57,bold"),
         'keyword3_style' : StyleItem("#0000FF,bold"),
         'keyword4_style' : StyleItem("#9D2424"),
         'marker_style' : StyleItem("#FFFFFF", "#000000"),
         'folder_style' : StyleItem("#FFFFFF", "#000000"),
         'number_style' : StyleItem("#387082"),
         'number2_style' : StyleItem("#A020F0,bold"),
         'operator_style' : StyleItem("#000000", face="%(primary)s,bold"),
         'pre_style' : StyleItem("#4939F2,bold"),               
         'pre2_style' : StyleItem("#AB39F2,bold", "#FFFFFF"),
         'regex_style' : StyleItem("#008B8B"),
         'scalar_style' : StyleItem("#AB37F2,bold", face="%(secondary)s"),
         'scalar2_style' : StyleItem("#AB37F2", face="%(secondary)s"),
         'select_style' : NullStyleItem(), # Use system default colour
         'string_style' : StyleItem("#1A701A"),
         'stringeol_style' : StyleItem("#000000,bold", "#EEC0EE,eol", \
                                       "%(secondary)s"),
         'unknown_style' : StyleItem("#FFFFFF,bold", "#DD0101,eol"),
         'whitespace_style' : StyleItem("#838383"),
         }
    return def_dict


# I override ed_style.DefaultStyleDictionary here so that I can replace the
# whole ed_style.py file when editra changes.
ed_style.DefaultStyleDictionary = PeppyDefaultStyleDictionaryCopy

__all__ = ['syntax', 'synglob', 'synextreg', 'ed_style']
