# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Actions for job control and process execution
"""

import os, glob

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.actions.base import *
from peppy.actions.minibuffer import *

from peppy.lib.processmanager import *

from peppy.debug import *


class RunMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'startInterpreter')
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and not hasattr(self.mode, 'process')

class RunScript(RunMixin, SelectAction):
    """Run this script through the interpreter
    
    If an interpreter has been set up for this major mode, this action causes
    the file to be saved and the interpreter to run using this file as input.
    Interpreter settings are controlled using the L{JobControlMixin} settings
    of the major mode in the Preferences dialog.
    """
    alias = "run-script"
    name = "Run"
    icon = 'icons/script_go.png'
    default_menu = ("Tools", 1)
    key_bindings = {'default': "F5"}

    def action(self, index=-1, multiplier=1):
        self.mode.startInterpreter()

class RunScriptWithArgs(RunMixin, SelectAction):
    """Run this script through the interpreter with optional arguments
    
    Like L{RunScript}, except provides the capability to specify optional
    arguments to the command line that runs the interpreter.
    """
    alias = "run-script-with-args"
    name = "Run with Args"
    icon = "icons/script_edit.png"
    default_menu = ("Tools", 2)
    key_bindings = {'default': "C-F5"}

    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Arguments:",
                                    initial = self.mode.getScriptArgs())
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.startInterpreter(text)

class RunFilter(RunMixin, SelectAction):
    """Run an external program on this file
    
    Similar to L{RunScript} except it provides the opportunity to specify the
    entire command line used to process the current file.
    """
    alias = "run-filter"
    name = "Run Filter"
    default_menu = ("Tools", 3)

    def action(self, index=-1, multiplier=1):
        cache = self.mode.getClassCache()
        if self.name in cache:
            last = cache[self.name]
        else:
            last = ''
        minibuffer = TextMinibuffer(self.mode, self, label="Command line:",
                                    initial = last)
        self.mode.setMinibuffer(minibuffer)
        self.mode.setStatusText("Enter command line, %s will be replaced by full path to file")

    def processMinibuffer(self, minibuffer, mode, text):
        cache = self.mode.getClassCache()
        cache[self.name] = text
        self.mode.startCommandLine(text, expand=True)

class StopScript(RunMixin, SelectAction):
    """Stop the currently running script
    
    If an interpreter is processing the current document, it can be forcefully
    stopped using this command.
    """
    alias = "stop-script"
    name = "Stop"
    icon = 'icons/stop.png'
    default_menu = ("Tools", 9)
    key_bindings = {'win': "C-CANCEL", 'emacs': "C-CANCEL", 'mac': 'C-.'}
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.stopInterpreter()


class JobControlMenu(IPeppyPlugin):
    """Plugin that provides the menu items for job control
    """
    def getActions(self):
        return [RunScript, RunScriptWithArgs, RunFilter, StopScript,
                ]
