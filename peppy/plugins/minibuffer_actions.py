# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Minibuffer text insertion and manipulation commands
"""

import os, sys

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import MinibufferKeyboardAction
from peppy.debug import *
from peppy.lib.multikey import *



class MinibufferTextCtrlMixin(object):
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return hasattr(ctrl, 'WriteText')
    

class MinibufferSelfInsertCommand(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'default',}
    
    def actionKeystroke(self, evt, multiplier=1):
        if evt.GetModifiers() == wx.MOD_CONTROL:
            uchar = unichr(evt.GetUnicodeKey())
        else:
            uchar = unichr(evt.GetKeyCode())
        if hasattr(evt, 'is_quoted'):
            text = uchar * multiplier
            #dprint("char=%s, unichar=%s, multiplier=%s, text=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), multiplier, text))
            self.ctrl.WriteText(text)
        else:
            if multiplier > 1:
                text = uchar * (multiplier - 1)
                self.ctrl.WriteText(text)
            evt.Skip()


class MinibufferInsertQuotedChar(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    """Quoted insert: insert the next keystroke as a raw character"""
    key_bindings = {'mac': "^Q", 'emacs': "C-q", }

    def actionKeystroke(self, evt, multiplier=1):
        dprint("Repeating next %d quoted characters" % multiplier)
        self.minibuffer.mode.frame.root_accel.setQuotedNext(multiplier)


class MinibufferDelete(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'DELETE',}
    
    def actionKeystroke(self, evt, multiplier=1):
        # Note: can't use EmulateKeyPress because on windows it causes a
        # KeyEvent which interferes with key processing by getting into a loop
        # and sending repeated presses.
        if multiplier > 1:
            start, end = self.ctrl.GetSelection()
            # NOTE: if there exists a selction, we emulate emacs by only
            # deleting the selection and ignore the multiplier.  Otherwise,
            # we remove all but one of the characters requested and let the
            # evt.Skip process the final delete.
            if start == end:
                end = min(end + multiplier - 1, self.ctrl.GetLastPosition())
                self.ctrl.Remove(start, end)
                self.ctrl.SetInsertionPoint(start)
        
        # Need the evt.Skip to process the final delete character, and thus
        # allow the EVT_TEXT_CHANGED event to be processed
        evt.Skip()


class MinibufferBackspace(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'BACK',}
    
    def actionKeystroke(self, evt, multiplier=1):
        if multiplier > 1:
            start, end = self.ctrl.GetSelection()
            # NOTE: if there exists a selction, we emulate emacs by only
            # deleting the selection and ignore the multiplier.  Otherwise,
            # we remove all but one of the characters requested and let the
            # evt.Skip process the final delete.
            if start == end:
                start = max(start - multiplier + 1, 0)
                self.ctrl.Remove(start, end)
                self.ctrl.SetInsertionPoint(start)
        
        # Need the evt.Skip to process the final backspace character, and thus
        # allow the EVT_TEXT_CHANGED event to be processed
        evt.Skip()


class MinibufferPreviousCharacter(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'LEFT', 'emacs': ['LEFT', 'C-b'],}
    
    def actionKeystroke(self, evt, multiplier=1):
        pos = self.ctrl.GetInsertionPoint()
        pos -= multiplier
        if pos < 0:
            pos = 0
        self.ctrl.SetInsertionPoint(pos)


class MinibufferNextCharacter(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'RIGHT', 'emacs': ['RIGHT', 'C-f'],}
    
    def actionKeystroke(self, evt, multiplier=1):
        pos = self.ctrl.GetInsertionPoint()
        pos += multiplier
        if pos > self.ctrl.GetLastPosition():
            pos = self.ctrl.GetLastPosition()
        self.ctrl.SetInsertionPoint(pos)


class MinibufferBeginningOfLine(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'HOME', 'emacs': ['HOME', 'C-a'],}
    
    def actionKeystroke(self, evt, multiplier=1):
        self.ctrl.SetInsertionPoint(0)


class MinibufferEndOfLine(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'default': 'END', 'emacs': ['END', 'C-e'],}
    
    def actionKeystroke(self, evt, multiplier=1):
        self.ctrl.SetInsertionPoint(self.ctrl.GetLastPosition())


class MinibufferSelectAll(MinibufferTextCtrlMixin, MinibufferKeyboardAction):
    key_bindings = {'win': "C-a", 'mac': "C-a", 'emacs': "C-x h"}
    
    def actionKeystroke(self, evt, multiplier=1):
        self.ctrl.SetSelection(0, self.ctrl.GetLastPosition())




class MinibufferEnterCommand(MinibufferKeyboardAction):
    key_bindings = {'default': 'RET',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return hasattr(ctrl, 'WriteText') and hasattr(minibuffer, 'getResult')
    
    def actionKeystroke(self, evt, multiplier=-1):
        minibuffer = self.minibuffer
        text, error = minibuffer.getResult()

        if minibuffer.next_focus:
            minibuffer.next_focus.focus()
        elif minibuffer.finish_callback:
            minibuffer.finish_callback()
        else:
            # Remove the minibuffer and perform the action in CallAfters so
            # the tab focus doesn't get confused.  If you try to perform these
            # actions directly, the focus will return to the original tab if
            # the action causes a new tab to be created.  Moving everything
            # to CallAfters prevents this.  Also, MSW can crash if performing
            # these directly, so it's worth the extra milliseconds to use
            # CallAfter
            wx.CallAfter(minibuffer.removeFromParent)
            if text is not None:
                wx.CallAfter(minibuffer.performAction, text)





class MinibufferTabCompleteCommand(MinibufferKeyboardAction):
    key_bindings = {'default': 'TAB',}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return hasattr(ctrl, 'WriteText') and hasattr(minibuffer, 'processCompletion')
    
    def actionKeystroke(self, evt, multiplier=-1):
        self.minibuffer.processCompletion()




class MinibufferTabCompleteSelfProcess(MinibufferKeyboardAction):
    """Allow the TextCtrlAutoComplete to use its self-processing ability for
    certain keys.
    
    The TextCtrlAutoComplete has its own key processing ability, and rather than
    create actions for every one of those events in its key dowv processing,
    they are simply passed through here.
    
    The minibuffer needs the allow_tab_complete_key_processing class attribute
    to be set in order for this action to be activated.
    """
    key_bindings = {'default': ['TAB', 'UP', 'DOWN', 'HOME', 'END', 'PAGEDOWN', 'PAGEUP']}
    
    @classmethod
    def worksWithMinibuffer(self, minibuffer, ctrl):
        return hasattr(ctrl, 'WriteText') and hasattr(minibuffer, 'allow_tab_complete_key_processing')
    
    def actionKeystroke(self, evt, multiplier=-1):
        self.ctrl.onKeyDown(evt)





class MinibufferActionPlugin(IPeppyPlugin):
    """Collection of minibuffer actions

    The minibuffer is designed to work with special actions that operate on the
    TextCtrl rather than the StyledTextCtrl.
    """
    
    def activateHook(self):
        Publisher().subscribe(self.pluginsChanged, 'peppy.plugins.changed')
        self.pluginsChanged()
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.pluginsChanged)

    def pluginsChanged(self, message=None):
        action_classes = getAllSubclassesOf(MinibufferKeyboardAction)
        MinibufferKeyboardAction.all_actions = action_classes
