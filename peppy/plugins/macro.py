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


class PlaybackState(object):
    def __init__(self, frame, mode):
        self.frame = frame
        self.mode = mode


class RecordedAction(debugmixin):
    def __init__(self):
        pass
    
    def canCoalesce(self, next_action):
        return False
    
    def coalesce(self, next_action, evt, multiplier):
        raise NotImplementedError
    
    def performAction(self, system_state):
        raise NotImplementedError


class RecordedKeyboardAction(RecordedAction):
    def __init__(self, action, evt, multiplier):
        self.evt = FakeCharEvent(evt)
        
        # Hack to force SelfInsertCommand to process the character, because
        # normally it uses the evt.Skip() to force the EVT_CHAR handler to
        # insert the character.
        self.evt.is_quoted = True
        
        self.actioncls = action.__class__
        self.multiplier = multiplier
    
    def __str__(self):
        return "%s: %dx%s" % (self.actioncls.__name__, self.multiplier, self.evt.GetKeyCode())
    
    def canCoalesce(self, next_action):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        if hasattr('canCoalesce', self.actioncls):
            return self.action.canCoalesce(next_action)
        return False
    
    def coalesce(self, next_action, evt, multiplier):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        action = self.action.coalesce(next_action, evt, multiplier)
    
    def performAction(self, system_state):
        action = self.actioncls(system_state.frame, mode=system_state.mode)
        dprint(action)
        action.actionKeystroke(self.evt, self.multiplier)


class ActionRecorder(AbstractActionRecorder, debugmixin):
    def __init__(self):
        self.recording = []
    
    def __str__(self):
        lines = []
        for recorded_item in self.recording:
            lines.append(str(recorded_item))
        return "\n".join(lines)
        
    def recordKeystroke(self, action, evt, multiplier):
        record = RecordedKeyboardAction(action, evt, multiplier)
        dprint(record)
        self.recording.append(record)
    
    def getRecordedActions(self):
        return self.recording
    
    def playback(self, frame, mode):
        state = PlaybackState(frame, mode)
        dprint(state)
        for recorded_action in self.recording:
            recorded_action.performAction(state)


class StartRecordingMacro(SelectAction):
    """Begin recording actions"""
    name = "Start Recording"
    key_bindings = {'default': "C-1", }
    default_menu = (("Tools/Macros", -800), 100)
    
    def action(self, index=-1, multiplier=1):
        self.frame.root_accel.startRecordingActions(ActionRecorder())


class StopRecordingMacro(SelectAction):
    """Stop recording actions"""
    name = "Stop Recording"
    key_bindings = {'default': "C-2", }
    default_menu = ("Tools/Macros", 110)
    
    def action(self, index=-1, multiplier=1):
        recorder = self.frame.root_accel.stopRecordingActions()
        dprint(recorder)
        ReplayLastMacro.setLastMacro(recorder)


class ReplayLastMacro(SelectAction):
    """Play back last macro that was recorded"""
    name = "Play Last Macro"
    key_bindings = {'default': "C-3", }
    default_menu = ("Tools/Macros", 110)
    
    last_recording = None
    
    @classmethod
    def setLastMacro(cls, recording):
        cls.last_recording = recording
    
    def action(self, index=-1, multiplier=1):
        dprint("Playing back %s" % self.last_recording)
        if self.last_recording:
            while multiplier > 0:
                self.last_recording.playback(self.frame, self.mode)
                multiplier -= 1
        else:
            dprint("No recorded macro.")
        


class MacroPlugin(IPeppyPlugin):
    """Plugin providing the macro recording capability
    """
    def getActions(self):
        return [StartRecordingMacro, StopRecordingMacro, ReplayLastMacro]
