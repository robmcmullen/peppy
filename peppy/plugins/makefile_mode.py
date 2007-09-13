# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Makefile editing support.

Major mode for editing makefiles.
"""

import os,struct
import keyword
from cStringIO import StringIO

import wx
import wx.stc

from peppy.menu import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

from peppy.about import SetAbout

_sample_file = """\
VAR = something
OTHER = $(VAR)
OTHER1 = ${VAR}
DIR = $(shell ls -1)

.SUFFIXES: .o

all: foo
	echo stuff

foo: bar.o baz.o

clean:
	rm -rf *~ *.o
    
.PHONY: print-% clean

print-%: ; @ echo $* = $($*)
"""

SetAbout('sample.mak',_sample_file)


class SampleMakefile(SelectAction):
    name = _("&Open Sample Makefile")
    tooltip = _("Open a sample Makefile")
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:sample.mak")


class MakefileMode(FundamentalMode):
    """Major mode for editing Makefiles.

    STC has a built-in Makefile mode, so we'll be using that.
    """
    keyword='Makefile'
    icon='icons/cog.png'
    regex="(\.mak|[Mm]akefile)$"

    start_line_comment = "# "

    default_classprefs = (
        StrParam('minor_modes', ''),
        IntParam('tab_size', 8),
        BoolParam('word_wrap', True),
        StrParam('sample_file', _sample_file),
        IntParam('stc_lexer', wx.stc.STC_LEX_MAKEFILE),
        StrParam('stc_keywords', 'if or and ifeq ifneq else endif ifdef ifndef subst patsubst strip findstring filter filter-out sort word wordlist words firstword lastword dir notdir suffix basename addsuffix addprefix join wildcard realpath abspath foreach call value eval origin flavor shell error warning info'),
        ReadOnlyParam('stc_boa_style_names', {wx.stc.STC_MAKE_DEFAULT: 'Default',
                                wx.stc.STC_MAKE_COMMENT: 'Comment',
                                wx.stc.STC_MAKE_IDENTIFIER: 'Variable or identifier',
                                wx.stc.STC_MAKE_PREPROCESSOR: 'Preprocessor',
                                wx.stc.STC_MAKE_OPERATOR: 'Operator',
                                wx.stc.STC_MAKE_IDEOL: 'Identifier unclosed string',
                                wx.stc.STC_MAKE_TARGET: 'Target',
                                }),
        ReadOnlyParam('stc_lexer_styles', {wx.stc.STC_MAKE_DEFAULT: '',
                             wx.stc.STC_MAKE_COMMENT: 'fore:%(comment-col)s,italic',
                             wx.stc.STC_MAKE_IDENTIFIER: 'fore:%(identifier-col)s,bold',
                             wx.stc.STC_MAKE_PREPROCESSOR: 'fore:#008040,back:#EAFFEA',
                             wx.stc.STC_MAKE_OPERATOR: 'fore:#A020F0',
                             wx.stc.STC_MAKE_IDEOL: 'fore:#808000',
                             wx.stc.STC_MAKE_TARGET: 'bold,fore:#004080',
                             }),
        )


class MakefilePlugin(MajorModeMatcherBase,debugmixin):
    """Makefile plugin to register modes and user interface.
    """
    implements(IMajorModeMatcher)
    implements(IMenuItemProvider)

    def possibleModes(self):
        yield MakefileMode
    
    default_menu=((None,None,Menu(_("Test")).after(_("Minor Mode"))),
                  (None,_("Test"),MenuItem(SampleMakefile)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

