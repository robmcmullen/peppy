# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Keyboard loader and configuration generator.
"""

import os, sys

import wx
from wx.lib.pubsub import Publisher

from peppy.list_mode import *
from peppy.stcinterface import *
from peppy.buffers import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.actions.minibuffer import MinibufferKeyboardAction
from peppy.debug import *
from peppy.configprefs import *
from peppy.lib.userparams import *
from peppy.lib.multikey import *
from peppy.majormodematcher import MajorModeMatcherDriver
from peppy.menu import UserActionClassList
from peppy.major import EmptyMode


class ShowModeKeys(SelectAction):
    """Display a list of key bindings.
    
    Simple action to show a list of keybindings of the current mode.
    """
    name = "&Show Key Bindings"
    alias = "describe-keys"
    default_menu = ("&Help", 210)
    key_bindings = {'emacs': "C-h b", }

    def action(self, index=-1, multiplier=1):
        bindings = self.frame.root_accel.getKeyBindings()
        text = ["List of key bindings:"]
        #dprint(str(bindings))
        sorted = [(a.__class__.__name__, key, a) for key, a in bindings.iteritems()]
        sorted.sort()
        for name, key, action in sorted:
            text.append("%s\t%s\t\t%s" % (key, name, action.tooltip))
        
        unbound = self.frame.root_accel.getUnboundActions()
        text.append("\n")
        text.append("Actions without key bindings:")
        sorted = [(a.__class__.__name__, a) for a in unbound]
        sorted.sort()
        for name, action in sorted:
            text.append("%s\t\t%s" % (name, action.tooltip))
        Publisher().sendMessage('peppy.log.info', '\n'.join(text))


class DebugKeypress(ToggleAction):
    """Print debugging information to the console for each keypress"""
    name = "Debug Keypress"
    alias = "debug-keypress"
    default_menu = (("Tools/Debug", -1000), 100)
    
    def isChecked(self):
        return AcceleratorList.debug
    
    def action(self, index=-1, multiplier=1):
        AcceleratorList.debug = not AcceleratorList.debug


class EditKeybindings(SelectAction):
    name = "Key Bindings..."
    tooltip = "Display and edit key bindings."
    icon = 'icons/keyboard.png'
    default_toolbar = False
    default_menu = ("Edit", 1000.05)

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:keybindings")


class KeybindingActionMixin(ListModeActionMixin):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return mode.stc_class == KeybindingSTC
    
    def isEnabled(self):
        return self.mode.list.GetSelectedItemCount() > 0

class TriggeredRebindingActionMixin(KeybindingActionMixin):
    def action(self, index=-1, multiplier=1):
        KeystrokeRecording(self.mode, self.keyboard)

class RebindKeyAction(TriggeredRebindingActionMixin, SelectAction):
    """Rebind the selected action to a new keystroke"""
    alias = "rebind-action"
    name = "New Multi-Key Binding"
    default_menu = ("Actions", -200)
    key_bindings = {'default': "RET", }

class CountedRebindingActionMixin(KeybindingActionMixin):
    def action(self, index=-1, multiplier=1):
        KeystrokeRecording(self.mode, count=self.keystroke_count)

class RebindSingleKeyAction(CountedRebindingActionMixin, SelectAction):
    """Rebind the selected action to a new single keystroke"""
    alias = "rebind-action-single-key"
    name = "New Single Key Accelerator"
    default_menu = ("Actions", 210)
    key_bindings = {'default': ["1", "SPACE"], }
    keystroke_count = 1

class RebindTwoKeyAction(CountedRebindingActionMixin, SelectAction):
    """Rebind the selected key to a new two keystroke combination"""
    alias = "rebind-action-two-key"
    name = "New Two Key Accelerator"
    default_menu = ("Actions", 220)
    key_bindings = {'default': "2", }
    keystroke_count = 2

class RebindThreeKeyAction(CountedRebindingActionMixin, SelectAction):
    """Rebind the selected key to a new three keystroke combination"""
    alias = "rebind-action-three-key"
    name = "New Three Key Accelerator"
    default_menu = ("Actions", 230)
    key_bindings = {'default': "3", }
    keystroke_count = 3


class KeystrokeRecording(object):
    def __init__(self, mode, trigger=None, count=-1):
        self.mode = mode
        if trigger:
            keystrokes = KeyAccelerator.split(trigger)
            self.trigger = keystrokes[0]
            self.count = -1
        elif count > 0:
            self.trigger = None
            self.count = count
        self.recording = []
        self.action = mode.getFirstSelectedAction()
        self.mode.frame.root_accel.setQuotedRaw(self.addKeystroke)
        self.platform = KeyboardConf.keyboard.platform
        if self.count > 1 or self.platform == 'emacs':
            self.emacs = True
        else:
            self.emacs = False
        
        self.status_text = "Enter new key binding for %s:" % self.action.__name__
        self.mode.setStatusText(self.status_text)
    
    def getAccelerator(self, keystroke):
        if self.emacs:
            acc = keystroke.getEmacsAccelerator()
        else:
            acc = keystroke.getMenuAccelerator()
        return acc
        
    def addKeystroke(self, keystroke):
        dprint("keystroke = %s" % keystroke)
        if keystroke == self.trigger:
            self.finishRecording()
        else:
            accelerator = self.getAccelerator(keystroke)
            dprint("keystroke = %s" % accelerator)
            self.recording.append(accelerator)
            if len(self.recording) == self.count:
                self.finishRecording()
            else:
                self.status_text += " " + accelerator
                self.mode.setStatusText(self.status_text)
                wx.CallAfter(self.mode.frame.root_accel.setQuotedRaw, self.addKeystroke)
    
    def finishRecording(self):
        dprint("Recording %s" % (self.recording))
        acc = " ".join(self.recording)
        self.status_text = "New key binding for %s: %s" % (self.action.__name__, acc)
        self.mode.setStatusText(self.status_text)
        dprint(self.status_text)
        self.mode.buffer.stc.setRemappedAccelerator(self.action, acc)
        wx.CallAfter(self.mode.resetList)


class UndoableKeybindingChange(UndoableItem):
    def __init__(self, action, new_acc, old_acc):
        self.action = action
        self.new_accelerator = new_acc
        self.old_remapped = old_acc
    
    def undo(self, stc):
        if self.old_remapped is None:
            del stc.remapped_actions[self.action]
        else:
            stc.remapped_actions[self.action] = self.old_remapped
    
    def redo(self, stc):
        stc.remapped_actions[self.action] = self.new_accelerator


class KeybindingSTC(UndoMixin, NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    def __init__(self, parent=None, copy=None):
        NonResidentSTC.__init__(self, parent, copy)
        self.remapped_actions = {}
        self.change_callback = None
    
    def getShortDisplayName(self, url):
        return "Key Bindings"

    def getRemappedAccelerator(self, action):
        return self.remapped_actions[action]
    
    def setRemappedAccelerator(self, action, accelerator):
        undo_obj = UndoableKeybindingChange(action, accelerator, self.remapped_actions.get(action, None))
        self.undoMixinSaveUndoableItem(undo_obj)
        self.remapped_actions[action] = accelerator
        self.fireChangeEvent()
    
    def addDocumentChangeEvent(self, callback):
        self.change_callback = callback
        
    def fireChangeEvent(self):
        callback = self.change_callback
        if callback:
            callback(None)
    
    def revertEncoding(self, buffer, url=None, message=None, encoding=None, allow_undo=False):
        self.remapped_actions = {}
        # For the moment, reset the undo buffer so that this action isn't
        # undoable regardless of what allow_undo says.
        self.EmptyUndoBuffer()

    def openFileForWriting(self, url):
        if url.scheme == 'about':
            return None
        raise NotImplementedError
    
    def writeTo(self, fh, url):
        if fh == None:
            for action, acc in self.remapped_actions.iteritems():
                dprint("Setting action %s to keybinding %s" % (action.__name__, acc))
                setattr(KeyboardConf.classprefs, action.__name__, acc)
            self.remapped_actions = {}
        else:
            raise NotImplementedError
    
    def closeFileAfterWriting(self, fh):
        if fh is not None:
            fh.close()
        else:
            Publisher().sendMessage('keybindings.changed')
            wx.CallAfter(wx.GetApp().updateAllFrames)
                        
class KeybindingMode(ListMode):
    """Display an editable list of keybindings
    """
    keyword = "Keybindings"
    icon = 'icons/keyboard.png'
    allow_threaded_loading = False
    
    stc_class = KeybindingSTC

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:buffers
        if url.scheme == 'about' and url.path == 'keybindings':
            return True
        return False
    
    # Need to add CanUndo, Undo, CanRedo, Redo to the major mode level so that
    # the actions can determine that Undo and Redo should be added to the user
    # interface.  worksWithMajorMode doesn't look at the STC to determine what
    # action to add; only the major mode class
    def CanUndo(self):
        return self.buffer.stc.CanUndo()

    def Undo(self):
        self.buffer.stc.Undo()
        self.buffer.stc.fireChangeEvent()
        self.resetList()

    def CanRedo(self):
        return self.buffer.stc.CanRedo()

    def Redo(self):
        self.buffer.stc.Redo()
        self.buffer.stc.fireChangeEvent()
        self.resetList()

    def revertPostHook(self):
        self.resetList()

    def createInfoHeader(self, sizer):
        self.all_actions = True
        self.current_mode = None
        self.show_global_keybindings = True
        
        panel = wx.Panel(self)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.choice = wx.Choice(panel, -1, choices = ['All Actions', 'Actions with Keybindings'])
        self.Bind(wx.EVT_CHOICE, self.OnChoice, self.choice)
        hbox.Add(self.choice, 0, wx.EXPAND)
        
        text = wx.StaticText(panel, -1, _(" of "))
        hbox.Add(text, 0, wx.EXPAND)
        
        self.mode_list, names = self.getActiveModesAndNames()
        self.mode_choice = wx.Choice(panel, -1, choices = names)
        self.Bind(wx.EVT_CHOICE, self.OnModeChoice, self.mode_choice)
        hbox.Add(self.mode_choice, 0, wx.EXPAND)
        
        global_check = wx.CheckBox(panel, -1, "Show Global Actions")
        global_check.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.OnGlobal, global_check)
        hbox.Add(global_check, 0, wx.EXPAND)
        
        panel.SetSizer(hbox)

        sizer.Add(panel, 0, wx.EXPAND)
        
        dprint(self.buffer)
    
    def getActiveModesAndNames(self):
        modes = []
        names = []
        for mode in MajorModeMatcherDriver.iterActiveModes():
            modes.append(mode)
            names.append(mode.keyword)
        order = [(n, m) for n, m in zip(names, modes)]
        order.sort()
        
        # NOTE: interestingly, zip is its own unzip!
        n, m = zip(*order)
        names = ["All Major Modes"]
        names.extend(n)
        modes = [None]
        modes.extend(m)
        dprint(modes)
        dprint(names)
        return modes, names
    
    def OnChoice(self, evt):
        if evt.GetSelection() == 0:
            self.all_actions = True
        else:
            self.all_actions = False
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def OnModeChoice(self, evt):
        index = evt.GetSelection()
        dprint("Using major mode %s" % self.mode_list[index])
        self.current_mode = self.mode_list[index]
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def OnGlobal(self, evt):
        self.show_global_keybindings = evt.IsChecked()
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def createColumns(self, list):
        list.InsertSizedColumn(0, "Name", min=100, greedy=True)
        list.InsertSizedColumn(1, "Description", min=100, greedy=False)
        list.InsertSizedColumn(2, "Key Binding", min=30, greedy=True)

    def getListItems(self):
        actions = self.getCurrentActions()
        if not self.all_actions:
            actions = [a for a in actions if a.keyboard is not None or a in self.buffer.stc.remapped_actions]
        
        # remove default
        actions = [a for a in actions if a.keyboard != "default"]
        
        def sortActions(a, b):
            aname = a.getName().replace("&", "")
            bname = b.getName().replace("&", "")
            return cmp(aname, bname)
        
        return sorted(actions, cmp=sortActions)
    
    def getCurrentActions(self):
        mode = self.current_mode
        if mode is None:
            actions = KeyboardConf.getAllLoadedActions()
        else:
            actions = UserActionClassList.getActiveActions(mode)
        
        if not self.show_global_keybindings:
            filter_out = UserActionClassList.getActiveActions(EmptyMode)
            actions = [a for a in actions if a not in filter_out]
        return actions
    
    def getItemRawValues(self, index, action):
        class ActionSortWrapper(object):
            def __init__(self, action):
                self.action = action
                self.name = action.getName().replace("&", "")
            
            def __str__(self):
                return self.name
            
            def __cmp__(self, other):
                return cmp(self.name, other.name)
        
        description = action.getDefaultTooltip()
        
        try:
            keyboard = self.buffer.stc.getRemappedAccelerator(action)
        except KeyError:
            if action.keyboard is None:
                keyboard = ""
            else:
                keyboard = str(action.keyboard)
        
        return (ActionSortWrapper(action), description, keyboard)
    
    def getFirstSelectedAction(self):
        """Get the action object of the first selected item in the list."""
        index = self.list.GetFirstSelected()
        if index == -1:
            return None
        actionwrapper = self.list.itemDataMap[index][0]
        return actionwrapper.action

    def getPopupActions(self, evt, x, y):
        return [
            RebindKeyAction,
            RebindSingleKeyAction,
            RebindTwoKeyAction,
            RebindThreeKeyAction,
            ]


class Keyboard(ClassPrefs):
    """Global keyboard configuration.
    
    """
    preferences_tab = "General"
    icon = "icons/keyboard.png"
    platform = 'win'
    force_emacs = False
    
    valid_platforms = ['system default', 'win', 'emacs', 'mac']
    default_classprefs = (
        ChoiceParam('key_bindings', valid_platforms, 'system default', 'Platform type from which to emulate the default keybindings.'),
        BoolParam('force_emacs_menu_accelerators', True, 'Display all key bindings in emacs form when multi-key bindings are present, otherwise a mixture of emacs and native key bindings are displayed in menus.'),
        )

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
    keyboard = Keyboard()
    default_classprefs = (
        # backward compatibility: now the key binding is set in Keyboard
        DeprecatedParam('key_bindings', 'system default', help="Deprecated.  Set the key bindings using the Keyboard option in the General tab of the Preferences dialog."),
        )
    
    ignore_list = ['MinibufferAction', 'MinibufferRepeatAction']
    
    def activateHook(self):
        Publisher().subscribe(self.settingsChanged, 'peppy.preferences.changed')
        Publisher().subscribe(self.loadBindings, 'keybindings.changed')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.settingsChanged)
        Publisher().unsubscribe(self.loadBindings)

    def addCommandLineOptions(self, parser):
        parser.add_option("--key-bindings", action="store",
                          dest="key_bindings", default='')
        parser.add_option("--show-key-bindings", action="store_true",
                          dest="show_key_bindings")

    def processCommandLineOptions(self, options):
        #dprint(options.key_bindings)
        if options.key_bindings:
            self.keyboard.platform = options.key_bindings
        else:
            self.keyboard.platform = self.classprefs.key_bindings
            if self.keyboard.classprefs.key_bindings != 'system default':
                self.keyboard.platform = self.keyboard.classprefs.key_bindings
        if self.keyboard.platform == 'system default':
            if wx.Platform == '__WXMAC__':
                self.keyboard.platform = 'mac'
            else:
                self.keyboard.platform = 'win'
        self.keyboard.force_emacs = self.keyboard.classprefs.force_emacs_menu_accelerators
        self.loadBindings()
        if options.show_key_bindings:
            self.configDefault()
    
    def requestedShutdown(self):
        # FIXME: configuration file should be saved here
        pass
    
    def settingsChanged(self, message=None):
        if self.keyboard.classprefs.key_bindings != self.keyboard.platform or self.keyboard.classprefs.force_emacs_menu_accelerators != self.keyboard.force_emacs:
            self.keyboard.platform = self.keyboard.classprefs.key_bindings
            self.keyboard.force_emacs = self.keyboard.classprefs.force_emacs_menu_accelerators
            self.loadBindings()

    def getKey(self, action):
        keyboard = None
        bindings = action.key_bindings
        platform = self.keyboard.platform
        if wx.Platform == '__WXMAC__' and platform == 'emacs':
            # Using emacs keybindings on the mac causes a blend of both mac and
            # emacs bindings.
            platform = 'mac'
            add_mac_emacs = True
        else:
            add_mac_emacs = False
        if isinstance(bindings, dict):
            if platform in bindings:
                keyboard = bindings[platform]
            elif 'default' in bindings:
                keyboard = bindings['default']
            
            if add_mac_emacs:
                # Merge the emacs bindings in with the mac defaults.
                emacs = bindings.get('emacs', [])
                if emacs:
                    if not isinstance(emacs, list):
                        emacs = [emacs]
                    if keyboard is None:
                        keyboard = []
                    elif not isinstance(keyboard, list):
                        keyboard = [keyboard]
                    emacs = self.convertEmacsToMac(emacs)
                    keyboard.extend(emacs)
        return keyboard
    
    def convertEmacsToMac(self, bindings):
        """Convert 'C-' representations to the control key for use on Mac.
        
        When trying to incorporate emacs keybindings into Mac keybindings, the
        'C-' has different meanings.  This changes the 'C-' to mean control,
        represented by '^' on the Mac.
        """
        converted = []
        for binding in bindings:
            if binding is not None:
                binding = binding.replace("C-", "^")
                converted.append(binding)
        self.dprint("converted %s to %s" % (bindings, converted))
        return converted
    
    @classmethod
    def getAllLoadedActions(cls, subclass=SelectAction):
        actions = getAllSubclassesOf(subclass)
        actions = [a for a in actions if a.action is not None and a.__name__ not in cls.ignore_list]
        return actions
    
    def loadBindings(self, message=None):
        actions = getAllSubclassesOf(SelectAction)
        self.setKeybindingsOfActions(actions)
        self.setAcceleratorTextOfActions(actions)
        
        # minibuffer keystrokes are never put in the menu bar so we don't need
        # to deal with accelerator text
        actions = getAllSubclassesOf(MinibufferKeyboardAction)
        self.setKeybindingsOfActions(actions)
    
    def setKeybindingsOfActions(self, actions):
        #dprint(actions)
        for action in actions:
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
                        action.user_keyboard = True
                    found = True
            if not found:
                action.keyboard = self.getKey(action)
                action.user_keyboard = None
            #dprint("%s: %s" % (action.__name__, action.keyboard))
    
    def setAcceleratorTextOfActions(self, actions):
        # Note that it's never allowed to have only emacs style accelerators on
        # Mac because the mac menu system enforces stock ids like preferences
        # and quit to include the default keystroke
        if wx.Platform != '__WXMAC__' and self.keyboard.force_emacs:
            wants_emacs = True
        else:
            wants_emacs = False
        
        found_emacs = False
        for action in actions:
            # Determine up the accelerator text here, up front, rather
            # than computing it every time the menu is displayed.
            numkeystrokes = action.setAcceleratorText()
            #dprint("%s: %d %s" % (action.__name__, numkeystrokes, action._accelerator_text))
            if wants_emacs and numkeystrokes>1:
                # If we find an emacs binding and we want to display in emacs
                # style, there's no need to search any more keybindings so we
                # break here and start again below.
                found_emacs = True
                break
        
        if wants_emacs and found_emacs:
            # Recalculate all the accelerators if we've found multi-key
            # bindings and we want to display only emacs style.
            for action in actions:
                action.setAcceleratorText(force_emacs=True)
                #dprint("%s: %d %s" % (action.__name__, numkeystrokes, action._accelerator_text))

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

    def getMajorModes(self):
        yield KeybindingMode

    def getActions(self):
        yield ShowModeKeys
        yield DebugKeypress
        yield EditKeybindings
        yield RebindKeyAction
        yield RebindSingleKeyAction
        yield RebindTwoKeyAction
        yield RebindThreeKeyAction
