"""Multiple keystrokes for command processing.

Using the wx.AcceleratorTable to create multiple keystroke events.

Precedence rules:

1) If an accelerator appears in a menu, that keystroke will always be available

corollary) There is no way to prevent the id associated with that menu
accelerator from overriding an accelerator table

2) If the same accelerator appears in a menu and the accelerator table, the id
associated with a menu accelerator will be the value returned to the EVT_MENU
handler.

These rules imply that the id associated with that accelerator will take
precedence over any remapping in an accelerator table.  Short of removing the
accelerator from the menu, there is no way to prevent this.


Specifying Keystrokes:

Keystrokes are specified using text strings like "Ctrl-X", "Shift-M", "Alt-G",
"Meta-Q", and on MAC keystrokes like "Command-O", and "Option-Z".  In addition
to standard modifier keys, Emacs style modifiers are available.  They are
specified as in "C-x" to mean Control-X.

Emacs-style Prefixes:
 C-   Control on MSW/GTK; Command on Mac
 ^-   Control on Mac, aliased to C- on MSW/GTK
 S-   Shift
 M-   Alt/Option on MAC; Alt on MSW/GTK
 A-   aliased to M- on all platforms
"""

import os, sys
import wx, wx.stc

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt


# Make sure internationalization support is available, or fake it if not
try:
    _("")
except NameError:
    import __builtin__
    __builtin__._ = unicode


class DuplicateKeyError(RuntimeError):
    pass


# The list of all the wx keynames (without the WXK_ prefix) is needed by both
# KeyMap and KeyProcessor objects
wxkeynames = [i[4:] for i in dir(wx) if i.startswith('WXK_')]

wxkeyname_to_keycode = {}
wxkeycode_to_keyname = {}
for keyname in wxkeynames:
    keycode = getattr(wx, "WXK_%s" % keyname)
    wxkeyname_to_keycode[keyname] = keycode
    wxkeycode_to_keyname[keycode] = keyname

# On some platforms, modifiers generate events by themselves, so we need to
# know what they are to ignore them when checking for real keys
ignore_modifiers = {}
for keyname in ['SHIFT', 'CONTROL', 'ALT', 'COMMAND', 'CAPITAL', 'NUMLOCK', 'SCROLL']:
    ignore_modifiers[wxkeyname_to_keycode[keyname]] = True

# Aliases for WXK_ names
keyaliases={'RET':'RETURN',
            'SPC':'SPACE',
            'ESC':'ESCAPE',
            }

# Reverse mapping from keycode to emacs name
wxkeycode_to_emacs_alias = {}
for alias, keyname in keyaliases.iteritems():
    wxkeyname_to_keycode[alias] = wxkeyname_to_keycode[keyname]
    wxkeycode_to_emacs_alias[wxkeyname_to_keycode[keyname]] = alias

if wx.Platform == '__WXMAC__':
    # Note that WXMAC needs Command to appear as Ctrl- in the accelerator
    # text.  It converts Ctrl into the command symbol.  Note that there is no
    # mapping for the C- prefix because wx doesn't have the ability to put a
    # Control character in a menu.
    usable_modifiers = [wx.ACCEL_CTRL, wx.ACCEL_ALT, wx.ACCEL_SHIFT, wx.ACCEL_CMD]
    emacs_modifiers = {
        wx.ACCEL_CMD: 'Cmd-',
        wx.ACCEL_CTRL: '^',
        wx.ACCEL_SHIFT: 'S-',
        wx.ACCEL_ALT: 'Opt-',
        }
    menu_modifiers = {
        wx.ACCEL_CMD: 'Ctrl-', # Ctrl appears in the menu item as the command cloverleaf
        wx.ACCEL_CTRL: '^',
        wx.ACCEL_SHIFT: 'Shift-', # Shift appears in the menu item as an up arrow
        wx.ACCEL_ALT: 'Alt-', # Alt appears in the menu item as the option character
        }
else:
    usable_modifiers = [wx.ACCEL_CTRL, wx.ACCEL_ALT, wx.ACCEL_SHIFT]
    emacs_modifiers = {
        wx.ACCEL_CTRL: 'C-',
        wx.ACCEL_SHIFT: 'S-',
        wx.ACCEL_ALT: 'M-',
        }
    menu_modifiers = {
        wx.ACCEL_CTRL: 'Ctrl-',
        wx.ACCEL_SHIFT: 'Shift-',
        wx.ACCEL_ALT: 'Alt-',
        }
    

modifier_alias = {
    'C-': wx.ACCEL_CMD,
    'Cmd-': wx.ACCEL_CMD,
    'Cmd+': wx.ACCEL_CMD,
    'Command-': wx.ACCEL_CMD,
    'Command+' :wx.ACCEL_CMD,
    'Apple-': wx.ACCEL_CMD,
    'Apple+' :wx.ACCEL_CMD,
    '^': wx.ACCEL_CTRL,
    '^-': wx.ACCEL_CTRL,
    'Ctrl-': wx.ACCEL_CTRL,
    'Ctrl+': wx.ACCEL_CTRL,
    'S-': wx.ACCEL_SHIFT,
    'Shift-': wx.ACCEL_SHIFT,
    'Shift+': wx.ACCEL_SHIFT,
    'M-': wx.ACCEL_ALT,
    'Alt-': wx.ACCEL_ALT,
    'Alt+': wx.ACCEL_ALT,
    'Opt-': wx.ACCEL_ALT,
    'Opt+': wx.ACCEL_ALT,
    'Option-': wx.ACCEL_ALT,
    'Option+': wx.ACCEL_ALT,
    'Meta-': wx.ACCEL_ALT,
    'Meta+': wx.ACCEL_ALT,
    }



class Keystroke(object):
    cache = {}
    
    def __init__(self, flags, key):
        self.flags = flags
        self.id = wx.NewId()
        self.keycode = self.getKeyCode(key)
        self.key = self.getKeyName(self.keycode)
        self.modifier_only = self.keycode in ignore_modifiers
    
    def __str__(self):
        return "id=%s flag=%s key=%s keycode=%s" % (self.id, self.flags, self.key, self.keycode)
    
    @classmethod
    def find(cls, flags, keycode):
        if not isinstance(keycode, int):
            keycode = cls.getKeyCode(keycode)
        try:
            keystroke = cls.cache[(flags, keycode)]
        except KeyError:
            keystroke = Keystroke(flags, keycode)
            cls.cache[(keystroke.flags, keystroke.keycode)] = keystroke
        return keystroke
    
    @classmethod
    def getKeyCode(self, key):
        try:
            keycode = wxkeyname_to_keycode[key]
        except KeyError:
            if not isinstance(key, int):
                keycode = ord(key)
            else:
                keycode = key
        return keycode
    
    @classmethod
    def getKeyName(self, keycode):
        try:
            keyname = wxkeycode_to_keyname[keycode]
        except KeyError:
            if keycode >= ord('A') and keycode <= ord('Z'):
                keycode += 32
            keyname = unichr(keycode)
        return keyname
    
    @classmethod
    def getTextFromKeyCode(cls, keycode):
        # If the keycode is ASCII, normalize it to a capital letter
        if keycode >= ord('A') and keycode <= ord('Z'):
            keycode += 32
        return unichr(keycode)
    
    def getMenuAccelerator(self):
        if self.key.startswith("NUMPAD"):
            return ""
        mod = self.getMenuModifiers()
        return mod + self.key
    
    def isPlainAsciiAccelerator(self):
        return self.flags == 0 and (self.keycode >= 32 and self.keycode < 127)
    
    def isModifierOnly(self):
        return self.modifier_only

    def getMenuModifiers(self):
        mods = ""
        for bit in usable_modifiers:
            if self.flags & bit:
                mods += menu_modifiers[bit]
        return mods
    
    def getEmacsAccelerator(self):
        mod = self.getEmacsModifiers()
        try:
            try:
                name = wxkeycode_to_emacs_alias[self.keycode]
            except KeyError:
                name = self.key
            return mod + name
        except TypeError:
            dprint("flag=%s key=%s keycode=%s" % (self.flags, self.key, self.keycode))
            raise

    def getEmacsModifiers(self):
        mods = ""
        for bit in usable_modifiers:
            if self.flags & bit:
                mods += emacs_modifiers[bit]
        return mods
    
    def getAcceleratorTableEntry(self):
        return (self.flags, self.keycode, self.id)



class KeyAccelerator(object):
    debug = False
    
    # Cache that maps accelerator string to the sequence of keystrokes
    accelerator_cache = {}
    
    # Cache that maps normalized keystrokes to Keystroke instances
    normalized_keystroke_cache = {}

    @classmethod
    def split(cls, acc):
        """Split the accelerator string (e.g. "C-X C-S") into
        individual keystrokes, expanding abbreviations and
        standardizing the order of modifier keys.
        """
        try:
            return cls.accelerator_cache[acc]
        except KeyError:
            if cls.debug: dprint("accelerator %s not found; creating keystrokes" % acc)
            normalized_keys = cls.normalizeAccelerators(acc)
            keystrokes = cls.getKeystrokes(normalized_keys)
            cls.accelerator_cache[acc] = keystrokes
            return keystrokes
    
    @classmethod
    def normalizeAccelerators(cls, acc):
        normalized = []
        keystrokes = acc.split()
        if cls.debug: dprint("*** parts=%s" % str(keystrokes))
        for keystroke in keystrokes:
            flags = 0
            last = len(keystroke)
            start_token = 0
            end_token = 0
            while end_token < last:
                c = keystroke[end_token]
                end_token += 1
                if c == "-" or c == "+":
                    # everything before this should be a modifier, unless it is
                    # representing the actual character - or +.
                    if start_token + 1 == end_token:
                        # If there is no modifier, it must be the character
                        key = c
                        break
                    else:
                        modifier = keystroke[start_token:end_token]
                        flags |= cls.getFlagFromModifier(modifier)
                    start_token = end_token
                elif c == "^":
                    if end_token == last:
                        # If it's the last thing, it must be the character
                        key = c
                        break
                    elif start_token + 1 == end_token:
                        # if this there is no modifier before it, it must mean
                        # the control modifier
                        flags |= wx.ACCEL_CTRL
                    start_token = end_token
            
            if start_token < end_token:
                key = keystroke[start_token:end_token]
            keyname = cls.getNameOfKey(key)
            if cls.debug: dprint("*** keystroke=%s key=%s modifiers=%s" % (keystroke, key, flags))
            normalized.append((flags, keyname))
        
        return normalized
    
    @classmethod
    def getFlagFromModifier(cls, modifier):
        try:
            return modifier_alias[modifier]
        except:
            # Strengthen this by checking for the user having entered the
            # modifier in the incorrect case
            try:
                return modifier_alias[modifier.title()]
            except:
                return 0
    
    @classmethod
    def getNameOfKey(cls, text):
        text = text.upper()
        if text in wxkeyname_to_keycode:
            return text
        if text in keyaliases:
            return keyaliases[text]
        return text
    
    @classmethod
    def getKeystrokes(cls, normalized):
        keystrokes = []
        for key in normalized:
            keystrokes.append(cls.getKeystroke(key))
        return tuple(keystrokes)
    
    @classmethod
    def getKeystroke(cls, key):
        try:
            keystroke = cls.normalized_keystroke_cache[key]
            if cls.debug: dprint("Found cached keystroke %s" % keystroke.getEmacsAccelerator())
        except KeyError:
            keystroke = Keystroke.find(key[0], key[1])
            if cls.debug: dprint("Created and cached keystroke %s" % keystroke.getEmacsAccelerator())
            
            # Save references to both the flag and string and flags and keycode
            # versions.
            cls.normalized_keystroke_cache[key] = keystroke
        return keystroke

    @classmethod
    def getEmacsAccelerator(cls, keystrokes):
        keys = []
        for keystroke in keystrokes:
            keys.append(keystroke.getEmacsAccelerator())
        return " ".join(keys)

    @classmethod
    def getAcceleratorText(cls, key_sequence, force_emacs=False):
        keystrokes = cls.split(key_sequence)
        if len(keystrokes) == 1 and not force_emacs and not keystrokes[0].isPlainAsciiAccelerator():
            # if it has a stock id, always force it to use the our
            # accelerator because wxWidgets will put one there anyway and
            # we need to overwrite it with our definition
            acc = keystrokes[0].getMenuAccelerator()
            if acc:
                text = u"\t%s" % acc
            else:
                text = ""
        else:
            acc = cls.getEmacsAccelerator(keystrokes)
            text = u"    %s" % acc
        return text



class KeystrokeRecorder(object):
    """Keystroke recorder used to create new keybindings.
    
    This class triggers L{AcceleratorManager.setQuotedRaw} to start capturing
    raw keystrokes.  At the completion of the key sequence, it calls
    L{KeybindingSTC.setRemappedAccelerator} to update the key sequence for the
    specified action.
    """
    def __init__(self, accel_mgr, trigger=None, count=-1, append=False, platform="win", action_name="action"):
        """Constructor that starts the quoted keystroke capturing
        
        @param accel_mgr: AcceleratorManager object
        
        @keyword trigger: (optional) trigger keystroke string that will be used
        to end a variable length key sequence
        
        @keyword count: (optional) exact number of keystrokes to capture
        
        @keyword append: True will append the key sequence to the
        action's list of key bindings, False (the default) will replace it.
        
        @keyword platform: Platform name used to set the style of the displayed
        keystrokes
        
        @keyword action_name: Name of the action to be rebound
        """
        if trigger:
            keystrokes = KeyAccelerator.split(trigger)
            self.trigger = keystrokes[0]
            self.count = -1
        elif count > 0:
            self.trigger = None
            self.count = count
        self.recording = []
        self.accel_mgr = accel_mgr
        self.accel_mgr.setQuotedRaw(self.addKeystroke)
        self.platform = platform
        if self.count > 1 or self.platform == 'emacs':
            self.emacs = True
        else:
            self.emacs = False
        self.append = append
        self.action_name = action_name
        
        if append:
            text = "Additional key binding for %s:"
        else:
            text = "New key binding for %s:"
        if trigger:
            text += " (end with %s)" % self.getAccelerator(self.trigger)
        elif count > 1:
            text += " (%d keystrokes)" % self.count
        elif count > 0:
            text += " (%d keystroke)" % self.count
        
        self.status_text = text % self.action_name
        self.statusUpdateHook(self.status_text)
    
    def statusUpdateHook(self, status_text):
        """Hook for subclasses to provide a display method as each keystroke
        is entered.
        
        """
        print(status_text)
    
    def getAccelerator(self, keystroke):
        """Convenience function to return the accelerator text of a keystroke
        
        Uses the L{KeystrokeRecording.emacs} instance attribute to determine if
        the accelerator should be displayed in emacs form or native platform
        form.
        """
        if self.emacs:
            acc = keystroke.getEmacsAccelerator()
        else:
            acc = keystroke.getMenuAccelerator()
        return acc
        
    def addKeystroke(self, keystroke):
        """Callback method for L{AcceleratorManager.setQuotedRaw}
        
        Used to add a keystroke to the key sequence list, and if the end of
        the key sequence is reached, calls L{finishRecording}.
        """
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
                self.statusUpdateHook(self.status_text)
                self.addKeystrokeHook()
                wx.CallAfter(self.accel_mgr.setQuotedRaw, self.addKeystroke)
    
    def addKeystrokeHook(self):
        """Hook for subclasses to perform some action after each keystroke
        has been entered.
        
        """
        pass
    
    def finishRecording(self):
        """Cleanup method to save the new key sequence.
        
        Saves the new key sequence as an accelerator for the action.  This is
        called from L{addKeystroke} when the key sequence has been completed.
        """
        dprint("Recording %s" % (self.recording))
        acc = " ".join(self.recording)
        self.status_text = "New key binding for %s: %s" % (self.action_name, acc)
        self.statusUpdateHook(self.status_text)
        self.finishRecordingHook(acc)
    
    def finishRecordingHook(self, accelerator_text):
        """Hook for subclasses to perform some action after the final keystroke
        has been added.
        
        @param accelerator_text: text string containing the accelerator key(s)
        """
        pass


class FakeCharEvent(object):
    def __init__(self, evt):
        self.event_object = evt.GetEventObject()
        self.id = evt.GetId()
        self.modifiers = evt.GetModifiers()
        self.keycode = evt.GetKeyCode()
        self.unicode = evt.GetUnicodeKey()
    
    def GetEventObject(self):
        return self.event_object
    
    def GetId(self):
        return self.id
    
    def GetModifiers(self):
        return self.modifiers
    
    def GetUnicodeKey(self):
        return self.unicode
    
    def GetKeyCode(self):
        return self.keycode
    
    def Skip(self):
        pass


class FakeQuotedCharEvent(FakeCharEvent):
    def __init__(self, event_object, keystroke, id=None, evt=None):
        self.evt = evt
        if id is None:
            self.id = -1
        else:
            self.id = keystroke.id
        self.modifiers = keystroke.flags
        self.keycode = keystroke.keycode
        self.event_object = event_object
    
    def GetUnicodeKey(self):
        keycode = self.keycode
        # If the keycode is ASCII, normalize it to a capital letter
        if keycode >= ord('a') and keycode <= ord('z'):
            keycode -= 32
        if keycode >= ord('A') and keycode <= ord('Z'):
            if self.modifiers == wx.ACCEL_CTRL:
                keycode -= 64
            elif self.modifiers == wx.ACCEL_SHIFT:
                keycode += 32
        return keycode
    
    def Skip(self):
        if self.evt:
            self.evt.Skip()


class QuotedCharAction(object):
    """Special action used to quote the next character verbatim.
    
    Sometimes, especially in search fields, it is desirable to have the ability
    to insert raw characters like the tab character or return characters.
    This action provides the callback mechanism to save the data needed to
    process the next character typed as a raw character.
    """
    def __init__(self, accel):
        self.accel = accel
    
    def actionWorksWithCurrentFocus(self):
        return True
    
    def action(self, index=-1, multiplier=1):
        self.multiplier = multiplier
        self.accel.setQuotedNext(multiplier)
    
    def actionKeystroke(self, evt, multiplier=1):
        self.action(-1, multiplier)


class QuotedData(object):
    """Data for the next quoted character"""
    def __init__(self, multiplier):
        self.multiplier = multiplier
        
    def getMultiplier(self):
        return self.multiplier


class AcceleratorList(object):
    """Driver class for multi-keystroke processing of CommandEvents.
    
    This class creates nested accelerator tables for processing multi-keystroke
    commands.  The tables are switched in and out dynamically as key events
    come into the L{processEvent} method.  Menu actions are also handled here.
    If the user selects a menu item, any in-progress multi-key sequence is
    cancelled.
    
    Multiple instances of this class are nested in the root instance.  The
    root instance holds the first character in all keystroke commands as
    well as all menu IDs.  Any multi-key combinations additional instances of
    AcceleratorList to the root level so that when the first keystroke is hit,
    the class switches out the frame's accelerator table to the table holding
    the next level's valid keystrokes.  This can be nested as far as necessary.
    
    
    """
    # Set the debug level to 1 for debugging output as keystrokes are typed,
    # and 2 for debugging info during the accelerator list creation and
    # deletion process
    debug = 0
    
    esc_keystroke = KeyAccelerator.split("ESC")[0]
    meta_esc_keystroke = KeyAccelerator.split("M-ESC")[0]
    
    # Various mappings between keystrokes, keystroke IDs, and keycodes
    digit_value = {}
    meta_digit_keystroke = {}
    plain_digit_keystroke = {}
    digit_keycode = {}
    digit_keycode_to_keystroke = {}
    for i in range(10):
        keystroke = KeyAccelerator.split("M-%d" % i)[0]
        meta_digit_keystroke[keystroke.id] = keystroke
        digit_value[keystroke.id] = i
        keystroke = KeyAccelerator.split("%d" % i)[0]
        plain_digit_keystroke[keystroke.id] = keystroke
        digit_value[keystroke.id] = i
        digit_keycode[keystroke.keycode] = i
        digit_keycode_to_keystroke[keystroke.keycode] = keystroke
    
    class ActionMap(object):
        """Simple helper class to provide multiple actions based on the window
        in which the event happened.
        """
        def __init__(self, action, window=None):
            self.actions = {}
            self.addAction(action, window)
        
        def __str__(self):
            return str(self.actions)
        
        def addAction(self, action, window=None):
            self.actions[window] = action
        
        def hasAction(self, window=None):
            return window in self.actions
        
        def getAction(self, window=None):
            try:
                return self.actions[window]
            except KeyError:
                try:
                    return self.actions[None]
                except KeyError:
                    return None
        
        def getActionOfWindow(self, window):
            return self.actions.get(window, None)
        
        def removeAction(self, window):
            if window in self.actions:
                del self.actions[window]
    
    def __init__(self):
        # Map of ID to keystroke for the current level
        self.id_to_keystroke = {}
        
        # Map of all IDs that have additional keystrokes, used in multi-key
        # processing.
        self.id_next_level = {}
        
        # Map of all keystroke IDs in this level to actions
        self.keystroke_id_to_action = {}
        
        # Map used to rebuild key bindings when reset
        self.multikey_binding_to_action = {}
        
    def __str__(self):
        return self.getPrettyStr()
    
    def __del__(self):
        if self.debug > 1: dprint("deleting %s" % (repr(self), ))
    
    
    def cleanSubLevels(self):
        """Recursive function to remove all references to the root object
        """
        self.current_level = None
#        for accel_list in self.id_next_level.values():
#            accel_list.cleanSubLevels()
        self.id_next_level = None
        self.menu_id_to_action = None
        self.keystroke_id_to_action = None

    def getPrettyStr(self, prefix=""):
        """Recursive-capable function to return a list of keystrokes at this
        level and below.
        """
        lines = []
        keys = self.id_to_keystroke.keys()
        keys.sort()
        for key in keys:
            keystroke = self.id_to_keystroke[key]
            lines.append("%skey %d: %s %s" % (prefix, key, keystroke.getEmacsAccelerator(), str(keystroke.getAcceleratorTableEntry())))
            if key in self.id_next_level:
                lines.append(self.id_next_level[key].getPrettyStr(prefix + "  "))
        return os.linesep.join(lines)

    def getCurrentKeyBindings(self, binding_of, previous_keystrokes=None):
        """Recursive-capable function to return dict of actions and keystrokes
        that trigger the actions.
        
        """
        if previous_keystrokes is None:
            previous_keystrokes = []
        for keystroke_id, actionmap in self.keystroke_id_to_action.iteritems():
            keystroke = self.id_to_keystroke[keystroke_id]
            keystrokes = previous_keystrokes[:]
            keystrokes.append(keystroke)
            for ctrl, action in actionmap.actions.iteritems():
                if action is not None:
                    acc = KeyAccelerator.getEmacsAccelerator(keystrokes)
                    binding_of[acc] = action
                    if self.debug > 1: dprint("found action: %s, keystroke %s" % (action, acc))
            if keystroke_id in self.id_next_level:
                next = self.id_next_level[keystroke_id]
                next.getCurrentKeyBindings(binding_of, keystrokes)

    def addKeyBinding(self, key_binding, action=None, window=None):
        """Add a key binding to the list.
        
        @param key_binding: text string representing the keystroke(s) to
        trigger the action.
        
        @param action: action to be called by this key binding
        
        @param cancel_Key: if True, this keystroke will be added to all levels
        and will cause the current keystrokes to be cancelled along with
        calling the action.
        """
        if isinstance(key_binding, list):
            for key_binding_entry in key_binding:
                self._addKeyBinding(key_binding_entry, action, window)
        else:
            self._addKeyBinding(key_binding, action, window)
    
    def _addKeyBinding(self, key_binding, action=None, window=None):
        if window is None:
            previous = self.multikey_binding_to_action.get(key_binding, None)
            if previous:
                if previous.default_menu:
                    dprint("%s already bound to menu item %s and takes precedence over attempted rebind to %s" % (key_binding, previous.__class__.__name__, action.__class__.__name__))
                    return
                else:
                    dprint("%s previously bound to %s has been rebound to %s" % (key_binding, previous.__class__.__name__, action.__class__.__name__))
            self.multikey_binding_to_action[key_binding] = action
        else:
            if not hasattr(window, 'multikey_binding_to_action'):
                # We store a new attribute in the wx.Window to hold the key
                # binding info for itself.
                if self.debug > 1: dprint("Setting multikey_binding_to_action in %s" % window)
                window.multikey_binding_to_action = {}
            window.multikey_binding_to_action[key_binding] = action
    
    def rebuildRootKeyBindings(self):
        self.id_to_keystroke = {}
        self.id_next_level = {}
        self.keystroke_id_to_action = {}
        
        self.rebuildWindowKeyBindings(self.multikey_binding_to_action)
    
    def rebuildWindowKeyBindings(self, key_binding_to_action, window=None):
        if not key_binding_to_action:
            return
        for key_binding, action in key_binding_to_action.iteritems():
            self.bindKeystrokes(key_binding, action, window)
    
    def bindKeystrokes(self, key_binding, action, window=None):
        keystrokes = KeyAccelerator.split(key_binding)
        keycount = len(keystrokes)
        count = 0
        current = self
        while count < keycount:
            keystroke = keystrokes[count]
            count += 1
            current.id_to_keystroke[keystroke.id] = keystroke
            if count == keycount:
                try:
                    existing = current.keystroke_id_to_action[keystroke.id]
                    existing_action = existing.getActionOfWindow(window)
                    if existing_action != action and existing_action != None and action != None:
                        # Unless it's a placeholder action, if there are
                        # different actions for the same keystroke, raise
                        # an error.
                        raise DuplicateKeyError("Key sequence %s for action %s already mapped to %s for window %s" % (str([str(k) for k in keystrokes[:-1]]), action, existing.getAction(window), window))
                except KeyError:
                    existing = None
                if existing is not None:
                    # Only add an action if the action is not None, because
                    # action == None only serves as a placeholder and if there
                    # is an existing action we already have something linked
                    # to the keystroke
                    if action is not None:
                        existing.addAction(action, window)
                    else:
                        if self.debug > 1: dprint("Ignoring placeholder key %s (%s) because there's already an existing action" % (key_binding, keystroke))
                else:
                    current.keystroke_id_to_action[keystroke.id] = AcceleratorList.ActionMap(action, window)
            else:
                try:
                    current = current.id_next_level[keystroke.id]
                except KeyError:
                    accel_list = AcceleratorList()
                    current.id_next_level[keystroke.id] = accel_list
                    current = accel_list
    
    def findKeyBinding(self, key_binding):
        """Given text representing a key binding, find the list of keystroke
        IDs that map to that binding.
        
        @return: tuple containing the list of ids and the action.  Each entry
        in the list represents one level in the id_next_level chain except for
        the last entry which is the value of the keystroke_id_to_action entry.
        """
        keystrokes = KeyAccelerator.split(key_binding)
        ids = []
        action = None
        current = self
        for keystroke in keystrokes:
            ids.append(keystroke.id)
            try:
                current = current.id_next_level[keystroke.id]
            except KeyError:
                action = current.keystroke_id_to_action[keystroke.id]
                break
        return ids, action
        
    def addCancelKeysToLevels(self, key_binding, action):
        """Recursive function to add the cancel keybinding to the current level
        and all sub levels
        """
        for accel_list in self.id_next_level.values():
            accel_list.addCancelKeysToLevels(key_binding, action)
        self.addKeyBinding(key_binding, action)
    
    def isModifierOnly(self, evt):
        return evt.GetKeyCode() in ignore_modifiers



class UnknownKeySequence(RuntimeError):
    pass


class CurrentKeystrokes(object):
    """Object to hold the current processing status variables
    
    """
    def __init__(self):
        # Has the ESC key been pressed?
        self.meta_next = False
        
        # Are we processing a chain of ESC digits to act as a repeat value?
        self.processing_esc_digit = False
        
        # Current keystrokes
        self.current_keystrokes = []
        
        # Flag to indicate the next character should be quoted
        self.quoted_next = False
        
        # temporary variable to hold the last keycode from key down event
        self.unknown_keystroke = None
    
        # Repeat values
        self.repeat_initialized = False
        self.repeat_value = 1
        
        # Number of characters in prefix
        self.prefix_count = 0

    def processChar(self, evt, manager):
        if AcceleratorList.debug: dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), self.repeat_value, evt.GetId()))
        if self.quoted_next:
            # Short circuit this character so that it isn't processed
            self.repeat_value = self.quoted_next.getMultiplier()
            if AcceleratorList.debug: dprint("Processing quoted character, multiplier=%s" % self.repeat_value)
            #
            manager.frame.SetStatusText("")
        elif not manager.isRoot() and not self.processing_esc_digit:
            # If we get an unhandled keystroke after a multi-key sequence, we
            # ignore it as a bad key combination.
            raise UnknownKeySequence
        eid = evt.GetId()
        if AcceleratorList.debug: dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), self.repeat_value, eid))
    
    def processEscDigit(self, keystroke):
        if not self.repeat_initialized:
            self.repeat_value = AcceleratorList.digit_value[keystroke.id]
            self.repeat_initialized = True
        else:
            self.repeat_value = 10 * self.repeat_value + AcceleratorList.digit_value[keystroke.id]
        self.prefix_count += 1
        if AcceleratorList.debug: dprint("in processEscDigit: FOUND REPEAT %d" % self.repeat_value)

    def getKeystrokeTuple(self, include_prefix=False):
        """Get the keystrokes in the form of a tuple
        
        @return: a tuple containing the keystrokes that triggered this action.
        It returns a tuple instead of a list so that can be directly compared
        with the result of the KeyAccelerator.split
        """
        if include_prefix:
            start = 0
        else:
            start = self.prefix_count
        keystrokes = tuple(self.current_keystrokes[start:])
        return keystrokes

class AbstractActionRecorder(object):
    """Abstract class that must be implemented by some recording mechanism
    in order to provide macro functionality.
    
    The calls to L{recordKeystroke} and L{recordMenu} provide all the
    information necessary to reproduce the action.  Subclasses should save
    this information in some manner and provide a means to store and/or play
    back the action.
    
    Not all actions are capable of being recorded.  The action's
    L{isRecordable} classmethod will return a boolean that indicates whether
    or not the action should be included in the list of saved actions.  It
    is not recommended that the recording process be allowed to continue if a
    non-recordable action is found.
    """
    def recordKeystroke(self, action, evt, multiplier):
        """The L{AcceleratorManager} calls this method whenever a keystroke
        action is performed.
        """
        pass
    
    def recordMenu(self, action, index):
        """The L{AcceleratorManager} calls this method whenever a keystroke
        action is performed.
        """
        pass
    
    def getRecordedActions(self):
        """Returns the list of L{RecordedAction}s instances.
        
        """
        return []


class AcceleratorManager(AcceleratorList):
    """Driver class for multi-keystroke processing of CommandEvents.
    
    This class creates nested accelerator tables for processing multi-keystroke
    commands.  The tables are switched in and out dynamically as key events
    come into the L{processEvent} method.  Menu actions are also handled here.
    If the user selects a menu item, any in-progress multi-key sequence is
    cancelled.
    """
    use_meta_escape = True
    
    @classmethod
    def setMetaEscapeAllowed(cls, state=True):
        #dprint("allowing meta escape: %s" % state)
        cls.use_meta_escape = state
    
    @classmethod
    def isMetaEscapeAllowed(cls):
        return cls.use_meta_escape
    
    # Blank level used in quoted character processing
    def __init__(self, *args, **kwargs):
        AcceleratorList.__init__(self)
        
        # The root keeps track of the current level that is another
        # instance of AcceleratorList from the id_next_level map
        self.current_level = None
        
        # Map of all menu IDs to actions.  Note that menu actions only occur
        # in the root level because wx doesn't allow multi-key actions in the
        # menu bar.  If they did, we wouldn't need this hackery!!! Note also
        # that there is no ActionMap associated with this because the menu
        # items all occur with the frame and not with transient controls
        self.menu_id_to_action = {}
        
        # If the menu id has an index, i.e.  it's part of a list or radio
        # button group, the index of the id is stored in this map
        self.menu_id_to_index = {}
        
        # Default keystroke action when nothing else is matched
        self.default_key_action = None
        
        # Electric character actions are for special characters that insert
        # themselves but also do something to the text like reindent or insert
        # snippets.
        self.electric_char_actions = {}
        
        # Raw keycodes can be quoted to an action by setting calling
        # L{SetQuotedRaw}, which in turn sets this value to the callback
        # function that will be used to return the raw keycode
        self.quoted_raw_callback = None
        
        self.pending_cancel_key_registration = []

        self.bound_controls = []
        
        self.current_target = None

        self.entry = CurrentKeystrokes()
        
        # Flag to indicate that the next keystroke should be ignored.  This is
        # needed because no OnMenu event is generated when a keystroke doesn't
        # exist in the translation table.
        self.skip_next = False
        
        # Status bar updates of characters seem to conflict with actual status
        # messages from minibuffers, so this variable holds the status column
        # to use instead of the primary
        self.status_column = 1
        
        # Flag to indicate that the next action should be reported rather
        # than acted upon.  Used to show documentation of keystrokes
        self.report_next = False
        
        # Callback processing for popups' EVT_MENU actions
        self.popup_callback = None
        
        # Macro recording flag that if points to a L{AbstractActionRecorder}
        # instance will record every keystroke or menu selection
        self.recorder = None

        # Always have an ESC keybinding for emacs-style ESC-as-sticky-meta
        # processing
        self.addKeyBinding("ESC")
        for arg in args:
            if self.debug: dprint(str(arg))
            self.addKeyBinding(arg)
        
        # Add default and dummy actions
        for i in range(10):
            self.addKeyBinding("M-%d" % i)
            if self.use_meta_escape:
                self.addKeyBinding("ESC %d" % i)
            self.addKeyBinding("C-%d" % i)
            self.addKeyBinding("M-%d" % i)
            self.addKeyBinding("S-C-%d" % i)
            self.addKeyBinding("S-M-%d" % i)
            self.addKeyBinding("S-C-M-%d" % i)
        for i in range(26):
            self.addKeyBinding("C-%s" % chr(ord('A') + i))
            self.addKeyBinding("M-%s" % chr(ord('A') + i))
            self.addKeyBinding("S-C-%s" % chr(ord('A') + i))
            self.addKeyBinding("S-M-%s" % chr(ord('A') + i))
            self.addKeyBinding("S-C-M-%s" % chr(ord('A') + i))
        for c in "/,.?<>'[]\-=`\"{}|_+~":
            self.addKeyBinding("C-%s" % c)
            self.addKeyBinding("M-%s" % c)
            self.addKeyBinding("S-C-%s" % c) # this one overwrites C-Q
            self.addKeyBinding("S-M-%s" % c)
            self.addKeyBinding("S-C-M-%s" % c)
            
    
    def __del__(self):
        if self.debug > 1: dprint("deleting %s" % (repr(self), ))
    
    def manageFrame(self, frame, *ctrls):
        """Initialize the frame and controls to be managed by the key
        processor.
        
        """
        self.bindEvents(frame, *ctrls)
    
    def cleanup(self):
        """Remove events and cleanup recursive structure.
        
        Because there are recursive references to other AcceleratorLists inside
        the root lists, the root won't be automatically garbarge collected.
        
        I might be able to use weak references to get rid of all this stuff.
        """
        self.unbindEvents()
        self.cleanSubLevels()
    
    def addDefaultKeyAction(self, action, window=None):
        """If no other action is matched, this action is used.
        
        """
        if self.default_key_action is None:
            self.default_key_action = AcceleratorList.ActionMap(action, window)
        else:
            self.default_key_action.addAction(action, window)
    
    def addMenuItem(self, id, action=None, index=-1):
        """Add a menu item that doesn't have an equivalent keystroke.
        
        Note that even if a menu item has a keystroke and that keystroke has
        been added to the list using L{addKeyBinding}, this method still needs
        to be called because the menu item ID is different from the keystroke
        ID.
        
        @param id: wx ID of the menu item
        """
        self.menu_id_to_action[id] = action
        if index >= 0:
            if self.debug > 1: dprint("Adding index %d to %d, %s" % (index, id, str(action)))
            self.menu_id_to_index[id] = index
    
    def setQuotedNext(self, multiplier):
        """Set the quoted character flag
        
        When this is set, the next character typed will be passed verbatim to
        the default character action specified by L{addDefaultKeyAction}.
        """
        self.entry.quoted_next = QuotedData(multiplier)
        if self.debug: dprint("Next character will be quoted raw...")
        self.showMessage(_("Quoting:"))
    
    def setQuotedRaw(self, callback):
        """Set the quoted character raw callback
        
        When this is set, the next keystroke typed will be passed to the
        callback and no further processing of the keystroke will occur.
        
        The callback should take a single parameter which is the L{Keystroke}
        object that represents the raw keycode and modifier that was typed.
        """
        self.entry.quoted_next = QuotedData(1) # just used as a flag
        self.quoted_raw_callback = callback
        if self.debug: dprint("Next character will be quoted raw to %s..." % callback)
        self.showMessage(_("Quoting:"))
    
    def addCancelKeyBinding(self, key_binding, action=None):
        """Add a cancel key binding.
        
        Cancel keys are special keystrokes that are added to all levels.  A
        cancel key will cancel the current keystrokes without processing them,
        and will also call the action specified here.
        
        @param key_binding: text string representing the keystroke(s) to
        trigger the action.
        
        @param action: optional action to be called when the cancel key
        keystroke combination is pressed.
        """
        # Cancel keys can't be added until all other keystrokes have been added
        # to the list because a copy of the cancel key binding is added to all
        # levels.  If the key binding were added when this method is called,
        # key bindings added later that create new levels wouldn't have the
        # cancel key binding in them.  So, this is used as a flag to create
        # new keybindings when bindEvents is called.
        self.pending_cancel_key_registration.append((key_binding, action))
    
    def addCancelKeys(self):
        """Add cancel keys to all keybinding levels
        
        """
        if self.pending_cancel_key_registration:
            for key_binding, action in self.pending_cancel_key_registration:
                if self.debug: dprint("Adding cancel key %s" % key_binding)
                self.addCancelKeysToLevels(key_binding, action)
        self.pending_cancel_key_registration = []
    
    def registerElectricChar(self, uchar, action, target):
        """Add to the mapping of special character to action.
        
        These characters are only called in the OnChar processing, so they have
        been interpreted by the control.  Any unicode character may be used,
        not just the codes available through the keycode processing.
        """
        self.electric_char_actions[(uchar, target)] = action
    
    def isRoot(self):
        return self.current_level == self
    
    def bindEvents(self, frame, *ctrls):
        """Initialization function to create all necessary event bindings
        between the frame and the managed controls.
        
        """
        self.addCancelKeys()
        self.frame = frame
        frame.Bind(wx.EVT_MENU, self.OnMenu)
        frame.Bind(wx.EVT_MENU_CLOSE, self.OnMenuClose)
        for ctrl in ctrls:
            self.addEventBinding(ctrl)
        self.rebuildAllKeyBindings()
        self.current_level = self
    
    def addEventBinding(self, ctrl):
        if self.debug > 1: dprint("Adding event bindings for %s" % ctrl)
        self.bound_controls.append(ctrl)
        ctrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        ctrl.Bind(wx.EVT_CHAR, self.OnChar)
        
    def unbindEvents(self):
        """Cleanup function to remove event bindings
        
        """
        self.frame.Unbind(wx.EVT_MENU)
        self.frame.Unbind(wx.EVT_MENU_CLOSE)
        self.removeBindings(self.bound_controls)
        self.bound_controls = []
    
    def removeAndRebuildBindings(self, ctrls):
        self.removeBindings(ctrls)
        self.rebuildAllKeyBindings()
    
    def rebuildAllKeyBindings(self):
        self.rebuildRootKeyBindings()
        for ctrl in self.bound_controls:
            if hasattr(ctrl, 'multikey_binding_to_action'):
                if self.debug > 1: dprint("key binding storage for %s: %s" % (ctrl, ctrl.multikey_binding_to_action))
                self.rebuildWindowKeyBindings(ctrl.multikey_binding_to_action, ctrl)
    
    def removeBindings(self, ctrls):
        for ctrl in ctrls:
            self.removeEventBinding(ctrl)
            if self.default_key_action:
                if self.debug > 1: dprint("Removing default key action for %s" % ctrl)
                self.default_key_action.removeAction(ctrl)
            if self.debug > 1: dprint("Removing key binding storage %s" % getattr(ctrl, 'multikey_binding_to_action', None))
            ctrl.multikey_binding_to_action = {}
        self.bound_controls = [c for c in self.bound_controls if c not in ctrls]
    
    def removeEventBinding(self, ctrl):
        if ctrl in self.bound_controls:
            if ctrl:
                if self.debug > 1: dprint("Removing event bindings for %s" % ctrl)
                ctrl.Unbind(wx.EVT_KEY_DOWN)
                ctrl.Unbind(wx.EVT_CHAR)
            else:
                if self.debug > 1: dprint("Control %s already deleted, no need to remove bindings" % ctrl)
    
    def OnChar(self, evt):
        """Character event processor that handles everything not recognized
        by the menu or keyboard events.
        """
        try:
            self.entry.processChar(evt, self)
        except UnknownKeySequence:
            keystroke = self.entry.unknown_keystroke
            if self.debug: dprint(keystroke)
            self.resetKeyboardFail(keystroke, "not defined.")
            return
        
        uchar = unichr(evt.GetUnicodeKey())
        if not self.entry.quoted_next and (uchar, self.current_target) in self.electric_char_actions:
            action = self.electric_char_actions[(uchar, self.current_target)]
        elif self.default_key_action:
            action = self.default_key_action.getAction(self.current_target)
        else:
            action = None
        if action:
            if self.report_next:
                return self.processReportNext(action)
            if self.entry.quoted_next:
                evt.is_quoted = True
            self.doKeystroke(action, evt)
        else:
            if self.debug: dprint("No action available for window %s" % self.current_target)
        self.reset()
    
    def startRecordingActions(self, recorder):
        """Start recording actions
        
        Actions (either from keystrokes or from menu selections) are recorded
        in a list for later playback.
        
        @param recorder: instance of the L{ActionRecorder} class
        """
        self.recorder = recorder
    
    def stopRecordingActions(self):
        """Stop the action recording.
        
        The recorded action list is finalized here, and after this call the
        list of actions will be available through a call to the returned
        object's L{getRecordedActions}
        """
        recorder = self.recorder
        self.recorder = None
        return recorder
    
    def isRecordingActions(self):
        """Check to see if currently recording actions.
        """
        return bool(self.recorder)
    
    def doKeystroke(self, action, evt):
        """Calls the actionKeystroke method of an action, possibly recording
        the action
        
        Driver function for all calls to the actionKeystroke method of an
        action.  Handles recording the action in the recorded actions list if
        recording is turned on.
        """
        multiplier = self.entry.repeat_value
        if self.recorder:
            self.recorder.recordKeystroke(action, evt, multiplier)
        self.last_keystroke = self.entry
        if self.debug: dprint("Calling action %s" % action)
        action.actionKeystroke(evt, multiplier=multiplier)
    
    def doMenu(self, action, index):
        """Calls the menu activation method of an action, possibly recording it
        
        Driver function for all calls to the menu activation method of an
        action.  Handles recording the action in the recorded actions list if
        recording is turned on.
        """
        multiplier = self.entry.repeat_value
        if self.recorder:
            self.recorder.recordMenu(action, index, multiplier)
        self.last_keystroke = self.entry
        if self.debug: dprint("Calling action %s" % action)
        wx.CallAfter(action.action, index, multiplier)
    
    def getLastKeystroke(self):
        """Returns the keystroke used for the last processed action.
        
        Also usable during an event handler's action or actionKeystroke callback
        """
        return self.last_keystroke
    
    def setReportNext(self, callback):
        """Set the report action callback
        
        When this is set, the next action that is found will be reported to the
        callback function rather than being acted upon.  This can be used for
        documentation purposes to display the docstring of the action.
        """
        self.report_next = callback
        self.showMessage(_("Describe key:"))
    
    def processReportNext(self, action):
        wx.CallAfter(self.report_next, action)
        self.report_next = False
        self.reset()
    
    def OnKeyDown(self, evt):
        """Helper event processing loop to be called from the Frame's
        EVT_KEY_DOWN callback.
        
        This is needed because there's no other way to cancel a bad multi-key
        keystroke.  EVT_MENU won't be called at all on an unrecognized
        keystroke but EVT_KEY_DOWN will will always be called, so we use this
        to preemptively check to see if the keystroke will be accepted or not
        and set appropriate flags for later use.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        eid = evt.GetId()
        keycode = evt.GetKeyCode()
        
        self.current_target = self.frame.FindFocus()

        if self.debug: dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (keycode, evt.GetUnicodeKey(), self.entry.repeat_value, eid))
        if self.entry.quoted_next and not self.quoted_raw_callback:
            if self.debug: dprint("Quoted next; skipping OnKeyDown to be processed by OnChar")
            evt.Skip()
            return
        
        keystroke = KeyAccelerator.getKeystroke((evt.GetModifiers(), keycode))
        if self.debug: dprint(keystroke)
        if keystroke.isModifierOnly():
            evt.Skip()
            return
        
        if self.quoted_raw_callback:
            self.processQuotedRaw(keystroke)
            return
        
        processed, keystroke = self.processEsc(evt, keystroke)
        if processed:
            return
        
        processed = self.processMultiKey(evt, keystroke)
        if processed:
            return
        
        if wx.Platform == '__WXMSW__' and evt.GetKeyCode() == wx.WXK_ESCAPE:
            evt = FakeQuotedCharEvent(self.current_target, self.esc_keystroke)
            self.OnMenu(evt)
        else:
            self.entry.unknown_keystroke = keystroke
            evt.Skip()
    
    def processQuotedRaw(self, keystroke):
        """Return the raw keystroke to a caller
        
        This returns the raw keystroke and prevents further processing of the
        keystroke.  The state of the keyboard processing is then reset to
        normal processing, so if you need multiple keystrokes, you'll need to
        call L{setQuotedRaw} again.
        """
        self.quoted_raw_callback(keystroke)
        self.quoted_raw_callback = None
        self.reset()
    
    def processEsc(self, evt, keystroke):
        """Process the keystroke for the ESC key.
        
        The ESC key can be used as a modifier for the next character, either by
        transforming it into an alt key, or by using it to prefix digits to be
        used as a repeat value.
        
        @param evt: KeyEvent
        
        @param keystroke: Keystroke converted from the event
        
        @return: 2-tuple of boolean status indicating if the keystroke was
        processed and no further processing is needed, and the new transformed
        keystroke if a previous ESC character modified this keystroke.
        """
        eid = keystroke.id
        if keystroke == self.esc_keystroke:
            if self.entry.meta_next:
                keystroke = self.meta_esc_keystroke
                eid = keystroke.id
                self.entry.meta_next = False
                self.entry.current_keystrokes.pop()
                if self.debug: dprint("in processEvent: evt=%s id=%s FOUND M-ESC" % (str(evt.__class__), eid))
            elif self.entry.current_keystrokes and self.entry.current_keystrokes[-1] == self.meta_esc_keystroke:
                # M-ESC ESC is processed as a regular keystroke
                if self.debug: dprint("in processEvent: evt=%s id=%s FOUND M-ESC ESC" % (str(evt.__class__), eid))
                pass
            elif self.use_meta_escape:
                if self.debug: dprint("in processEvent: evt=%s id=%s FOUND ESC" % (str(evt.__class__), eid))
                self.entry.meta_next = True
                self.entry.prefix_count += 1
                self.updateCurrentKeystroke(keystroke)
                return True, keystroke
        elif eid in self.meta_digit_keystroke:
            self.entry.processEscDigit(keystroke)
            self.updateCurrentKeystroke(keystroke)
            return True, keystroke
        elif (self.entry.meta_next or self.entry.processing_esc_digit) and eid in self.plain_digit_keystroke:
            if self.debug: dprint("After ESC, found digit char: %d" % evt.GetKeyCode())
            self.entry.meta_next = False
            self.entry.processing_esc_digit = True
            self.entry.processEscDigit(keystroke)
            self.updateCurrentKeystroke(keystroke)
            return True, keystroke
        elif self.entry.meta_next:
            # If we run into anything else while we're processing a digit
            # string, stop the digit processing change the accelerator to an alt
            if self.debug: dprint("After ESC, found non-digit char: %d; adding alt to modifiers" % evt.GetKeyCode())
            keystroke = KeyAccelerator.getKeystroke((evt.GetModifiers()|wx.ACCEL_ALT, keycode))
            self.entry.processing_esc_digit = False
        elif self.entry.processing_esc_digit:
            # A non-digit character during digit processing will reset the
            # accelerator table back to the root so we can then find out
            # the command to which the digits will be applied.
            self.entry.processing_esc_digit = False
        return False, keystroke

    def processMultiKey(self, evt, keystroke):
        """Process the next keystroke.
        
        Examine the keystroke to see if it's part of a multi-key sequence or is
        the final key that specifies an action.
        
        If it is part of a multi-key sequence and it's not the end of the
        sequence, it will note that there are still key sequences remaining
        before an action can be determined.
        
        If it is part of a key sequence and it uniquely identifies an action
        (i.e.  it's the last key of the sequence), the action is called.
        
        If it's neither of those things, it returns False to let the caller
        know to continue processing.
        
        @param evt: KeyEvent
        
        @param keystroke: Keystroke converted from the event
        
        @return: True if the keystroke was acted upon, either as a valid or
        invalid keystroke.  If the keystroke doesn't match any of the criteria
        in this method (for instance if it is an unknown keystroke for this
        level) it will return False.
        """
        eid = keystroke.id
        if eid in self.current_level.id_next_level:
            if self.debug: dprint("in processEvent: evt=%s id=%s FOUND MULTI-KEYSTROKE" % (str(evt.__class__), eid))
            self.current_level = self.current_level.id_next_level[eid]
            self.updateCurrentKeystroke(keystroke, pending=True)
            return True
        elif eid in self.current_level.keystroke_id_to_action:
            if self.debug: dprint("in processEvent: evt=%s id=%s FOUND ACTION %s repeat=%s" % (str(evt.__class__), eid, self.current_level.keystroke_id_to_action[eid].actions, self.entry.repeat_value))
            action = self.getKeystrokeAction(eid)
            if self.report_next:
                self.processReportNext(action)
                return True
            if action is not None:
                if action.actionWorksWithCurrentFocus():
                    self.updateCurrentKeystroke(keystroke)
                    self.doKeystroke(action, evt)
                else:
                    # Found action but it doesn't work with the current focus.
                    # It should passed up though the OnChar processing.
                    if self.debug: dprint("found keystroke but action doesn't work with current focus.  Allowing to propagate to OnChar")
                    return False
            else:
                self.updateCurrentKeystroke(keystroke, "not defined..")
            
            if not self.entry.quoted_next:
                self.resetKeyboardSuccess()
            return True
        return False
    
    def getKeystrokeAction(self, eid):
        """Determine the action to use based on the currently targeted window
        
        The default action is used if the currently targeted window doesn't
        exist in the action map for this keystroke.
        """
        actionmap = self.current_level.keystroke_id_to_action[eid]
        action = actionmap.getAction(self.current_target)
        return action

    def getMenuAction(self, eid):
        """Determine the action to use based on the currently targeted window
        
        The default action is used if the currently targeted window doesn't
        exist in the action map for this keystroke.
        """
        action = self.menu_id_to_action[eid]
        return action

    def OnMenuClose(self, evt):
        """Helper event processing to cancel multi-key keystrokes
        
        Using EVT_MENU_CLOSE instead of EVT_MENU_OPEN because on MSW the
        EVT_MENU_OPEN event is called when a keyboard accelerator matches the
        menu accelerator, regardless of the state of the accelerator table.
        """
        if self.debug: dprint("id=%d menu_id=%d" % (evt.GetId(), evt.GetMenuId()))
        self.cancelMultiKey()
    
    def addPopupCallback(self, callback):
        """Short circuit menu handling with the specified callback to handle
        popup menu processing.
        
        The callback function should be a regular event handler that takes a
        single parameter, the CommandEvent of the EVT_MENU.
        """
        self.popup_callback = callback
    
    def removePopupCallback(self):
        """Remove any popup menu callback"""
        self.popup_callback = None

    def OnMenu(self, evt):
        """Main event processing loop to be called from the Frame's EVT_MENU
        callback.
        
        This method is designed to be called from the root level as it
        redirects the event processing to the current keystroke level.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        # If a toolbar button is clicked while in the middle of a multi-key
        # keystroke combination, kill the multi-key combo and allow the
        # toolbar ID to be processed.
        if isinstance(evt.GetEventObject(), wx.ToolBar) and self.current_level != self:
            self.cancelMultiKey()
            
        if self.debug: dprint("id=%d event=%s" % (evt.GetId(), evt))
        if self.popup_callback:
            if self.debug: dprint("handling evt for popup")
            self.popup_callback(evt)
            return
        if self.skip_next:
            # The incoming character has been already marked as being bad by a
            # KeyDown event, so we should't process it.
            if self.debug: dprint("in processEvent: skipping incoming char marked as bad by OnKeyDown")
            self.skip_next = False
        else:
            self.current_target = self.frame.FindFocus()

            eid = evt.GetId()
            if self.entry.quoted_next:
                try:
                    keystroke = self.id_to_keystroke[eid]
                except KeyError:
                    keystroke = self.findKeystrokeFromMenuId(eid)
                if self.debug: dprint(keystroke)
                if self.quoted_raw_callback:
                    self.processQuotedRaw(keystroke)
                else:
                    evt = FakeQuotedCharEvent(self.current_target, keystroke)
                    self.OnChar(evt)
            elif eid in self.menu_id_to_action:
                self.foundMenuAction(evt)
            else:
                if self.debug: dprint("in processEvent: evt=%s id=%s not found in this level" % (str(evt.__class__), eid))
                self.reset()
    
    def findKeystrokeFromMenuId(self, eid):
        """Find the keystroke that corresponds to the current menu ID
        
        Will raise KeyError if eid not found in the list of valid menu actions
        """
        action = self.getMenuAction(eid)
        return self.findKeystrokeFromMenuAction(action)
    
    def findKeystrokeFromMenuAction(self, action):
        """Find the keystroke that corresponds to the menu action
        
        Will raise KeyError if eid not found in the list of valid menu actions
        
        By design, all menu actions will occur in the L{ActionMap} window
        target of None.  Transient controls currently aren't allowed to change
        the menu bar to include their own menu items.
        """
        if self.debug: dprint("checking for action %s: keystroke IDs=%s" % (action, str(self.keystroke_id_to_action.keys())))
        for keystroke_id, actionmap in self.keystroke_id_to_action.iteritems():
            # NOTE: this is not actionmap.getAction(self.current_target)
            # because all menu items that have key bindings will have a window
            # target of None.
            keystroke_action = actionmap.getAction(None)
            if action == keystroke_action:
                keystroke = self.id_to_keystroke[keystroke_id]
                return keystroke
        raise KeyError
    
    def foundMenuAction(self, evt):
        """Fire off an action found in menu item or toolbar item list
        """
        eid = evt.GetId()
        if self.current_level != self:
            # Events won't be processed as a menu action if we are in the
            # middle of a multi-key keystroke.  We need to get the keystroke
            # equivalent of the menu item and process it as a multi-key action.
            keystroke = self.findKeystrokeFromMenuId(eid)
            
            processed, keystroke = self.processEsc(evt, keystroke)
            if processed:
                return
            
            processed = self.processMultiKey(evt, keystroke)
            if processed:
                return
            
            self.resetKeyboardFail(keystroke, "not defined...")
            return
            
        action = self.getMenuAction(eid)
        if action is not None:
            if self.report_next:
                action, evt = self.findKeystrokeActionFromMenuAction(action)
                if action:
                    self.processReportNext(action)
                else:
                    self.resetKeyboardFail(keystroke, "not defined...")
                    return
            elif action.actionWorksWithCurrentFocus():
                try:
                    index = self.menu_id_to_index[eid]
                except KeyError:
                    index = -1
                if self.debug: dprint("evt=%s id=%s index=%d repeat=%s FOUND MENU ACTION %s" % (str(evt.__class__), eid, index, self.entry.repeat_value, self.menu_id_to_action[eid]))
                self.doMenu(action, index)
            else:
                action, evt = self.findKeystrokeActionFromMenuAction(action)
                if action:
                    if self.debug: dprint("id=%s menu action %s USED AS KEYSTROKE ACTION" % (eid, self.menu_id_to_action[eid]))
                    self.doKeystroke(action, evt)
                else:
                    if self.debug: dprint("id=%s menu action %s NOT VALID ON CURRENT FOCUS" % (eid, self.menu_id_to_action[eid]))
        elif self.entry.meta_next and eid in self.plain_digit_keystroke:
            self.entry.meta_next = False
            self.entry.processing_esc_digit = True
            self.entry.processEscDigit(self.plain_digit_keystroke[eid])
            return
        elif self.entry.processing_esc_digit and eid in self.plain_digit_keystroke:
            self.entry.processEscDigit(self.plain_digit_keystroke[eid])
            return
        else:
            if self.debug: dprint("evt=%s id=%s repeat=%s FOUND MENU ACTION NONE" % (str(evt.__class__), eid, self.entry.repeat_value))
            self.frame.SetStatusText("None", self.status_column)
        self.resetMenuSuccess()
    
    def findKeystrokeActionFromMenuAction(self, action):
        """Find the keystroke that corresponds to the current menu ID
        
        Finds the keystroke from the menu bar, translates that to a keystroke,
        and looks up the keystroke in the L{ActionMap} of the current window
        target.
        
        Will raise KeyError if eid not fount in the list of valid menu actions
        
        @return: tuple of the action that corresponds to the keystroke in
        the current_target window, and a fake char event to be passed to the
        action's actionKeystroke method.
        """
        keystroke = self.findKeystrokeFromMenuAction(action)
        actionmap = self.keystroke_id_to_action[keystroke.id]
        action = actionmap.getAction(self.current_target)
        if action:
            evt = FakeQuotedCharEvent(self.current_target, keystroke)
        else:
            evt = None
        return action, evt
    
    def updateCurrentKeystroke(self, keystroke, info=None, pending=False):
        """Add the keystroke to the list of keystrokes displayed in the status
        bar as the user is typing.
        """
        self.entry.current_keystrokes.append(keystroke)
        self.displayCurrentKeystroke(info, pending)
    
    def displayCurrentKeystroke(self, info=None, pending=False):
        """Display the list of keystrokes (with an optional informational
        message) in the status bar
        """
        if pending or len(self.entry.current_keystrokes) > 1 or info is not None:
            text = KeyAccelerator.getEmacsAccelerator(self.entry.current_keystrokes)
            if info is not None:
                text += " " + info
            self.frame.SetStatusText(text, self.status_column)
    
    def cancelMultiKey(self):
        if self.current_level != self:
            self.reset(_("Cancelled multi-key keystroke"))
            
    def reset(self, message=""):
        self.entry = CurrentKeystrokes()
        if self.debug: dprint("resetting status text to %s" % message)
        self.frame.SetStatusText(message, self.status_column)
        self.current_level = self
    
    def resetKeyboardSuccess(self):
        self.entry = CurrentKeystrokes()
        self.current_level = self
    
    def resetKeyboardFail(self, keystroke, info=None):
        self.updateCurrentKeystroke(keystroke, info)
        self.entry = CurrentKeystrokes()
        self.current_level = self
    
    def resetMenuSuccess(self):
        self.reset()
            
    def showMessage(self, message=""):
        self.frame.SetStatusText(message, self.status_column)
    
    def skipNext(self):
        self.skip_next = True
        self.reset()
    
    def getKeyBindings(self):
        """Return a dict of key bindings and their associated actions
        
        """
        bindings = {}
        self.getCurrentKeyBindings(bindings)
        return bindings
    
    def getUnboundActions(self):
        """Return a list of actions that are only callable through the menu
        interface
        
        """
        bindings = {}
        for menu_id, action in self.menu_id_to_action.iteritems():
            try:
                keystroke = self.findKeystrokeFromMenuAction(action)
                if self.debug > 1: dprint("menu keystroke=%s.  Not unbound." % keystroke)
            except KeyError:
                bindings[action] = True
        return bindings.keys()



if __name__ == '__main__':
    class ActionWrapper:
        def __init__(self, function):
            self.function = function
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            self.function()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)
    
    class StatusUpdater:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            if multiplier is not None:
                self.frame.SetStatusText("%d x %s" % (multiplier, self.message))
            else:
                self.frame.SetStatusText(self.message)
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)
    
    class SelfInsertCommand(object):
        def __init__(self, frame, ctrl):
            self.frame = frame
            self.ctrl = ctrl
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            raise NotImplementedError
        def actionKeystroke(self, evt, multiplier=1, **kwargs):
            raise NotImplementedError

    class SelfInsertSTC(SelfInsertCommand):
        def actionKeystroke(self, evt, multiplier=1, **kwargs):
            text = unichr(evt.GetUnicodeKey()) * multiplier
            dprint("char=%s, unichar=%s, multiplier=%s, text=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), multiplier, text))
            self.ctrl.AddText(text)

    class SelfInsertText(SelfInsertCommand):
        def actionKeystroke(self, evt, multiplier=1, **kwargs):
            if evt.GetModifiers() == wx.MOD_CONTROL:
                uchar = unichr(evt.GetUnicodeKey())
            else:
                uchar = unichr(evt.GetKeyCode())
            if hasattr(evt, 'is_quoted'):
                text = uchar * multiplier
                dprint("char=%s, unichar=%s, multiplier=%s, text=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), multiplier, text))
                self.ctrl.WriteText(text)
            else:
                if multiplier > 1:
                    text = uchar * (multiplier - 1)
                    self.ctrl.WriteText(text)
                evt.Skip()

    class TextCtrlDelete(SelfInsertCommand):
        def actionKeystroke(self, evt, multiplier=1):
            start, end = self.ctrl.GetSelection()
            dprint("start=%d end=%d multiplier=%d" % (start, end, multiplier))
            if start == end:
                # If there's no selection, delete the number of characters requested
                end = min(end + multiplier, self.ctrl.GetLastPosition())
            self.ctrl.Remove(start, end)
            self.ctrl.SetInsertionPoint(start)

    class TextCtrlBackspace(SelfInsertCommand):
        def actionKeystroke(self, evt, multiplier=1):
            start, end = self.ctrl.GetSelection()
            dprint("start=%d end=%d multiplier=%d" % (start, end, multiplier))
            if start == end:
                # If there's no selection, delete the number of characters requested
                start = max(start - multiplier, 0)
            self.ctrl.Remove(start, end)
            self.ctrl.SetInsertionPoint(start)

    class PrimaryMenu(object):
        def __init__(self, frame):
            self.frame = frame
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            self.frame.setPrimaryMenu()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)

    class AlternateMenu(object):
        def __init__(self, frame):
            self.frame = frame
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            self.frame.setAlternateMenu()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)

    class ShowKeyBindings(object):
        def __init__(self, frame):
            self.frame = frame
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            bindings = self.frame.root_accel.getKeyBindings()
            self.frame.ctrl.AddText(str(bindings))
            bindings = self.frame.root_accel.getUnboundActions()
            self.frame.ctrl.AddText(str(bindings))
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)
    
    class ExitDemo(object):
        def __init__(self, frame):
            self.frame = frame
        def actionWorksWithCurrentFocus(self):
            return True
        def action(self, index, multiplier=1, **kwargs):
            dprint()
            wx.GetApp().Exit()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier, **kwargs)
    
    
    class MainFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, "test")
            self.CreateStatusBar(2)
            self.SetStatusWidths([-1, 150])
            
            sizer = wx.BoxSizer(wx.VERTICAL)
            self.ctrl = wx.stc.StyledTextCtrl(self, -1)
            self.ctrl.CmdKeyClearAll()
            sizer.Add(self.ctrl, 0, wx.EXPAND)
            
            # ESC repeat works for TextCtrl, but not for STC
            self.text = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.WANTS_CHARS)
            self.text.SetFocus()

            sizer.Add(self.text, 0, wx.EXPAND)
            
            self.SetSizer(sizer)

            menuBar = wx.MenuBar()
            wx.MenuBar.SetAutoWindowMenu(False)
            self.SetMenuBar(menuBar)  # Adding empty sample menubar

            self.root_accel = AcceleratorManager()
            AcceleratorManager.debug = 1
            self.root_accel.manageFrame(self, self.ctrl, self.text)
            
            self.setPrimaryMenu()
            self.setToolbar()
            
            self.Show(True)

        def setPrimaryMenu(self):
            self.root_accel.cleanup()

            self.removeOldMenus()
            menuBar = self.GetMenuBar()
            gmap = wx.Menu()
            self.root_accel = AcceleratorManager("^X", "Ctrl-S", "Ctrl-TAB", "Ctrl-X Ctrl-S", "C-S C-A", "C-c C-c")
            
            self.menuAddM(menuBar, gmap, "File", "Global key map")
            self.menuAdd(gmap, "Open\tC-O", StatusUpdater)
            self.menuAdd(gmap, "Emacs Open\t^X ^F", StatusUpdater)
            self.menuAdd(gmap, "Not Quitting\tC-X C-Q", StatusUpdater)
            self.menuAdd(gmap, "Emacs M-ESC test\tM-ESC A", StatusUpdater)
            self.menuAdd(gmap, "Alternate Menu\t^a", AlternateMenu(self))
            self.menuAdd(gmap, "Test for hiding C-a\t^X ^A", StatusUpdater)
            self.menuAdd(gmap, "Exit\tC-Q", ExitDemo(self), wx.ID_EXIT)
            
            indexmap = wx.Menu()
            self.menuAddM(menuBar, indexmap, "&Help", "List of items")
            self.menuAdd(indexmap, "Item 1\t^X 1", StatusUpdater, index=0)
            self.menuAdd(indexmap, "Item 2\t^X 2", StatusUpdater, index=1)
            self.menuAdd(indexmap, "Item 3\t^X 3", StatusUpdater, index=2)
            self.menuAdd(indexmap, "Quote Next Character\tM-q", QuotedCharAction(self.root_accel))
            self.menuAdd(indexmap, "Show Key Bindings\tC-h b", ShowKeyBindings(self))
            self.menuAdd(indexmap, "Unmodified character in STC\tM", SelfInsertSTC(self, self.ctrl))
            wx.GetApp().SetMacHelpMenuTitleName("&Help")

            self.root_accel.addKeyBinding("DELETE", TextCtrlDelete(self, self.text), self.text)
            self.root_accel.addKeyBinding("BACK", TextCtrlBackspace(self, self.text), self.text)
            self.root_accel.addCancelKeyBinding("C-g", StatusUpdater(self, "Cancel"))
            self.root_accel.addCancelKeyBinding("M-ESC ESC", StatusUpdater(self, "Cancel"))
            self.root_accel.addDefaultKeyAction(SelfInsertSTC(self, self.ctrl), self.ctrl)
            self.root_accel.addDefaultKeyAction(SelfInsertText(self, self.text), self.text)
            
            dprint(self.root_accel)
            dprint(self)
            dprint(self.ctrl)
            self.root_accel.manageFrame(self, self.ctrl, self.text)
        
        def removeOldMenus(self):
            menubar = self.GetMenuBar()
            while menubar.GetMenuCount() > 0:
                old = menubar.Remove(0)
                old.Destroy()

        def setAlternateMenu(self):
            self.root_accel.cleanup()
            
            self.removeOldMenus()
            menuBar = self.GetMenuBar()
            gmap = wx.Menu()
            self.root_accel = AcceleratorManager("^X", "Ctrl-TAB", "Ctrl-X Ctrl-S", "C-x C-c")
            
            self.menuAddM(menuBar, gmap, "Alternate", "Global key map")
            self.menuAdd(gmap, "New\tC-N", StatusUpdater)
            self.menuAdd(gmap, "Open\tC-O", StatusUpdater)
            self.menuAdd(gmap, "Save\tC-S", StatusUpdater)
            self.menuAdd(gmap, "Primary Menu\tC-B", PrimaryMenu(self))
            self.menuAdd(gmap, "Exit\tC-Q", ExitDemo(self), wx.ID_EXIT)
            
            self.root_accel.addCancelKeyBinding("ESC", StatusUpdater(self, "Cancel"))
            self.root_accel.addKeyBinding("M-q", QuotedCharAction(self.root_accel))
            self.root_accel.addDefaultKeyAction(SelfInsertSTC(self, self.ctrl), self.ctrl)
            self.root_accel.addDefaultKeyAction(SelfInsertText(self, self.text), self.text)
            
            dprint(self.root_accel)
            self.root_accel.manageFrame(self, self.ctrl, self.text)
        
        def setToolbar(self):
            self.toolbar = self.CreateToolBar(wx.TB_HORIZONTAL)
            tsize = (16, 16)
            self.toolbar.SetToolBitmapSize(tsize)
            
            id = wx.NewId()
            bmp =  wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR, tsize)
            self.toolbar.AddLabelTool(id, "New", bmp, shortHelp="New", longHelp="Long help for 'New'")
            self.root_accel.addMenuItem(id, StatusUpdater(self, "Toolbar New"))
            
            id = wx.NewId()
            bmp =  wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, tsize)
            self.toolbar.AddLabelTool(id, "Open", bmp, shortHelp="Open", longHelp="Long help for 'Open'")
            self.root_accel.addMenuItem(id, StatusUpdater(self, "Toolbar Open"))
            
            # EVT_TOOL_ENTER and EVT_TOOR_RCLICKED don't work on OS X
            self.toolbar.Bind(wx.EVT_TOOL_ENTER, self.OnToolEnter)
            self.toolbar.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolContext)
            
            self.toolbar.Realize()
        
        def OnToolEnter(self, evt):
            # When a menu is opened, reset the accelerator level to the root
            # and cancel the current key sequence
            dprint("in OnToolEnter: id=%s" % evt.GetId())
            self.root_accel.cancelMultiKey()
            
        def OnToolContext(self, evt):
            # When a menu is opened, reset the accelerator level to the root
            # and cancel the current key sequence
            dprint("in OnToolContext: id=%s" % evt.GetId())
            
        def OnKeyDown(self, evt):
            self.LogKeyEvent("KeyDown", evt)
            evt.Skip()

        def OnKeyUp(self, evt):
            self.LogKeyEvent("KeyUp", evt)
            evt.Skip()

        def OnChar(self, evt):
            self.LogKeyEvent("Char", evt)
            evt.Skip()
                
        def LogKeyEvent(self, evType, evt):
            keycode = evt.GetKeyCode()
            keyname = wxkeycode_to_keyname.get(keycode, None)

            if keyname is None:
                if keycode < 256:
                    if keycode == 0:
                        keyname = "NUL"
                    elif keycode < 27:
                        keyname = "Ctrl-%s" % chr(ord('A') + keycode-1)
                    else:
                        keyname = "\"%s\"" % chr(keycode)
                else:
                    keyname = "(%s)" % keycode

            UniChr = ''
            if "unicode" in wx.PlatformInfo:
                UniChr = "\"" + unichr(evt.GetUnicodeKey()) + "\""
            
            modifiers = ""
            for mod, ch in [(evt.ControlDown(), 'C'),
                            (evt.AltDown(),     'A'),
                            (evt.ShiftDown(),   'S'),
                            (evt.MetaDown(),    'M')]:
                if mod:
                    modifiers += ch
                else:
                    modifiers += '-'
            
            dprint("%s: id=%d %s code=%s unicode=%s modifiers=%s" % (evType, evt.GetId(), keyname, keycode, repr(UniChr), modifiers))

        def menuAdd(self, menu, name, fcn, id=-1, kind=wx.ITEM_NORMAL, index=-1):
            def _spl(st):
                if '\t' in st:
                    return st.split('\t', 1)
                return st, ''

            ns, acc = _spl(name)
            if fcn == StatusUpdater:
                fcn = StatusUpdater(self, ns)

            if acc:
                acc=acc.replace('\t',' ')
                #print "acc=%s" % acc
                
                # The "append ascii zero to the end of the accelerator" trick
                # no longer works for windows, so use the same hack below for
                # all platforms.

                # wx doesn't allow displaying arbitrary text as the
                # accelerator, so we have format it according to what's
                # allowed by the current platform.  Emacs style multi-
                # keystroke bindings are not right-aligned, unfortunately.
                acc_text = KeyAccelerator.getAcceleratorText(acc)
                label = "%s%s" % (ns, acc_text)
                
                self.root_accel.addKeyBinding(acc, fcn)
            else:
                label = ns
            
            if id == -1:
                id = wx.NewId()
            self.root_accel.addMenuItem(id, fcn, index)
            
            a = wx.MenuItem(menu, id, label, name, kind)
            menu.AppendItem(a)

        def menuAddM(self, parent, menu, name, help=''):
            if isinstance(parent, wx.Menu):
                id = wx.NewId()
                parent.AppendMenu(id, "TEMPORARYNAME", menu, help)

                self.menuBar.SetLabel(id, name)
                self.menuBar.SetHelpString(id, help)
            else:
                parent.Append(menu, name)
    
    def run():
        app = wx.PySimpleApp(redirect=False)
        frame = MainFrame()
        app.MainLoop()
    
    def test():
        keys = (
            ["C-x", [(wx.ACCEL_CTRL, "X")]],
            ["C-y", [(wx.ACCEL_CTRL, "Y")]],
            ["BACK", [(wx.ACCEL_NORMAL, wx.WXK_BACK)]],
            ["C-BACK", [(wx.ACCEL_CTRL, wx.WXK_BACK)]],
            ["S-C-BACK", [(wx.ACCEL_CTRL|wx.ACCEL_SHIFT, wx.WXK_BACK)]],
            ["M-ESC ESC", [(wx.ACCEL_ALT, wx.WXK_ESCAPE), (wx.ACCEL_NORMAL, wx.WXK_ESCAPE)]],
            ["1", [(wx.ACCEL_NORMAL, ord("1"))]],
            ["a", [(wx.ACCEL_NORMAL, ord("A"))]],
            ["A", [(wx.ACCEL_NORMAL, ord("A"))]],
            ["c", [(wx.ACCEL_NORMAL, ord("C"))]],
            ["C", [(wx.ACCEL_NORMAL, ord("C"))]],
            ["C-c", [(wx.ACCEL_CTRL, ord("C"))]],
            ["C-C", [(wx.ACCEL_CTRL, ord("C"))]],
            ["^C", [(wx.ACCEL_CTRL, ord("C"))]],
            ["Ctrl-c", [(wx.ACCEL_CTRL, ord("C"))]],
            ["Ctrl-C", [(wx.ACCEL_CTRL, ord("C"))]],
            ["Ctrl+c", [(wx.ACCEL_CTRL, ord("C"))]],
            ["Ctrl+C", [(wx.ACCEL_CTRL, ord("C"))]],
            ["C-x 5 2", [(wx.ACCEL_CTRL, ord("X")), (wx.ACCEL_NORMAL, ord("5")), (wx.ACCEL_NORMAL, ord("2"))]],
            ["C-x C-b C-M-S-p", [(wx.ACCEL_CTRL, ord("X")), (wx.ACCEL_CTRL, ord("B")), (wx.ACCEL_CTRL|wx.ACCEL_ALT|wx.ACCEL_SHIFT, ord("P")), ]],
            )
        
        errors = 0
        for key_binding, expected_keystrokes in keys:
            calculated_keystrokes = KeyAccelerator.split(key_binding)
            for calculated, expected_def in zip(calculated_keystrokes, expected_keystrokes):
                expected = Keystroke.find(expected_def[0], expected_def[1])
                if expected != calculated:
                    dprint("ERROR: expected <%s> != calculated <%s>" % (expected, calculated))
                    errors += 1
                else:
                    dprint("works: expected <%s> == calculated <%s>" % (expected, calculated))
        
        dprint("errors = %d" % errors)
            

    try:
        index = sys.argv.index("-p")
        import cProfile
        cProfile.run('run()','profile.out')
    except ValueError:
        test()
        run()

