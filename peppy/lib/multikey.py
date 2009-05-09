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
for keyname in ['SHIFT', 'CONTROL', 'ALT', 'COMMAND', 'CAPITAL', 'NUMLOCK', 'SCROLL']:
    ignore_modifiers[wxkeyname_to_keycode[keyname]] = True
dprint(ignore_modifiers)

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
            if keycode >= ord('a') and keycode <= ord('z'):
                keycode -= 32
            keyname = unichr(keycode)
        return keyname
    
    @classmethod
    def getTextFromKeyCode(cls, keycode):
        # If the keycode is ASCII, normalize it to a capital letter
        if keycode >= ord('a') and keycode <= ord('z'):
            keycode -= 32
        dprint(keycode)
        return unichr(keycode)
    
    def getMenuAccelerator(self):
        mod = self.getMenuModifiers()
        return mod + self.key
    
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



class FakeQuotedCharEvent(object):
    def __init__(self, event_object, keystroke, id=None, evt=None):
        self.evt = evt
        if id is None:
            self.id = -1
        else:
            self.id = keystroke.id
        self.modifiers = keystroke.flags
        self.keycode = keystroke.keycode
        self.event_object = event_object
    
    def GetEventObject(self):
        return self.event_object
    
    def GetId(self):
        return self.id
    
    def GetModifiers(self):
        return self.modifiers
    
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
    
    def GetKeyCode(self):
        return self.keycode
    
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
        self.multiplier = 1
        self.last_keycode = None
    
    def actionKeystroke(self, evt, multiplier=1):
        self.multiplier = multiplier
        dprint("Saving multiplier=%d" % multiplier)
        self.accel.setQuotedNext(self)
    
    def getMultiplier(self):
        return self.multiplier
    
    def copyLastEvent(self, evt):
        self.last_event = FakeQuotedCharEvent(evt.GetEventObject())
    
    def getLastEvent(self):
        return self.last_event


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
            
    def __init__(self):
        # Map of ID to keystroke for the current level
        self.id_to_keystroke = {}
        
        # Map of all IDs that have additional keystrokes, used in multi-key
        # processing.
        self.id_next_level = {}
        
        # Map of all keystroke IDs in this level to actions
        self.keystroke_id_to_action = {}
        
        # Map used to quickly identify all valid keystrokes at this level
        self.valid_keystrokes = {}
        
    def __str__(self):
        return self.getPrettyStr()
    
    def __del__(self):
        print("deleting %s" % (repr(self), ))
    
    
    def cleanSubLevels(self):
        """Recursive function to remove all references to the root object
        """
        self.current_level = None
        for accel_list in self.id_next_level.values():
            accel_list.cleanSubLevels()
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
                    accel_list = AcceleratorList()
                    current.id_next_level[keystroke.id] = accel_list
                    current = accel_list
        self.accelerator_table = None
        
    def addCancelKeysToLevels(self, key_binding, action):
        """Recursive function to add the cancel keybinding to the current level
        and all sub levels
        """
        for accel_list in self.id_next_level.values():
            accel_list.addCancelKeysToLevels(key_binding, action)
            
            # Reset the accelerator table flag to force its regeneration
            accel_list.accelerator_table = None
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
        
        self.blank_quoted_level = None
    
        # Repeat values
        self.repeat_initialized = False
        self.repeat_value = 1

    def processChar(self, evt, manager):
        dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), self.repeat_value, evt.GetId()))
        if self.quoted_next:
            # Short circuit this character so that it isn't processed
            self.repeat_value = self.quoted_next.getMultiplier()
            dprint("Processing quoted character, multiplier=%s" % self.repeat_value)
            #
            manager.frame.SetStatusText("")
        elif not manager.isRoot() and not self.processing_esc_digit:
            # If we get an unhandled keystroke after a multi-key sequence, we
            # ignore it as a bad key combination.
            raise UnknownKeySequence
        eid = evt.GetId()
        dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), self.repeat_value, eid))
    
    def processEscDigit(self, keystroke):
        if not self.repeat_initialized:
            self.repeat_value = AcceleratorList.digit_value[keystroke.id]
            self.repeat_initialized = True
        else:
            self.repeat_value = 10 * self.repeat_value + AcceleratorList.digit_value[keystroke.id]
        dprint("in processEscDigit: FOUND REPEAT %d" % self.repeat_value)



class AcceleratorManager(AcceleratorList):
    """Driver class for multi-keystroke processing of CommandEvents.
    
    This class creates nested accelerator tables for processing multi-keystroke
    commands.  The tables are switched in and out dynamically as key events
    come into the L{processEvent} method.  Menu actions are also handled here.
    If the user selects a menu item, any in-progress multi-key sequence is
    cancelled.
    """
    # Blank level used in quoted character processing
    def __init__(self, *args, **kwargs):
        AcceleratorList.__init__(self)
        
        # The root keeps track of the current level that is another
        # instance of AcceleratorList from the id_next_level map
        self.current_level = None
        
        # Map of all menu IDs to actions.  Note that menu actions only occur
        # in the root level because wx doesn't allow multi-key actions in the
        # menu bar.  If they did, we wouldn't need this hackery!!!
        self.menu_id_to_action = {}
        
        # If the menu id has an index, i.e.  it's part of a list or radio
        # button group, the index of the id is stored in this map
        self.menu_id_to_index = {}
        
        # Default keystroke action when nothing else is matched
        self.default_key_action = None
        
        self.pending_cancel_key_registration = []

        self.bound_controls = []
        
        self.current_target = None

        self.entry = CurrentKeystrokes()
        
        # Flag to indicate that the next keystroke should be ignored.  This is
        # needed because no OnMenu event is generated when a keystroke doesn't
        # exist in the translation table.
        self.skip_next = False

        # Always have an ESC keybinding for emacs-style ESC-as-sticky-meta
        # processing
        self.addKeyBinding("ESC")
        for arg in args:
            dprint(str(arg))
            self.addKeyBinding(arg)
        
        for i in range(10):
            self.addKeyBinding("M-%d" % i)
            self.addKeyBinding("ESC %d" % i)
    
    def __del__(self):
        print("deleting %s" % (repr(self), ))
    
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
        wx.CallAfter(self.cleanSubLevels)
    
    def addDefaultKeyAction(self, action):
        """If no other action is matched, this action is used.
        
        """
        self.default_key_action = action
    
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
            dprint("Adding index %d to %d, %s" % (index, id, str(action)))
            self.menu_id_to_index[id] = index
    
    def addQuotedCharKeyBinding(self, key_binding):
        """Add a quoted character key binding.
        
        A quoted character key binding allows the next character typed after
        the quoted character to be inserted in raw form without processing by
        the action handler.
        
        Quoted character key bindings are only valid at the root level.
        
        @param key_binding: text string representing the keystroke(s) to
        trigger the action.
        """
        self.addKeyBinding(key_binding, QuotedCharAction(self))
    
    def setQuotedNext(self, callback):
        """Set the quoted character callback
        
        When this is set, the next character typed will be passed verbatim to
        the default character action specified by L{addDefaultKeyAction}.
        """
        # Remove all accelerators temporarily so we can get all keystrokes
        # without the OnMenu callback interfering
        self.entry.quoted_next = callback
        dprint("Setting empty accelerator table")
    
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
        for key_binding, action in self.pending_cancel_key_registration:
            dprint("Adding cancel key %s" % key_binding)
            self.addCancelKeysToLevels(key_binding, action)
        self.pending_cancel_key_registration = []
    
    def isRoot(self):
        return self.current_level == self
    
    def bindEvents(self, frame, *ctrls):
        """Initialization function to create all necessary event bindings
        between the frame and the managed controls.
        
        """
        if self.pending_cancel_key_registration:
            self.addCancelKeys()
        self.frame = frame
        frame.Bind(wx.EVT_MENU, self.OnMenu)
        frame.Bind(wx.EVT_MENU_CLOSE, self.OnMenuClose)
        frame.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        for ctrl in ctrls:
            self.bound_controls.append(ctrl)
            ctrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            ctrl.Bind(wx.EVT_CHAR, self.OnChar)
            ctrl.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.current_level = self
        self.current_target = frame.FindFocus()
        
    def unbindEvents(self):
        """Cleanup function to remove event bindings
        
        """
        self.frame.Unbind(wx.EVT_MENU)
        self.frame.Unbind(wx.EVT_MENU_CLOSE)
        self.frame.Unbind(wx.EVT_CHAR_HOOK)
        for ctrl in self.bound_controls:
            ctrl.Unbind(wx.EVT_KEY_DOWN)
            ctrl.Unbind(wx.EVT_CHAR)
            ctrl.Unbind(wx.EVT_SET_FOCUS)
        self.bound_controls = []
        self.frame = None
    
    def OnSetFocus(self, evt):
        dprint("Setting focus to %s" % evt.GetEventObject())
        self.cancelMultiKey()
        self.current_target = evt.GetEventObject()
        evt.Skip()
        
    def OnCharHook(self, evt):
        """Character event processor that handles everything not recognized
        by the menu or keyboard events.
        """
        dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), self.entry.repeat_value, evt.GetId()))
        evt.Skip()
        
    def OnChar(self, evt):
        """Character event processor that handles everything not recognized
        by the menu or keyboard events.
        """
        try:
            self.entry.processChar(evt, self)
        except UnknownKeySequence:
            self.reset("Unknown multi-key sequence")
            return
            
        self.default_key_action.actionKeystroke(evt, multiplier=self.entry.repeat_value)
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
        dprint("char=%s, unichar=%s, multiplier=%d, id=%s" % (keycode, evt.GetUnicodeKey(), self.entry.repeat_value, eid))
        if self.entry.quoted_next:
            dprint("Quoted next; skipping OnKeyDown to be processed by OnChar")
            evt.Skip()
            return
        
        keystroke = KeyAccelerator.getKeystroke((evt.GetModifiers(), keycode))
        dprint(keystroke)
        if keystroke.isModifierOnly():
            evt.Skip()
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
            evt.Skip()
    
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
                dprint("in processEvent: evt=%s id=%s FOUND M-ESC" % (str(evt.__class__), eid))
            elif self.entry.current_keystrokes and self.entry.current_keystrokes[-1] == self.meta_esc_keystroke:
                # M-ESC ESC is processed as a regular keystroke
                dprint("in processEvent: evt=%s id=%s FOUND M-ESC ESC" % (str(evt.__class__), eid))
                pass
            else:
                dprint("in processEvent: evt=%s id=%s FOUND ESC" % (str(evt.__class__), eid))
                self.entry.meta_next = True
                self.displayCurrentKeystroke(keystroke)
                return True, keystroke
        elif eid in self.meta_digit_keystroke:
            self.entry.processEscDigit(keystroke)
            self.displayCurrentKeystroke(keystroke)
            return True, keystroke
        elif (self.entry.meta_next or self.entry.processing_esc_digit) and eid in self.plain_digit_keystroke:
            dprint("After ESC, found digit char: %d" % evt.GetKeyCode())
            self.entry.meta_next = False
            self.entry.processing_esc_digit = True
            self.entry.processEscDigit(keystroke)
            self.displayCurrentKeystroke(keystroke)
            return True, keystroke
        elif self.entry.meta_next:
            # If we run into anything else while we're processing a digit
            # string, stop the digit processing change the accelerator to an alt
            dprint("After ESC, found non-digit char: %d; adding alt to modifiers" % evt.GetKeyCode())
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
        self.displayCurrentKeystroke(keystroke)
        if eid in self.current_level.id_next_level:
            dprint("in processEvent: evt=%s id=%s FOUND MULTI-KEYSTROKE" % (str(evt.__class__), eid))
            self.current_level = self.current_level.id_next_level[eid]
            return True
        elif eid in self.current_level.keystroke_id_to_action:
            dprint("in processEvent: evt=%s id=%s FOUND ACTION %s repeat=%s" % (str(evt.__class__), eid, self.current_level.keystroke_id_to_action[eid], self.entry.repeat_value))
            action = self.current_level.keystroke_id_to_action[eid]
            if action is not None:
                action.actionKeystroke(evt, multiplier=self.entry.repeat_value)
            else:
                self.frame.SetStatusText("%s: No action specified for keystroke" % KeyAccelerator.getEmacsAccelerator(self.entry.current_keystrokes))
            
            if not self.entry.quoted_next:
                self.resetKeyboardSuccess()
            return True
        return False

    def OnMenuClose(self, evt):
        """Helper event processing to cancel multi-key keystrokes
        
        Using EVT_MENU_CLOSE instead of EVT_MENU_OPEN because on MSW the
        EVT_MENU_OPEN event is called when a keyboard accelerator matches the
        menu accelerator, regardless of the state of the accelerator table.
        """
        dprint("id=%d menu_id=%d" % (evt.GetId(), evt.GetMenuId()))
        self.cancelMultiKey()

    def OnMenu(self, evt):
        """Main event processing loop to be called from the Frame's EVT_MENU
        callback.
        
        This method is designed to be called from the root level as it
        redirects the event processing to the current keystroke level.
        
        @param evt: the CommandEvent instance from the EVT_MENU callback
        """
        dprint("id=%d event=%s" % (evt.GetId(), evt))
        if self.skip_next:
            # The incoming character has been already marked as being bad by a
            # KeyDown event, so we should't process it.
            dprint("in processEvent: skipping incoming char marked as bad by OnKeyDown")
            self.skip_next = False
        else:
            eid = evt.GetId()
            if self.entry.quoted_next:
                try:
                    keystroke = self.id_to_keystroke[eid]
                except KeyError:
                    keystroke = self.findKeystrokeFromMenuId(eid)
                dprint(keystroke)
                evt = FakeQuotedCharEvent(self.current_target, keystroke)
                self.OnChar(evt)
            elif eid in self.menu_id_to_action:
                self.foundMenuAction(evt)
            else:
                dprint("in processEvent: evt=%s id=%s not found in this level" % (str(evt.__class__), eid))
                self.reset()
    
    def findKeystrokeFromMenuId(self, eid):
        """Find the keystroke that corresponds to the current menu ID
        
        Will raise KeyError if eid not fount in the list of valid menu actions
        """
        action = self.menu_id_to_action[eid]
        dprint("checking %s" % str(self.keystroke_id_to_action))
        for keystroke_id, keystroke_action in self.keystroke_id_to_action.iteritems():
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
            
            self.reset("Unknown multi-key sequence")
            return
            
        action = self.menu_id_to_action[eid]
        if action is not None:
            try:
                index = self.menu_id_to_index[eid]
            except KeyError:
                index = -1
            dprint("evt=%s id=%s index=%d repeat=%s FOUND MENU ACTION %s" % (str(evt.__class__), eid, index, self.entry.repeat_value, self.menu_id_to_action[eid]))
            wx.CallAfter(action.action, index, self.entry.repeat_value)
        elif self.entry.meta_next and eid in self.plain_digit_keystroke:
            self.entry.meta_next = False
            self.entry.processing_esc_digit = True
            self.entry.processEscDigit(self.plain_digit_keystroke[eid])
            return
        elif self.entry.processing_esc_digit and eid in self.plain_digit_keystroke:
            self.entry.processEscDigit(self.plain_digit_keystroke[eid])
            return
        else:
            dprint("evt=%s id=%s repeat=%s FOUND MENU ACTION NONE" % (str(evt.__class__), eid, index, self.entry.repeat_value))
            self.frame.SetStatusText("None")
        self.resetMenuSuccess()
    
    def displayCurrentKeystroke(self, keystroke):
        """Add the keystroke to the list of keystrokes displayed in the status
        bar as the user is typing.
        """
        self.entry.current_keystrokes.append(keystroke)
        text = KeyAccelerator.getEmacsAccelerator(self.entry.current_keystrokes)
        self.frame.SetStatusText(text)
    
    def cancelMultiKey(self):
        if self.current_level != self:
            self.reset("Cancelled multi-key keystroke")
            
    def reset(self, message=""):
        self.entry = CurrentKeystrokes()
        self.frame.SetStatusText(message)
        self.current_level = self
    
    def resetKeyboardSuccess(self):
        self.entry = CurrentKeystrokes()
        self.current_level = self
    
    def resetMenuSuccess(self):
        self.reset()
    
    def skipNext(self):
        self.skip_next = True
        self.reset()



if __name__ == '__main__':
    class StatusUpdater:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def action(self, index, multiplier=1, **kwargs):
            if multiplier is not None:
                self.frame.SetStatusText("%d x %s" % (multiplier, self.message))
            else:
                self.frame.SetStatusText(self.message)
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)
    
    class SelfInsertCommand(object):
        def __init__(self, frame):
            self.frame = frame
        def action(self, index, multiplier=1, **kwargs):
            raise NotImplementedException
        def actionKeystroke(self, evt, multiplier=1, **kwargs):
            text = unichr(evt.GetUnicodeKey()) * multiplier
            dprint("char=%s, unichar=%s, multiplier=%s, text=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), multiplier, text))
            ctrl = evt.GetEventObject()
            if hasattr(ctrl, 'WriteText'):
                ctrl.WriteText(text)
            else:
                ctrl.AddText(text)

    class PrimaryMenu(object):
        def __init__(self, frame):
            self.frame = frame
        def action(self, index, multiplier=1, **kwargs):
            self.frame.setPrimaryMenu()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)

    class AlternateMenu(object):
        def __init__(self, frame):
            self.frame = frame
        def action(self, index, multiplier=1, **kwargs):
            self.frame.setAlternateMenu()
        def actionKeystroke(self, evt, multiplier, **kwargs):
            self.action(0, multiplier)
    
    
    class MainFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, "test")
            self.CreateStatusBar()
            
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
            self.SetMenuBar(menuBar)  # Adding empty sample menubar

            self.root_accel = AcceleratorManager()
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
            
            self.menuAddM(menuBar, gmap, "Global", "Global key map")
            self.menuAdd(gmap, "Open\tC-O", StatusUpdater)
            self.menuAdd(gmap, "Emacs Open\tC-X C-F", StatusUpdater)
            self.menuAdd(gmap, "Not Quitting\tC-X C-Q", StatusUpdater)
            self.menuAdd(gmap, "Emacs M-ESC test\tM-ESC A", StatusUpdater)
            self.menuAdd(gmap, "Alternate Menu\tC-a", AlternateMenu(self))
            self.menuAdd(gmap, "Test for hiding C-a 3\tC-X C-A", StatusUpdater)
            self.menuAdd(gmap, "Exit\tC-Q", sys.exit)
            
            indexmap = wx.Menu()
            self.menuAddM(menuBar, indexmap, "List", "List of items")
            self.menuAdd(indexmap, "Item 1\tC-X 1", StatusUpdater, index=0)
            self.menuAdd(indexmap, "Item 2\tC-X 2", StatusUpdater, index=1)
            self.menuAdd(indexmap, "Item 3\tC-X 3", StatusUpdater, index=2)

            self.root_accel.addCancelKeyBinding("C-g", StatusUpdater(self, "Cancel"))
            self.root_accel.addCancelKeyBinding("M-ESC ESC", StatusUpdater(self, "Cancel"))
            self.root_accel.addQuotedCharKeyBinding("M-q")
            self.root_accel.addDefaultKeyAction(SelfInsertCommand(self))
            
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
            self.menuAdd(gmap, "Exit\tC-Q", sys.exit)
            
            self.root_accel.addCancelKeyBinding("ESC", StatusUpdater(self, "Cancel"))
            self.root_accel.addQuotedCharKeyBinding("M-q")
            self.root_accel.addDefaultKeyAction(SelfInsertCommand(self))
            
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
