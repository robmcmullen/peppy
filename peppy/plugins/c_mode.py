# peppy Copyright (c) 2006-2007 Rob McMullen
# c_mode Copyright (c) 2007 Julian Back
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""C programming language editing support.

Major mode for editing ANSI C files.
"""

import os

import wx
import wx.stc

from peppy.major import *
from peppy.fundamental import FundamentalMode

from peppy.about import SetAbout

_sample_file="""\
#include <stdio.h>

int main(int argc, char *argv[])
{
   printf("Hello, world!\\n");
   return 0;
}
"""

SetAbout('hello.c',_sample_file)

class SampleCFile(SelectAction):
   name = _("&Open Sample C File")
   tooltip = _("Open a sample C file")
   icon = wx.ART_FILE_OPEN

   def action(self, pos=-1):
       assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
       self.frame.open("about:hello.c")

class CMode(FundamentalMode):
   """Major mode for editing C files.
   """
   keyword='C'
   icon='icons/page_white_c.png'
   regex="(\.c|\.h)$"

   default_settings = {
       'sample_file': _sample_file,
       'stc_lexer': wx.stc.STC_LEX_CPP,
       # These are the ANSI/ISO C (C90) keywords.  C99, C++, GNU &
       # Microsoft extensions could be added.
       'stc_keywords': 'auto break case char const continue default do double else enum extern float for goto if int long register return short signed sizeof static struct switch typedef union unsigned void volatile while',
       'stc_boa_style_names': {wx.stc.STC_C_DEFAULT: 'Default',
                               wx.stc.STC_C_COMMENT: 'Comment',
                               wx.stc.STC_C_COMMENTLINE: 'Comment line',
                               wx.stc.STC_C_COMMENTDOC: 'Comment doc',
                               wx.stc.STC_C_NUMBER: 'Number',
                               wx.stc.STC_C_WORD: 'Keyword',
                               wx.stc.STC_C_STRING: 'String',
                               wx.stc.STC_C_PREPROCESSOR: 'Preprocessor',
                               wx.stc.STC_C_OPERATOR: 'Operator',
                               wx.stc.STC_C_STRINGEOL: 'EOL unclosed string',
                               },
       'stc_lexer_styles': {wx.stc.STC_C_COMMENTLINE: wx.stc.STC_C_COMMENT,
                            wx.stc.STC_C_COMMENTDOC: wx.stc.STC_C_COMMENT,
                            wx.stc.STC_C_NUMBER: 'fore:#0076AE',
                            wx.stc.STC_C_WORD: 'bold,fore:#004080',
                            wx.stc.STC_C_STRING: 'fore:#800080',
                            wx.stc.STC_C_PREPROCESSOR: 'fore:#808000',
                            wx.stc.STC_C_OPERATOR: 'bold',
                            wx.stc.STC_C_STRINGEOL: 'back:#FFD5FF',
                            },
       }


class CModePlugin(MajorModeMatcherBase,debugmixin):
   """C plugin to register modes and user interface.
   """
   implements(IMajorModeMatcher)
   implements(IMenuItemProvider)

   def possibleModes(self):
       yield CMode

   default_menu=((None,None,Menu(_("Test")).after(_("Minor Mode"))),
                 (None,_("Test"),MenuItem(SampleCFile)),
                 )
   def getMenuItems(self):
       for mode,menu,item in self.default_menu:
           yield (mode,menu,item)
