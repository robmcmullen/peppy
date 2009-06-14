# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Simple macros created by recording actions

This plugin provides macro recording
"""

import os

import wx

from peppy.fundamental import FundamentalMode
from peppy.yapsy.plugins import *

from peppy.actions.base import *
from peppy.actions import *
from peppy.lib.multikey import *
from peppy.debug import *


class RecordedAction(debugmixin):
    def __init__(self):
        pass
    
    def canCoelesce(self, next_action):
        return False
    
    def coelesce(self, next_action, evt, multiplier):
        raise NotImplementedError


class RecordedKeyboardAction(RecordedAction):
    def __init__(self, action, evt, multiplier):
        self.evt = FakeCharEvent(evt)
        self.action = action
        self.multiplier = multiplier
    
    def __str__(self):
        return "%s: %dx%s" % (self.action, self.multiplier, self.evt.GetKeyCode())
    
    def canCoelesce(self, next_action):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        if hasattr('canCoelesce', self.action):
            return self.action.canCoelesce(next_action)
        return False
    
    def coelesce(self, next_action, evt, multiplier):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        action = self.action.coelesce(next_action, evt, multiplier)


class ActionRecorder(AbstractActionRecorder, debugmixin):
    def __init__(self):
        self.recording = []
    
    def recordKeystroke(self, action, evt, multiplier):
        record = RecordedKeyboardAction(action, evt, multiplier)
        dprint(record)
        self.recording.append(record)
    
    def getRecordedActions(self):
        return self.recording


class StartRecordingMacro(SelectAction):
    """Begin recording actions"""
    name = "Start Recording"
    default_menu = (("Tools/Macros", -800), 100)
    
    def action(self, index=-1, multiplier=1):
        self.frame.root_accel.startRecordingActions(ActionRecorder())


class StopRecordingMacro(SelectAction):
    """Stop recording actions"""
    name = "Stop Recording"
    default_menu = ("Tools/Macros", 110)
    
    def action(self, index=-1, multiplier=1):
        recorder = self.frame.root_accel.stopRecordingActions()
        actions = recorder.getRecordedActions()
        for action in actions:
            dprint(action)


class MacroPlugin(IPeppyPlugin):
    """Plugin providing the macro recording capability
    """
    def getActions(self):
        return [StartRecordingMacro, StopRecordingMacro]
