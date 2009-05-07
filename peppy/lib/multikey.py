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
import wx

from peppy.debug import *

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
for keyname in ['SHIFT', 'CONTROL', 'ALT', 'COMMAND']:
    ignore_modifiers[wxkeyname_to_keycode[keyname]] = True
dprint(ignore_modifiers)

# Aliases for WXK_ names
keyaliases={'RET':'RETURN',
            'SPC':'SPACE',
            'ESC':'ESCAPE',
            }


if wx.Platform == '__WXMAC__':
    # Note that WXMAC needs Command to appear as Ctrl- in the accelerator
    # text.  It converts Ctrl into the command symbol.  Note that there is no
    # mapping for the C- prefix because wx doesn't have the ability to put a
    # Control character in a menu.
    usable_modifiers = [wx.ACCEL_CTRL, wx.ACCEL_ALT, wx.ACCEL_SHIFT, wx.ACCEL_CMD]
    emacs_modifiers = {
        wx.ACCEL_CMD: 'C-',
        wx.ACCEL_CTRL: '^-',
        wx.ACCEL_SHIFT: 'S-',
        wx.ACCEL_ALT: 'M-',
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
    def __init__(self, flags, key):
        self.flags = flags
        self.key = key
        self.keycode = self.getKeycode(key)
        self.id = wx.NewId()
    
    def getKeycode(self, key):
        try:
            code = wxkeyname_to_keycode[key]
        except KeyError:
            code = ord(key)
        return code
    
    def getMenuAccelerator(self):
        mod = self.getMenuModifiers()
        return mod + self.key

    def getMenuModifiers(self):
        mods = ""
        for bit in usable_modifiers:
            if self.flags & bit:
                mods += menu_modifiers[bit]
        return mods
    
    def getEmacsAccelerator(self):
        mod = self.getEmacsModifiers()
        return mod + self.key

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
            return keystrokes
    
    @classmethod
    def normalizeAccelerators(cls, acc):
        # find the individual keystrokes from a more emacs style
        # list, where the keystrokes are separated by whitespace.
        normalized = []
        i = 0
        while i<len(acc):
            while acc[i].isspace() and i < len(acc): i += 1

            flags = 0
            j = i
            while j < len(acc):
                chars, bit = cls.matchModifier(acc[j:])
                if bit:
                    j += chars
                    flags |= bit
                else:
                    break
            #if cls.debug: print "modifiers found: '%s'  remaining='%s'" % (cls.getEmacsModifiers(flags), acc[j:])
            
            chars, key = cls.matchKey(acc[j:])
            if key is not None:
                if cls.debug: dprint("key found: %s, chars=%d" % (key, chars))
                normalized.append((flags, key))
            else:
                if cls.debug: dprint("unknown key %s" % acc[j:j+chars])
            if j + chars < len(acc):
                if cls.debug: dprint("remaining='%s'" % acc[j+chars:])
            i = j + chars
        if cls.debug: dprint("keystrokes: %s" % normalized)
        return normalized
    
    @classmethod
    def getKeystrokes(cls, normalized):
        keystrokes = []
        for key in normalized:
            try:
                keystroke = cls.normalized_keystroke_cache[key]
                if cls.debug: dprint("Found cached keystroke %s" % keystroke.getEmacsAccelerator())
            except KeyError:
                keystroke = Keystroke(key[0], key[1])
                if cls.debug: dprint("Created and cached keystroke %s" % keystroke.getEmacsAccelerator())
                cls.normalized_keystroke_cache[key] = keystroke
            keystrokes.append(keystroke)
        return tuple(keystrokes)

    @classmethod
    def matchModifier(cls, str):
        """Find a modifier in the accelerator string
        """        
        for m in modifier_alias.keys():
            if str.startswith(m):
                return len(m), modifier_alias[m]
        return 0, None

    @classmethod
    def matchKey(cls, text):
        """Find a keyname (not modifier name) in the accelerator
        string, matching any special keys or abbreviations of the
        special keys
        """
        text = text.upper()
        key = None
        i = 0
        for name in keyaliases:
            if text.startswith(name):
                val = keyaliases[name]
                if text.startswith(val):
                    return i+len(val), val
                else:
                    return i+len(name), val
        for name in wxkeynames:
            if text.startswith(name):
                return i+len(name), name
        if i<len(text) and not text[i].isspace():
            return i+1, text[i].upper()
        return i, None

    @classmethod
    def getEmacsAccelerator(cls, keystrokes):
        keys = []
        for keystroke in keystrokes:
            keys.append(keystroke.getEmacsAccelerator())
        return " ".join(keys)

    @classmethod
    def matchPlatformModifier(cls, str):
        """Find a modifier in the accelerator string
        """        
        for m in modaccelerator.keys():
            if str.startswith(m):
                return len(m),modaccelerator[m]
        return 0,None

    @classmethod
    def getAcceleratorText(cls, key_sequence, force_emacs=False):
        keystrokes = cls.split(key_sequence)
        if len(keystrokes) == 1 and not force_emacs:
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
    esc_keystroke = KeyAccelerator.split("ESC")[0]
    meta_esc_keystroke = KeyAccelerator.split("M-ESC")[0]
    
    digit_value = {}
    meta_digit_keystroke = {}
    plain_digit_keystroke = {}
    digit_keycode = {}
    for i in range(10):
        keystroke = KeyAccelerator.split("M-%d" % i)[0]
        meta_digit_keystroke[keystroke.id] = keystroke
        digit_value[keystroke.id] = i
        keystroke = KeyAccelerator.split("%d" % i)[0]
        plain_digit_keystroke[keystroke.id] = keystroke
        digit_value[keystroke.id] = i
        digit_keycode[keystroke.keycode] = i
    
    def __init__(self, *args, **kwargs):
        if 'frame' in kwargs:
            self.frame = kwargs['frame']
        if 'root' in kwargs:
            self.root = kwargs['root']
        else:
            if not hasattr(self, 'frame'):
                raise KeyError('Root level needs wx.Frame instance')
            
            # Root also needs several extra variables to keep track of
            self.root = self
            
            # The root keeps track of the current level that is another
            # instance of AcceleratorList from the id_next_level map
            self.current_level = None
            
            self.meta_next = False
            self.processing_esc_digit = False
            self.pending_cancel_key_registration = []
            self.current_keystrokes = []
        
        # Cached value of wx.AcceleratorTable; will be regenerated
        # automatically by getTable if set to None
        self.accelerator_table = None
        
        # Flag to indicate that the next keystroke should be ignored.  This is
        # needed because no OnMenu event is generated when a keystroke doesn't
        # exist in the translation table.
        self.skip_next = False
        
        # Map of ID to keystroke for the current level
        self.id_to_keystroke = {}
        
        # Map of all IDs that have additional keystrokes, used in multi-key
        # processing.
        self.id_next_level = {}
        
        # Map of all keystroke IDs in this level to actions
        self.keystroke_id_to_action = {}
        
        # Map of all menu IDs in this level to actions
        self.menu_id_to_action = {}
        
        # If the menu id has an index, i.e.  it's part of a list or radio
        # button group, the index of the id is stored in this map
        self.menu_id_to_index = {}
        
        # Map used to quickly identify all valid keystrokes at this level
        self.valid_keystrokes = {}
        
        # Always have an ESC keybinding for emacs-style ESC-as-sticky-meta
        # processing
        self.addKeyBinding("ESC")
        for arg in args:
            dprint(str(arg))
            self.addKeyBinding(arg)
        
        # Special keybindings for the root level
        if self.root == self:
            for i in range(10):
                self.addKeyBinding("M-%d" % i)
                self.addKeyBinding("ESC %d" % i)
            self.resetRoot()
    
    def __str__(self):
        return self.getPrettyStr()
    
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
    
    def addKeyBinding(self, key_binding, action=None):
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
                self._addKeyBinding(key_binding_entry, action)
        else:
            self._addKeyBinding(key_binding, action)
    
    def _addKeyBinding(self, key_binding, action=None):
        keystrokes = list(KeyAccelerator.split(key_binding))
        keystrokes.append(None)
        current = self
        for keystroke, next_keystroke in zip(keystrokes, keystrokes[1:]):
            current.id_to_keystroke[keystroke.id] = keystroke
            current.valid_keystrokes[(keystroke.flags, keystroke.keycode)] = True
            if next_keystroke is None:
                current.keystroke_id_to_action[keystroke.id] = action
            else:
                try:
                    current = current.id_next_level[keystroke.id]
                except KeyError:
                    accel_list = AcceleratorList(root=self.root)
                    current.id_next_level[keystroke.id] = accel_list
                    current = accel_list
        self.accelerator_table = None
        
    def addMenuItem(self, id, action=None, index=-1):
        """Add a menu item that doesn't have an equivalent keystroke.
        
        Note that even if a menu item has a keystroke and that keystroke has
        been added to the list using L{addKeyBinding}, this method still needs
        to be called because the menu item ID is different from the keystroke
        ID.
        
        @param id: wx ID of the menu item
        """
        if self.root != self:
            raise RuntimeError("Menu actions can only be added to the root level accelerators")
        self.menu_id_to_action[id] = action
        if index >= 0:
            dprint("Adding index %d to %d, %s" % (index, id, str(action)))
            self.menu_id_to_index[id] = index
        self.accelerator_table = None
    
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
        # new keybindings the first time getTable is called.
        self.root.pending_cancel_key_registration.append((key_binding, action))
    
    def addCancelKeys(self):
        """Add cancel keys to all keybinding levels
        
        """
        for key_binding, action in self.root.pending_cancel_key_registration:
            dprint("Adding cancel key %s" % key_binding)
            self.root.addCancelKeysToLevels(key_binding, action)
        self.root.pending_cancel_key_registration = []
    
    def addCancelKeysToLevels(self, key_binding, action):
        """Recursive function to add the cancel keybinding to the current level
        and all sub levels
        """
        for accel_list in self.id_next_level.values():
            accel_list.addCancelKeysToLevels(key_binding, action)
            
            # Reset the accelerator table flag to force its regeneration
            accel_list.accelerator_table = None
        self.addKeyBinding(key_binding, action)
    
    def getTable(self):
        """Returns a L{wx.AcceleratorTable} that corresponds to the key bindings
        in the current level.
        """
        if self.root.pending_cancel_key_registration:
            self.root.addCancelKeys()
        if self.accelerator_table is None:
            table = []
            for keystroke in self.id_to_keystroke.values():
                table.append(keystroke.getAcceleratorTableEntry())
            dprint("AcceleratorTable: %s" % str(table))
            self.accelerator_table = wx.AcceleratorTable(table)
        return self.accelerator_table
    
    def setAcceleratorTable(self, level=None):
        if level is None:
            level = self.root
        if self.root.current_level != level:
            self.root.current_level = level
            self.root.frame.SetAcceleratorTable(level.getTable())
    
    def processKeyDownEvent(self, evt):
        """Helper event processing loop to be called from the Frame's
        EVT_KEY_DOWN callback.
        
        This is needed because there's no other way to cancel a bad multi-key
        keystroke.  EVT_MENU won't be called at all on an unrecognized
        keystroke but EVT_KEY_DOWN will will always be called, so we use this
        to preemptively check to see if the keystroke will be accepted or not
        and set appropriate flags for later use.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        if self.root.meta_next and self.root.current_level == self.root:
            # digit processing is only available at the root level
            
            dprint("char: %d" % evt.GetKeyCode())
            if evt.GetKeyCode() in self.digit_keycode:
                # digit processing after the ESC key is available in a special
                # sublevel of ESC.  If digits are instead included in the root
                # level, the digits will never get sent to the application's
                # OnChar event because they'll be processed by the root
                # accelerator table
                self.setAcceleratorTable(self.id_next_level[self.esc_keystroke.id])
                self.root.meta_next = False
                self.root.processing_esc_digit = True
            else:
                # If we run into anything else while we're processing a digit
                # string, stop the digit processing and reset the accelerator
                # table to the root
                self.setAcceleratorTable()
                self.root.processing_esc_digit = False
        elif self.root.processing_esc_digit and evt.GetKeyCode() not in self.digit_keycode:
            # A non-digit character during digit processing will reset the
            # accelerator table back to the root so we can then find out the
            # command to which the digits will be applied.
            self.processing_esc_digit = False
            self.setAcceleratorTable()
            
            
        if not self.root.current_level.isValidAccelerator(evt):
            # If the keystroke isn't valid for the current level but would
            # be recognized by the root level, we have to skip it because
            # we're about to reset the current level to the root level and
            # the keystroke would be processed by the root level
            if self.root.isValidAccelerator(evt):
                self.root.skipNext()
            else:
                self.root.reset()

            # OnMenu event will never get generated if it doesn't appear in
            # the accelerator table, so reset the accelerator table to the
            # root table
            dprint("Unknown accelerator; resetting to root")
            if self.root.current_level != self.root:
                self.setAcceleratorTable()

    def processMenuEvent(self, evt):
        """Main event processing loop to be called from the Frame's EVT_MENU
        callback.
        
        This method is designed to be called from the root level as it
        redirects the event processing to the current keystroke level.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        self.root.current_level.processEvent(evt)

    def processEvent(self, evt):
        """Main processing loop used on the current keystroke level.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        if self.skip_next:
            # The incoming character has been already marked as being bad by a
            # KeyDown event, so we should't process it.
            dprint("in processEvent: skipping incoming char marked as bad by OnKeyDown")
            self.skip_next = False
        else:
            eid = evt.GetId()
            if eid in self.menu_id_to_action:
                self.foundMenuAction(evt)
            elif eid in self.id_to_keystroke:
                self.foundKeyAction(evt)
            else:
                dprint("in processEvent: evt=%s id=%s not found in this level" % (str(evt.__class__), eid))
                self.reset()
    
    def foundMenuAction(self, evt):
        """Fire off an action found in menu item or toolbar item list
        """
        eid = evt.GetId()
        self.resetMenuSuccess()
        action = self.menu_id_to_action[eid]
        if action is not None:
            try:
                index = self.menu_id_to_index[eid]
            except KeyError:
                index = -1
            dprint("evt=%s id=%s index=%d repeat=%s FOUND MENU ACTION %s" % (str(evt.__class__), eid, index, self.root.repeat_value, self.menu_id_to_action[eid]))
            action.action(index, self.root.repeat_value)
        else:
            dprint("evt=%s id=%s repeat=%s FOUND MENU ACTION NONE" % (str(evt.__class__), eid, index, self.root.repeat_value))
    
    def foundKeyAction(self, evt):
        eid = evt.GetId()
        keystroke = self.id_to_keystroke[eid]
        
        if eid == self.esc_keystroke.id:
            if self.root.meta_next:
                keystroke = self.meta_esc_keystroke
                eid = keystroke.id
                self.root.meta_next = False
                self.root.current_keystrokes.pop()
                dprint("in processEvent: evt=%s id=%s FOUND M-ESC" % (str(evt.__class__), eid))
            elif self.root.current_keystrokes and self.root.current_keystrokes[-1] == self.meta_esc_keystroke:
                # M-ESC ESC is processed as a regular keystroke
                dprint("in processEvent: evt=%s id=%s FOUND M-ESC ESC" % (str(evt.__class__), eid))
                pass
            else:
                dprint("in processEvent: evt=%s id=%s FOUND ESC" % (str(evt.__class__), eid))
                self.root.meta_next = True
                self.displayCurrentKeystroke(keystroke)
                return
        elif eid in self.meta_digit_keystroke:
            self.displayCurrentKeystroke(keystroke)
            if self.root.repeat_value is None:
                self.root.repeat_value = self.digit_value[eid]
            else:
                self.root.repeat_value = 10 * self.root.repeat_value + self.digit_value[eid]
            dprint("in processEvent: evt=%s id=%s FOUND REPEAT %d" % (str(evt.__class__), eid, self.root.repeat_value))
            return
        elif eid in self.plain_digit_keystroke:
            self.displayCurrentKeystroke(keystroke)
            if self.root.repeat_value is None:
                self.root.repeat_value = self.digit_value[eid]
            else:
                self.root.repeat_value = 10 * self.root.repeat_value + self.digit_value[eid]
            dprint("in processEvent: evt=%s id=%s FOUND REPEAT %d" % (str(evt.__class__), eid, self.root.repeat_value))
            return
            
        self.displayCurrentKeystroke(keystroke)
        if eid in self.id_next_level:
            dprint("in processEvent: evt=%s id=%s FOUND MULTI-KEYSTROKE" % (str(evt.__class__), eid))
            self.setAcceleratorTable(self.id_next_level[eid])
        else:
            dprint("in processEvent: evt=%s id=%s FOUND ACTION %s repeat=%s" % (str(evt.__class__), eid, self.keystroke_id_to_action[eid], self.root.repeat_value))
            self.resetKeyboardSuccess()
            action = self.keystroke_id_to_action[eid]
            if action is not None:
                action.actionKeystroke(evt, multiplier=self.root.repeat_value)
            self.setAcceleratorTable()
    
    def displayCurrentKeystroke(self, keystroke):
        """Add the keystroke to the list of keystrokes displayed in the status
        bar as the user is typing.
        """
        self.root.current_keystrokes.append(keystroke)
        text = KeyAccelerator.getEmacsAccelerator(self.root.current_keystrokes)
        self.root.frame.SetStatusText(text)
    
    def cancelMultiKey(self):
        if self.root.current_level != self.root:
            self.reset("Cancelled multi-key keystroke")
            
    def reset(self, message=""):
        self.resetRoot()
        self.root.frame.SetStatusText(message)
        self.setAcceleratorTable()
    
    def resetRoot(self):
        self.root.meta_next = False
        self.root.repeat_value = None
        self.root.current_keystrokes = []
    
    def resetKeyboardSuccess(self):
        self.resetRoot()
    
    def resetMenuSuccess(self):
        self.resetRoot()
    
    def skipNext(self):
        self.skip_next = True
        self.reset()
    
    def isValidAccelerator(self, evt):
        key = (evt.GetModifiers(), evt.GetKeyCode())
        return key in self.valid_keystrokes or evt.GetKeyCode() in ignore_modifiers
    
    def isModifierOnly(self, evt):
        return evt.GetKeyCode() in ignore_modifiers



if __name__ == '__main__':
    class StatusUpdater:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def action(self, index, multiplier=-1, **kwargs):
            if multiplier is not None:
                self.frame.SetStatusText("%d x %s" % (multiplier, self.message))
            else:
                self.frame.SetStatusText(self.message)
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)

    #The frame with hotkey chaining.

    class MainFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, "test")
            self.CreateStatusBar()
            self.ctrl = self.ctrl = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.WANTS_CHARS|wx.TE_RICH2)
            self.ctrl.SetFocus()

            self.setMenu()
            self.setToolbar()

        def setMenu(self):
            menuBar = wx.MenuBar()
            self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
            self.menuBar = menuBar
            
            gmap = wx.Menu()
            self.root_accel = AcceleratorList("^X", "Ctrl-S", "Ctrl-TAB", "Ctrl-X Ctrl-S", "C-S C-A", "C-c C-c", frame=self)
            
            self.menuAddM(menuBar, gmap, "Global", "Global key map")
            self.menuAdd(gmap, "Open\tC-O", StatusUpdater)
            self.menuAdd(gmap, "Emacs Open\tC-X C-F", StatusUpdater)
            self.menuAdd(gmap, "Not Quitting\tC-X C-Q", StatusUpdater)
            self.menuAdd(gmap, "Emacs M-ESC test\tM-ESC A", StatusUpdater)
            self.menuAdd(gmap, "Exit\tC-Q", sys.exit)
            
            indexmap = wx.Menu()
            self.menuAddM(menuBar, indexmap, "List", "List of items")
            self.menuAdd(indexmap, "Item 1\tC-X 1", StatusUpdater, index=0)
            self.menuAdd(indexmap, "Item 2\tC-X 2", StatusUpdater, index=1)
            self.menuAdd(indexmap, "Item 3\tC-X 3", StatusUpdater, index=2)

            self.root_accel.addCancelKeyBinding("C-g", StatusUpdater(self, "Cancel"))
            self.root_accel.addCancelKeyBinding("M-ESC ESC", StatusUpdater(self, "Cancel"))
            
            self.root_accel.setAcceleratorTable()
            dprint(self.root_accel)
            
            self.Bind(wx.EVT_MENU, self.OnMenu)
            self.Bind(wx.EVT_MENU_OPEN, self.OnMenuOpen)
            self.ctrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            #self.ctrl.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
            self.Show(1)
        
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
        
        def OnMenu(self, evt):
            eid = evt.GetId()
            dprint("in OnMenu: id=%s" % eid)
            self.root_accel.processMenuEvent(evt)
            
        def OnMenuOpen(self, evt):
            # When a menu is opened, reset the accelerator level to the root
            # and cancel the current key sequence
            dprint("in OnMenuOpen: id=%s" % evt.GetId())
            self.root_accel.cancelMultiKey()
            
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
            self.root_accel.processKeyDownEvent(evt)
                
            evt.Skip()

        def OnKeyUp(self, evt):
            self.LogKeyEvent("KeyUp", evt)
            evt.Skip()

        def OnChar(self, evt):
            self.LogKeyEvent("KeyDown", evt)
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

            modifiers = ""
            for mod, ch in [(evt.ControlDown(), 'C'),
                            (evt.AltDown(),     'A'),
                            (evt.ShiftDown(),   'S'),
                            (evt.MetaDown(),    'M')]:
                if mod:
                    modifiers += ch
                else:
                    modifiers += '-'
            
            dprint("%s: id=%d %s code=%s modifiers=%s" % (evType, evt.GetId(), keyname, keycode, modifiers))

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
                
                # If the menu item has a single keystroke that will be placed
                # in the menu item's text, we need to use the same id for the
                # menu as is used for the keystroke.  If we don't do this, a
                # multi key sequence that uses the character from this event
                # as the 2nd or later character won't get the proper event.
                # I.e.  if there's a menu item "Ctrl-Q" and a multi key "C-x
                # C-q", the "C-x C-q" multi-key will never get called because
                # the event for "Ctrl-Q" will get returned instead of the id
                # for "C-q"
                keystrokes = KeyAccelerator.split(acc)
                if len(keystrokes) == 1:
                    id = keystrokes[0].id
                
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
    
    app = wx.PySimpleApp(redirect=False)
    frame = MainFrame()
    app.MainLoop()
