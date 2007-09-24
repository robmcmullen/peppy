# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.debug import *
from peppy.configprefs import *
from peppy.lib.userparams import *

from peppy.trac.core import *

class KeyboardConf(ClassPrefs, debugmixin):
    """Loader for keyboard configurations.

    Keyboard accelerator settings are made in the application
    configuration file peppy.cfg in the user's configuration
    directory.  In the file, the section KeyboardConf is used to map
    an action name to its keyboard accelerator.

    For example:

      [KeyboardConf]
      Copy = C-C
      Open = C-X C-F
      SaveAs = None
      Help = default

    will set the keyboard accelerators for the Copy and Open actions,
    remove any keyboard accelerator from SaveAs, and use the
    application's default setting for Help.  Additionally, if an
    action doesn't appear in the KeyboardConf section it will also use
    the application's default value (which is specified in the source
    code.)
    """
    default_classprefs = ()
    platform = 'win'
    
    ignore_list = ['MajorAction', 'MinibufferAction']

    @classmethod
    def getKey(cls, action):
        keyboard = None
        bindings = action.key_bindings
        if isinstance(bindings, dict):
            if cls.platform in bindings:
                keyboard = bindings[cls.platform]
            elif 'default' in bindings:
                keyboard = bindings['default']
        return keyboard
    
    @classmethod
    def load(cls):
        actions = getAllSubclassesOf(SelectAction)
        #dprint(actions)
        found_emacs = False
        for action in actions:
            #dprint("%s: default=%s new=%s" % (action.__name__, action.keyboard, cls.classprefs._get(action.__name__)))
            acc = cls.classprefs._get(action.__name__)
            if acc is not None and acc.lower() != 'default':
                if acc.lower() == "none":
                    # if the text is None, don't bind it to anything.
                    action.keyboard = None
                else:
                    action.keyboard = acc
            else:
                action.keyboard = cls.getKey(action)

            # Determine up the accelerator text here, up front, rather
            # than computing it every time the menu is displayed.
            numkeystrokes = action.setAcceleratorText()
            if numkeystrokes>1:
                found_emacs = True

        if found_emacs:
            # Found a multi-key accelerator: force all accelerators to
            # be displayed in emacs style.
            for action in actions:
                action.setAcceleratorText(force_emacs=True)

    @classmethod
    def configDefault(cls, fh=sys.stdout):
        lines = []
        lines.append("[%s]" % cls.__name__)
        keymap = {}
        for action in getAllSubclassesOf(SelectAction):
            if not issubclass(action, ToggleAction) and not issubclass(action, ListAction) and action.__name__ not in cls.ignore_list:
                keymap[action.__name__] = cls.getKey(action)
        names = keymap.keys()
        names.sort()
        for name in names:
            lines.append("%s = %s" % (name, keymap[name]))
        fh.write(os.linesep.join(lines) + os.linesep)

class KeyboardConfExtender(IPeppyPlugin):
    def loadConf(self):
        KeyboardConf.platform = wx.GetApp().classprefs.key_bindings
        KeyboardConf.load()
    
    def saveConf(self):
        pass
    
