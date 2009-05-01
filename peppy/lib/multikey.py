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

# Emacs style modifiers are used internally to specify which of the modifier
# keys are pressed.  They are used as in "C-x" to mean Control-X.
#
# Prefixes:
#  C-   Control on MSW/GTK; Command on Mac
#  ^-   Control on Mac, aliased to C- on MSW/GTK
#  S-   Shift
#  M-   Alt/Option on MAC; Alt on MSW/GTK
#  A-   aliased to M- on all platforms
emacs_modifiers=['^-', 'C-','S-','A-','M-']

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
    debug = True
    
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
                if cls.debug: print "key found: %s, chars=%d" % (key, chars)
                normalized.append((flags, key))
            else:
                if cls.debug: print "unknown key %s" % acc[j:j+chars]
            if j + chars < len(acc):
                if cls.debug: print "remaining='%s'" % acc[j+chars:]
            i = j + chars
        if cls.debug: print "keystrokes: %s" % normalized
        return normalized
    
    @classmethod
    def getKeystrokes(cls, normalized):
        keystrokes = []
        for key in normalized:
            try:
                keystroke = cls.normalized_keystroke_cache[key]
                dprint("Found cached keystroke %s" % keystroke.getEmacsAccelerator())
            except KeyError:
                keystroke = Keystroke(key[0], key[1])
                dprint("Created and cached keystroke %s" % keystroke.getEmacsAccelerator())
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
    def __init__(self, frame, *args, **kwargs):
        self.frame = frame
        if 'root' in kwargs:
            self.root = kwargs['root']
        else:
            self.root = self
        
        # Flag to indicate that the 
        self.skip_next = False
            
        self.id_to_keystroke = {}
        self.id_next_level = {}
        self.valid_keystrokes = {}
        for arg in args:
            dprint(str(arg))
            self.add(arg)
    
    def __str__(self):
        return self.getPrettyStr()
    
    def getPrettyStr(self, prefix=""):
        lines = []
        keys = self.id_to_keystroke.keys()
        keys.sort()
        for key in keys:
            keystroke = self.id_to_keystroke[key]
            lines.append("%skey %d: %s %s" % (prefix, key, keystroke.getEmacsAccelerator(), str(keystroke.getAcceleratorTableEntry())))
            if key in self.id_next_level:
                lines.append(self.id_next_level[key].getPrettyStr(prefix + "  "))
        return os.linesep.join(lines)
    
    def add(self, key_binding):
        keystrokes = list(KeyAccelerator.split(key_binding))
        keystrokes.append(None)
        current = self
        for keystroke, next_keystroke in zip(keystrokes, keystrokes[1:]):
            current.id_to_keystroke[keystroke.id] = keystroke
            current.valid_keystrokes[(keystroke.flags, keystroke.keycode)] = True
            if next_keystroke is not None:
                try:
                    current = current.id_next_level[keystroke.id]
                except KeyError:
                    accel_list = AcceleratorList(self.frame)
                    current.id_next_level[keystroke.id] = accel_list
                    current = accel_list
    
    def getTable(self):
        table = []
        for keystroke in self.id_to_keystroke.values():
            table.append(keystroke.getAcceleratorTableEntry())
        dprint("AcceleratorTable: %s" % str(table))
        return wx.AcceleratorTable(table)
    
    def setAccelerators(self):
        self.frame.SetAcceleratorTable(self.getTable())
    
    def processEvent(self, evt):
        if self.skip_next:
            # The incoming character has been already marked as being bad by a
            # KeyDown event, so we should't process it.
            dprint("in processEvent: skipping incoming char marked as bad by OnKeyDown")
            self.skip_next = False
        else:
            eid = evt.GetId()
            if eid in self.id_to_keystroke:
                if eid in self.id_next_level:
                    dprint("in processEvent: id=%s FOUND MULTI-KEYSTROKE" % eid)
                    return self.id_next_level[eid]
                else:
                    dprint("in processEvent: id=%s FOUND ACTION" % eid)
            else:
                dprint("in processEvent: id=%s not found in this level" % eid)
        return None
    
    def skipNext(self):
        self.skip_next = True
    
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
        def __call__(self, evt, number=None, **kwargs):
            if number is not None:
                self.frame.SetStatusText("%d x %s" % (number,self.message))
            else:
                self.frame.SetStatusText(self.message)

    #The frame with hotkey chaining.

    class MainFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, "test")
            self.CreateStatusBar()
            self.ctrl = self.ctrl = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.WANTS_CHARS|wx.TE_RICH2)
            self.ctrl.SetFocus()

            try:
                self.setMenu()
            except:
                import traceback
                traceback.print_exc()
                raise

        def setMenu(self):
            menuBar = wx.MenuBar()
            self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
            self.menuBar = menuBar
            
            gmap = wx.Menu()
            self.root_accel = AcceleratorList(self, "^X", "Ctrl-S", "Ctrl-TAB", "^X^F", "Ctrl-X Ctrl-S", "C-S C-A", "C-c C-c")
            dprint(self.root_accel)
            
            self.menuAddM(menuBar, gmap, "Global", "Global key map")
            self.menuAdd(gmap, "Exit\tC-Q", "Exit", sys.exit)

            dprint("HERE")
            
            self.setAcceleratorLevel()
            dprint("HERE")
            
            self.Bind(wx.EVT_MENU, self.OnMenu)
            dprint("HERE")
            self.ctrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            #self.ctrl.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
            dprint("HERE")
            self.Show(1)
            dprint("HERE")
        
        def setAcceleratorLevel(self, level=None):
            if level is None:
                self.current_accel = self.root_accel
            else:                self.current_accel = level
            self.current_accel.setAccelerators()
        
        def OnMenu(self, evt):
            eid = evt.GetId()
            dprint("in OnMenu: id=%s" % eid)
            level = self.current_accel.processEvent(evt)
            if level:
                self.setAcceleratorLevel(level)
            else:
                if self.current_accel != self.root_accel:
                    self.setAcceleratorLevel()
            
        def OnKeyDown(self, evt):
            self.LogKeyEvent("KeyDown", evt)
            if not self.current_accel.isValidAccelerator(evt):
                # OnMenu event will never get generated if it doesn't appear in
                # the accelerator table, so reset the accelerator table to the
                # root table
                dprint("Unknown accelerator; resetting to root")
                if self.current_accel != self.root_accel:
                    self.setAcceleratorLevel()
                self.root_accel.skipNext()
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

        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
            menu.AppendItem(a)
            #wx.EVT_MENU(self, id, fcn)

            def _spl(st):
                if '\t' in st:
                    return st.split('\t', 1)
                return st, ''

            ns, acc = _spl(name)

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
                menu.SetLabel(id, "%s%s" % (ns, acc_text))
                
                self.root_accel.add(acc)
            else:
                menu.SetLabel(id,ns)
            menu.SetHelpString(id, desc)

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
