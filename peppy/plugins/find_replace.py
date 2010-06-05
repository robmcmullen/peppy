# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Find and replace minibuffer

This plugin includes the minibuffers for both the find and the find/replace
commands in peppy.
"""
import os, glob, re

import wx

from peppy.yapsy.plugins import *
from peppy.find_replace.actions import *

from peppy.fundamental import FundamentalMode

from peppy.about import AddCredit
AddCredit("Jan Hudec", "for the shell-style wildcard to regex converter from bzrlib")


class FindReplacePlugin(IPeppyPlugin):
    """Plugin containing of a bunch of cursor movement (i.e. non-destructive)
    actions.
    """

    def getCompatibleActions(self, modecls):
        if issubclass(modecls, FundamentalMode):
            return [FindText, FindRegex, FindWildcard, FindPrevText,
                    Replace, ReplaceRegex, ReplaceWildcard,
                    
                    CaseSensitiveSearch, WholeWordSearch, 
                    ]
