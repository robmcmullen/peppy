# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""ChangeLog editing support.

Major mode for editing ChangeLogs.
"""

import os, struct, time
import keyword
from cStringIO import StringIO

import wx
import wx.stc

from peppy.actions import *
from peppy.major import *
from peppy.fundamental import FundamentalMode
from peppy.actions.base import *
from peppy.lib.autoindent import *
from peppy.lib.foldexplorer import *

class AddChangeLogEntry(STCModificationAction):
    """Add new ChangeLog entry to the top of the ChangeLog"""
    name = "Add ChangeLog Entry"
    default_menu = ("Tools", 500)
    key_bindings = {'emacs': "C-c C-n",}
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return issubclass(modecls, ChangeLogMode)
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        date = time.strftime(self.mode.classprefs.date_format_str)
        prefs = wx.GetApp().user.classprefs
        
        s = self.mode
        eol = s.getLinesep()
        pretext = "%s  %s  <%s>%s%s\t* " % (date, prefs.full_name, prefs.email,
            eol, eol)
        posttext = eol + eol
        
        existing = s.GetTextRange(0, len(pretext))
        if existing == pretext:
            # If we're trying to insert a new entry that matches the topmost
            # entry, don't do it.  Move to the first entry instead of
            # inserting a duplicate entry.
            s.GotoPos(len(pretext))
        else:
            # OK, the entry doesn't exist, so insert it.
            s.BeginUndoAction()
            s.InsertText(0, pretext + posttext)
            s.GotoPos(len(pretext))
            s.EndUndoAction()


# The ChangeLog major mode is descended from FundamentalMode, meaning that
# it is an STC based editing window.  Currently, no particular additional
# functionality is present in the mode except for overriding some
# classprefs
class ChangeLogMode(NonFoldCapableCodeExplorerMixin, FundamentalMode):
    """Major mode for editing ChangeLogs.
    
    """
    # keyword is required: it's a one-word name that must be unique
    # compared to all other major modes
    keyword='ChangeLog'
    
    # Specifying an icon here will cause it to be displayed in the tab
    # of any file using the ChangeLog mode
    icon='icons/text_list_bullets.png'
    
    default_classprefs = (
        StrParam('filename_regex', '([Cc]hange[Ll]og(:?(\..*|$)))', fullwidth=True),
        BoolParam('use_tab_characters', True, override_superclass=True),
        IntParam('tab_size', 8, override_superclass=True),
        IntParam('indent_size', 8, override_superclass=True),
        BoolParam('word_wrap', True),
        StrParam('date_format_str', "%Y-%m-%d", "Date format string, in strftime format"),
        Param('indent_after', r'(^[0-9])', fullwidth=True),
        Param('indent', r'\*', fullwidth=True),
        Param('unindent', r'(^[0-9])', fullwidth=True),
       )
    
    autoindent = None
    
    def createPostHook(self):
        if not self.autoindent:
            self.__class__.autoindent = RegexAutoindent(self.classprefs.indent_after,
                                                        self.classprefs.indent,
                                                        self.classprefs.unindent,
                                                        '')

    def checkFoldEntryFunctionName(self, line, last_line):
        text = self.GetLine(line)
        #dprint(text)
        if text[0:4].isdigit():
            return text, line, 1
        return "", -1, 1


# This is the plugin definition for ChangeLogMode.  This is the only way
# to inform peppy of the enhancement to the capabilities.  It will ignore
# anything defined in the file unless it is registered using methods of
# IPeppyPlugin.
class ChangeLogPlugin(IPeppyPlugin):
    """ChangeLog plugin to register modes and user interface.
    """
    # This registers the ChangeLog mode so that it can be used
    def getMajorModes(self):
        yield ChangeLogMode
        
    def getActions(self):
        return [AddChangeLogEntry]
