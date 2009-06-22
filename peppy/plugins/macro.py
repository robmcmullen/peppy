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


class CharEvent(FakeCharEvent):
    """Fake character event used by L{RecordKeyboardAction} when generating
    scripted copies of an action list.
    
    """
    def __init__(self, key, unicode, modifiers):
        self.id = -1
        self.event_object = None
        self.keycode = key
        self.unicode = unicode
        self.modifiers = modifiers
        self.is_quoted = True
    
    @classmethod
    def getScripted(cls, evt):
        """Returns a string that represents the python code to instantiate
        the object.
        
        Used when serializing a L{RecordedKeyboardAction} to a python string
        """
        return "%s(%d, %d, %d)" % (cls.__name__, evt.GetKeyCode(), evt.GetUnicodeKey(), evt.GetModifiers())


class RecordedKeyboardAction(RecordedAction):
    """Subclass of L{RecordedAction} for keyboard events.
    
    """
    def __init__(self, action, evt, multiplier):
        RecordedAction.__init__(self, action, multiplier)
        self.evt = FakeCharEvent(evt)
        
        # Hack to force SelfInsertCommand to process the character, because
        # normally it uses the evt.Skip() to force the EVT_CHAR handler to
        # insert the character.
        self.evt.is_quoted = True
    
    def __str__(self):
        return "%s: %dx%s" % (self.actioncls.__name__, self.multiplier, self.evt.GetKeyCode())
    
    def performAction(self, system_state):
        action = self.actioncls(system_state.frame, mode=system_state.mode)
        dprint(action.__class__.__name__)
        action.actionKeystroke(self.evt, self.multiplier)
    
    def getScripted(self):
        return "%s(frame, mode).actionKeystroke(%s, %d)" % (self.actioncls.__name__, CharEvent.getScripted(self.evt), self.multiplier)


class RecordedMenuAction(RecordedAction):
    """Subclass of L{RecordedAction} for menu events.
    
    """
    def __init__(self, action, index, multiplier):
        RecordedAction.__init__(self, action, multiplier)
        self.index = index
    
    def __str__(self):
        return "%s x%d, index=%s" % (self.actioncls.__name__, self.multiplier, self.index)
    
    def performAction(self, system_state):
        action = self.actioncls(system_state.frame, mode=system_state.mode)
        dprint(action.__class__.__name__)
        action.action(self.index, self.multiplier)
    
    def getScripted(self):
        return "%s(frame, mode).action(%d, %d)" % (self.index, self.multiplier)


class ActionRecorder(AbstractActionRecorder, debugmixin):
    """Creates, maintains and plays back a list of actions recorded from the
    user's interaction with a major mode.
    
    """
    def __init__(self):
        self.recording = []
    
    def __str__(self):
        summary = ''
        count = 0
        for recorded_item in self.recording:
            if hasattr(recorded_item, 'text'):
                summary += recorded_item.text + " "
                if len(summary) > 50:
                    summary = summary[0:50] + "..."
            count += 1
        if len(summary) == 0:
            if count == 1:
                text = _("action")
            else:
                text = _("actions")
            summary = "%d %s" % (count, text)
        return summary
        
    def details(self):
        """Get a list of actions that have been recorded.
        
        Primarily used for debugging, there is no way to use this list to
        play back the list of actions.
        """
        lines = []
        for recorded_item in self.recording:
            lines.append(str(recorded_item))
        return "\n".join(lines)
        
    def recordKeystroke(self, action, evt, multiplier):
        if action.isRecordable():
            record = RecordedKeyboardAction(action, evt, multiplier)
            self.appendRecord(record)
    
    def recordMenu(self, action, index, multiplier):
        if action.isRecordable():
            record = RecordedMenuAction(action, index, multiplier)
            self.appendRecord(record)
    
    def appendRecord(self, record):
        """Utility method to add a recordable action to the current list
        
        This method checks for the coalescability of the record with the
        previous record, and it is merged if possible.
        
        @param record: L{RecordedAction} instance
        """
        dprint("adding %s" % record)
        if self.recording:
            last = self.recording[-1]
            if last.canCoalesceActions(record):
                self.recording.pop()
                record = last.coalesceActions(record)
                dprint("coalesced into %s" % record)
        self.recording.append(record)
    
    def getRecordedActions(self):
        return self.recording
    
    def playback(self, frame, mode, multiplier=1):
        mode.BeginUndoAction()
        state = MacroPlaybackState(frame, mode)
        dprint(state)
        SelectAction.debuglevel = 1
        while multiplier > 0:
            for recorded_action in self.getRecordedActions():
                recorded_action.performAction(state)
            multiplier -= 1
        SelectAction.debuglevel = 0
        mode.EndUndoAction()


class PythonScriptableMacro(debugmixin):
    """A list of serialized SelectAction commands used in playing back macros.
    
    This object contains python code in the form of text strings that
    provide a way to reproduce the effects of a previously recorded macro.
    Additionally, since they are in plain text, they may be carefully edited
    by the user to provide additional functionality that is not possible only
    using the record capability.
    
    The generated python script looks like the following:
    
    SelfInsertCommand(frame, mode).actionKeystroke(CharEvent(97, 97, 0), 1)
    BeginningTextOfLine(frame, mode).actionKeystroke(CharEvent(65, 65, 2), 1)
    SelfInsertCommand(frame, mode).actionKeystroke(CharEvent(98, 98, 0), 1)
    ElectricReturn(frame, mode).actionKeystroke(CharEvent(13, 13, 0), 1)
    
    where the actions are listed, one per line, by their python class name.
    The statements are C{exec}'d in in the global namespace, but have a
    constructed local namespace that includes C{frame} and C{mode} representing
    the current L{BufferFrame} and L{MajorMode} instance, respectively.
    """
    def __init__(self, recorder):
        """Converts the list of recorded actions into python string form.
        
        """
        self.name = str(recorder)
        self.script = self.getScriptFromRecorder(recorder)
    
    def __str__(self):
        return self.name
    
    def getScriptFromRecorder(self, recorder):
        """Converts the list of recorded actions into a python script that can
        be executed by the L(playback) method.
        
        Calls the L{RecordAction.getScripted} method of each recorded action to
        generate the python script version of the action.
        
        @returns: a multi-line string, exec-able using the L{playback} method
        """
        script = ""
        lines = []
        for recorded_action in recorder.getRecordedActions():
            lines.append(recorded_action.getScripted())
        script += "\n".join(lines)
        return script
    
    def playback(self, frame, mode, multiplier=1):
        """Plays back the list of actions.
        
        Uses the current frame and mode as local variables for the python
        scripted version of the action list.
        """
        local = {'mode': mode,
                 'frame': frame,
                 }
        self.addActionsToLocal(local)
        dprint(local)
        dprint(self.script)
        while multiplier > 0:
            exec self.script in globals(), local
            multiplier -= 1
    
    def addActionsToLocal(self, local):
        """Sets up the local environment for the exec call
        
        All the possible actions must be placed in the local environment for
        the call to exec.
        """
        actions = MacroAction.getAllKnownActions()
        for action in actions:
            local[action.__name__] = action
        actions = SelectAction.getAllKnownActions()
        for action in actions:
            local[action.__name__] = action
        names = local.keys()
        names.sort()
        dprint(names)



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
    
    @classmethod
    def isRecordable(cls):
        return False
    
    def action(self, index=-1, multiplier=1):
        if self.frame.root_accel.isRecordingActions():
            recorder = self.frame.root_accel.stopRecordingActions()
            dprint(recorder)
            RecentMacros.appendRecording(recorder)


class ReplayLastMacro(SelectAction):
    """Play back last macro that was recorded"""
    name = "Play Last Macro"
    key_bindings = {'default': "C-3", }
    default_menu = ("Tools/Macros", 110)
    
    def isEnabled(self):
        return RecentMacros.isEnabled()
    
    @classmethod
    def isRecordable(cls):
        return False
    
    def action(self, index=-1, multiplier=1):
        if self.frame.root_accel.isRecordingActions():
            recorder = self.frame.root_accel.stopRecordingActions()
            dprint(recorder)
            RecentMacros.appendRecording(recording)
        macro = RecentMacros.getLastMacro()
        if macro:
            dprint("Playing back %s" % macro)
            wx.CallAfter(macro.playback, self.frame, self.mode, multiplier)
        else:
            dprint("No recorded macro.")
        


class RecentMacros(OnDemandGlobalListAction):
    """Play a macro from the list of recently created macros
    
    Maintains a list of the recent macros and runs the selected macro if chosen
    out of the submenu.
    
    Macros are stored as a list of L{PythonScriptableMacro}s
    """
    name = "Recent Macros"
    default_menu = ("Tools/Macros", -200)
    inline = False
    
    storage = []
    
    @classmethod
    def isEnabled(cls):
        return bool(cls.storage)
    
    @classmethod
    def appendRecording(cls, recorder):
        """Convert the recording from a L{ActionRecorder} into a
        L{PythonScriptableMacro} and add it to the list of recent macros.
        
        """
        macro = PythonScriptableMacro(recorder)
        cls.append(macro)
        
    @classmethod
    def getLastMacro(cls):
        """Return the most recently added macro
        
        @returns L{PythonScriptableMacro} instance, or None if no macro has yet
        been added.
        """
        if cls.storage:
            return cls.storage[-1]
        return None
    
    def action(self, index=-1, multiplier=1):
        macro = self.storage[index]
        assert self.dprint("replaying macro %s" % macro)
        wx.CallAfter(macro.playback, self.frame, self.mode, 1)


class MacroPlugin(IPeppyPlugin):
    """Plugin providing the macro recording capability
    """
    def getActions(self):
        return [
            StartRecordingMacro, StopRecordingMacro, ReplayLastMacro,
            
            RecentMacros,
            ]
