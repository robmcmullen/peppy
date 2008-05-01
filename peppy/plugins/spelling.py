# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Spell checking provider
"""

import os, sys

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.lib.stcspellcheck import *


class SpellCheck(IPeppyPlugin):
    """Plugin for spell check provider

    This simple plugin provides the spelling checker for Fundamental mode.
    """
    def activateHook(self):
        Publisher().subscribe(self.getProvider, 'spelling.provider')
        Publisher().subscribe(self.defaultLanguage, 'spelling.default_language')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getProvider)
        Publisher().unsubscribe(self.defaultLanguage)

    def getProvider(self, message):
        message.data.append(STCSpellCheck)
    
    def defaultLanguage(self, message):
        lang = message.data
        STCSpellCheck.setDefaultLanguage(lang)
