# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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

class KeyboardConf(IPeppyPlugin):
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
    valid_platforms = ['system default', 'win', 'emacs', 'mac']
    default_classprefs = (
        ChoiceParam('key_bindings', valid_platforms, 'system default', 'Platform type from which to emulate the\ndefault keybindings.'),
        )
    platform = 'win'
    
    ignore_list = ['MajorAction', 'MinibufferAction']

    def addCommandLineOptions(self, parser):
        parser.add_option("--key-bindings", action="store",
                          dest="key_bindings", default='')
        parser.add_option("--show-key-bindings", action="store_true",
                          dest="show_key_bindings")

    def processCommandLineOptions(self, options):
        #dprint(options.key_bindings)
        if options.key_bindings:
            self.platform = options.key_bindings
        else:
            self.platform = self.classprefs.key_bindings
        if self.platform == 'system default':
            if wx.Platform == '__WXMAC__':
                self.platform = 'mac'
            else:
                self.platform = 'win'
        self.load()
        if options.show_key_bindings:
            self.configDefault()
    
    def requestedShutdown(self):
        # FIXME: configuration file should be saved here
        pass

    def getKey(self, action):
        keyboard = None
        bindings = action.key_bindings
        if isinstance(bindings, dict):
            if self.platform in bindings:
                keyboard = bindings[self.platform]
            elif 'default' in bindings:
                keyboard = bindings['default']
        return keyboard
    
    def load(self):
        actions = getAllSubclassesOf(SelectAction)
        #dprint(actions)
        found_emacs = False
        for action in actions:
            #dprint("%s: default=%s new=%s" % (action.__name__, action.keyboard, self.classprefs._get(action.__name__)))

            # Use the action key binding from the configuration, if it exists
            found = False
            if hasattr(self.classprefs, action.__name__):
                acc = self.classprefs._get(action.__name__)
                if acc.lower() != 'default':
                    if acc.lower() == "none":
                        # if the text is None, don't bind it to anything.
                        action.keyboard = None
                    else:
                        action.keyboard = acc
                    found = True
            if not found:
                action.keyboard = self.getKey(action)

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

    def configDefault(self, fh=sys.stdout):
        lines = []
        lines.append("[%s]" % self.__class__.__name__)
        keymap = {}
        for action in getAllSubclassesOf(SelectAction):
            if not issubclass(action, ToggleAction) and not issubclass(action, ListAction) and action.__name__ not in self.ignore_list:
                keymap[action.__name__] = self.getKey(action)
        names = keymap.keys()
        names.sort()
        for name in names:
            lines.append("%s = %s" % (name, keymap[name]))
        fh.write(os.linesep.join(lines) + os.linesep)
