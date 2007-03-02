#!/usr/bin/env python

import sys
import wx

# Based on demo program by Josiah Carlson found at
# http://wiki.wxpython.org/index.cgi/Using_Multi-key_Shortcuts

wxkeynames = (
    "BACK", "TAB", "RETURN", "ESCAPE", "SPACE", "DELETE", "START",
    "LBUTTON", "RBUTTON", "CANCEL", "MBUTTON", "CLEAR", "PAUSE",
    "CAPITAL", "PRIOR", "NEXT", "END", "HOME", "LEFT", "UP", "RIGHT",
    "DOWN", "SELECT", "PRINT", "EXECUTE", "SNAPSHOT", "INSERT", "HELP",
    "NUMPAD0", "NUMPAD1", "NUMPAD2", "NUMPAD3", "NUMPAD4", "NUMPAD5",
    "NUMPAD6", "NUMPAD7", "NUMPAD8", "NUMPAD9", "MULTIPLY", "ADD",
    "SEPARATOR", "SUBTRACT", "DECIMAL", "DIVIDE", "F1", "F2", "F3", "F4",
    "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "F13", "F14",
    "F15", "F16", "F17", "F18", "F19", "F20", "F21", "F22", "F23", "F24",
    "NUMLOCK", "SCROLL", "PAGEUP", "PAGEDOWN", "NUMPAD_SPACE",
    "NUMPAD_TAB", "NUMPAD_ENTER", "NUMPAD_F1", "NUMPAD_F2", "NUMPAD_F3",
    "NUMPAD_F4", "NUMPAD_HOME", "NUMPAD_LEFT", "NUMPAD_UP",
    "NUMPAD_RIGHT", "NUMPAD_DOWN", "NUMPAD_PRIOR", "NUMPAD_PAGEUP",
    "NUMPAD_NEXT", "NUMPAD_PAGEDOWN", "NUMPAD_END", "NUMPAD_BEGIN",
    "NUMPAD_INSERT", "NUMPAD_DELETE", "NUMPAD_EQUAL", "NUMPAD_MULTIPLY",
    "NUMPAD_ADD", "NUMPAD_SEPARATOR", "NUMPAD_SUBTRACT", "NUMPAD_DECIMAL",
    "NUMPAD_DIVIDE",
    )

class DuplicateKeyError(Exception):
    pass

##
# This class represents a group of key mappings.  The KeyProcessor
# class below uses multiple groups, one to represent global keymaps,
# one for local keymaps, and an arbitrary number of other keymaps for
# any additional minor modes that need other keymappings.
class KeyMap(object):
    modifiers=['C-','S-','A-','M-']
    modaccelerator = {'C-': 'Ctrl-',
                      'S-': 'Shift-',
                      'A-': 'Alt-',
                      'M-': 'Alt-',
                      }
    modaliases={'Ctrl-':'C-',
                'Shift-':'S-',
                'Alt-':'A-',
                'Meta-':'M-',
                'Ctrl+':'C-',
                'Shift+':'S-',
                'Alt+':'A-',
                'Meta+':'M-',
                }
    keyaliases={'RET':'RETURN',
                'SPC':'SPACE',
                'ESC':'ESCAPE',
                }
    debug = False

    def __init__(self):
        self.lookup={}
        self.reset()
        
        self.function=None

        # if this is true, it will throw an exception when finding a
        # duplicate keystroke.  If false, it silently overwrites any
        # previously defined keystroke with the new one.
        self.exceptionsWhenDuplicate=False

    def reset(self):
        self.cur=self.lookup
        self.function=None

    ##
    # return True if keystroke is processed by the handler
    def add(self, key):
        if self.cur:
            if key in self.cur:
                # get next item, either a dict of more possible
                # choices or a function to execute
                self.cur=self.cur[key]
                if not isinstance(self.cur, dict):
                    self.function = self.cur
                    self.cur=None
                return True
            elif self.cur is not self.lookup:
                # if we get here, we have processed a partial match,
                # but the most recent keystroke doesn't match
                # anything.  Flag as unknown keystroke combo
                self.cur=None
                return True
            else:
                # OK, this is the first keystroke and it doesn't match
                # any of the first keystrokes in our keymap.  It's
                # probably a regular character, so flag it as
                # unprocessed by our handler.
                self.cur=None
        return False

    ##
    # Convience function to check whether the keystroke combo is an
    # unknown combo.
    def isUnknown(self):
        return self.cur==None and self.function==None

    ##
    # Find a modifier in the accerelator string
    @classmethod
    def matchModifier(self,str):
        for m in self.modifiers:
            if str.startswith(m):
                return len(m),m
        for m in self.modaliases.keys():
            if str.startswith(m):
                return len(m),self.modaliases[m]
        return 0,None

    ##
    # Find a keyname (not modifier name) in the accelerator string,
    # matching any special keys or abbreviations of the special keys
    @classmethod
    def matchKey(self,str):
        key=None
        i=0
        for name in self.keyaliases:
            if str.startswith(name):
                val=self.keyaliases[name]
                return i+len(val),val
        for name in wxkeynames:
            if str.startswith(name):
                return i+len(name),name
        if i<len(str) and not str[i].isspace():
            return i+1,str[i].upper()
        return i,None

    ##
    # Split the accelerator string (e.g. "C-X C-S") into individual
    # keystrokes, expanding abbreviations and standardizing the order
    # of modifier keys
    @classmethod
    def split(self,acc):
        if acc.find('\t')>=0:
            # match the original format from the wxpython wiki, where
            # keystrokes are delimited by tab characters
            keystrokes = [i for i in acc.split('\t') if i]
        else:
            # find the individual keystrokes from a more emacs style
            # list, where the keystrokes are separated by whitespace.
            keystrokes=[]
            i=0
            flags={}
            while i<len(acc):
                while acc[i].isspace() and i<len(acc): i+=1

                # check all modifiers in any order.  C-S-key and
                # S-C-key mean the same thing.
                j=i
                for m in self.modifiers: flags[m]=False
                while j<len(acc):
                    chars,m=self.matchModifier(acc[j:])
                    if m:
                        j+=chars
                        flags[m]=True
                    else:
                        break
                if self.debug: print "modifiers found: %s" % str(flags)
                
                chars,key=self.matchKey(acc[j:])
                if key is not None:
                    if self.debug: print "key found: %s" % key
                    keys="".join([m for m in self.modifiers if flags[m]])+key
                    if self.debug: print "keystroke = %s" % keys
                    keystrokes.append(keys)
                else:
                    if self.debug: print "unknown key %s" % acc[j:j+chars]
                i=j+chars
        if self.debug: print "keystrokes: %s" % keystrokes
        return keystrokes

    @classmethod
    def nonEmacsName(self, acc):
        modifiers=[]
        j=0
        while j<len(acc):
            chars,m=self.matchModifier(acc[j:])
            if m:
                j+=chars
                modifiers.append(self.modaccelerator[m])
            else:
                modifiers.append(acc[j:])
                break
        return "".join(modifiers)
        
                
    ##
    # Create the nested dicts that point to the function to be
    # executed on the completion of the keystroke
    def define(self,acc,fcn):
        hotkeys = self.lookup
        if self.debug: print "define: acc=%s" % acc
        keystrokes = self.split(acc)
        if self.debug: print "define: keystrokes=%s" % str(keystrokes)
        if keystrokes:
            # create the nested dicts for everything but the last keystroke
            for keystroke in keystrokes[:-1]:
                if keystroke in hotkeys:
                    if self.exceptionsWhenDuplicate and not isinstance(hotkeys[keystroke], dict):
                        raise DuplicateKeyError("Some other hotkey shares a prefix with this hotkey: %s"%acc)
                    if not isinstance(hotkeys[keystroke],dict):
                        # if we're overwriting a function, we need to
                        # replace the function call with a dict so
                        # that the remaining keystrokes can be parsed.
                        hotkeys[keystroke] = {}
                else:
                    hotkeys[keystroke] = {}
                hotkeys = hotkeys[keystroke]

            # the last keystroke maps to the function to execute
            if self.exceptionsWhenDuplicate and keystrokes[-1] in hotkeys:
                raise DuplicateKeyError("Some other hotkey shares a prefix with this hotkey: %s"%acc)
            hotkeys[keystrokes[-1]] = fcn
        return " ".join(keystrokes)



##
# Driver class for key processing.  Takes multiple keymaps and looks
# at them in order, first the minor modes, then the local, and finally
# if nothing matches, the global key maps.
class KeyProcessor(object):
    def __init__(self,status=None):
        self.debug=False
        
        self.keymaps=[]
        self.minorKeymaps=[]
        self.globalKeymap=KeyMap()
        self.localKeymap=KeyMap()
        
        self.num=0
        self.status=status

        # I'm guessing here; I don't know what the Mac should default
        # to.
        if wx.Platform == '__WXMAC__':
            self.remapMeta="Cmd" # or Cmd
        else:
            self.remapMeta="Alt" # or Cmd

        # XEmacs defaults to the Ctrl-G to abort keystroke processing
        self.abortKey="C-G"

        # Probably should create a standard way to process sticky
        # keys, but for now ESC corresponds to a sticky meta key just
        # like XEmacs
        self.stickyMeta="ESCAPE"
        self.metaNext=False
        self.nextStickyMetaCancel=False

        self.number=None
        self.defaultNumber=4 # for some reason, XEmacs defaults to 4
        self.scale=1 # scale factor, usually either 1 or -1
        self.universalArgument="C-U"
        self.processingArgument=0

        self.hasshown=False
        self.reset()

        # Mapping of wx keystroke numbers to keystroke names
        self.wxkeys={}
        # set up the wxkeys{} dict
        self.wxkeymap()

    def wxkeymap(self):
        for i in wxkeynames:
            self.wxkeys[getattr(wx, "WXK_"+i)] = i
        for i in ("SHIFT", "ALT", "CONTROL", "MENU"):
            if wx.Platform == '__WXMSW__':
                self.wxkeys[getattr(wx, "WXK_"+i)] = ''
            else:
                # unix doesn't create a keystroke when a modifier key
                # is also modified by another modifier key, so we
                # create entries here so that decode() doesn't have to
                # have platform-specific code
                self.wxkeys[getattr(wx, "WXK_"+i)] = i[0:1]+'-'

    ##
    # set up the search order of keymaps
    def fixmaps(self):
        self.keymaps=self.minorKeymaps+[self.localKeymap,self.globalKeymap]
        self.num=len(self.keymaps)
        self.reset()

    ##
    # Add the keymap to the list of keymaps recognized by this
    # processor.  Minor mode keymaps are processed in the order that
    # they are added.
    def addMinorKeyMap(self,keymap):
        self.minorKeymaps.append(keymap)
        self.fixmaps()

    def clearMinorKeyMaps(self):
        self.minorKeymaps=[]
        self.fixmaps()

    def setGlobalKeyMap(self,keymap):
        # Always add the ESC-ESC-ESC quit key sequence
        keymap.define("M-"+self.stickyMeta+" "+self.stickyMeta,None)
        self.globalKeymap=keymap
        self.fixmaps()

    def clearGlobalKeyMap(self):
        keymap=KeyMap()
        self.setGlobalKeyMap(keymap)

    def setLocalKeyMap(self,keymap):
        self.localKeymap=keymap
        self.fixmaps()

    def clearLocalKeyMap(self):
        keymap=KeyMap()
        self.setLocalKeyMap(keymap)

    ##
    # Raw event processor that takes the keycode and produces a string
    # that describes the key pressed.  The modifier keys are always
    # returned in the order C-, S-, A-, M-
    def decode(self,evt):
        keycode = evt.GetKeyCode()
        raw = evt.GetRawKeyCode()
        keyname = self.wxkeys.get(keycode, None)
        modifiers = ""

        # handle remapping of some modifier keys.  Should probably be
        # written to be more general so that all modifier keys could
        # be remapped.
        if self.remapMeta=="Alt":
            metadown=evt.AltDown()
            altdown=False
        else:
            altdown=evt.AltDown()
            if self.remapMeta=="Cmd":
                metadown=evt.CmdDown()
            else:
                metadown=evt.MetaDown()

        # Get the modifier string in order C-, S-, A-, M-
        for mod, ch in ((evt.ControlDown(), 'C-'),
                        (evt.ShiftDown(), 'S-'),
                        (altdown, 'A-'),
                        (metadown, 'M-')
                        ):
            if mod:
                modifiers += ch

        # Check the sticky-meta
        if self.metaNext:
            if not metadown:
                # if the actual meta modifier is not pressed, add it.  We don't want to end up with M-M-key
                modifiers += 'M-'
            self.metaNext=False

            # if this is the second consecutive ESC, flag the next one
            # to cancel the keystroke input
            if keyname==self.stickyMeta:
                self.nextStickyMetaCancel=True
        else:
            # ESC hasn't been pressed before, so flag it for next
            # time.
            if keyname==self.stickyMeta:
                self.metaNext=True

        # check for printable character
        if keyname is None:
            if 27 < keycode < 256:
                keyname = chr(keycode)
            else:
                keyname = "(%s)unknown" % keycode
        if self.debug: print "keycode=%d raw=%d key=%s" % (keycode,raw,modifiers+keyname)
        return modifiers + keyname

    ##
    # reset the lookup table to the root in each keymap.
    def reset(self):
        if self.debug: print "reset"
        self.sofar = ''
        for keymap in self.keymaps:
            keymap.reset()
        if self.hasshown:
            # If we've displayed some stuff in the status area, clear
            # it.
            self.show('')
            self.hasshown=False
            
        self.number=None
        self.metaNext=False
        self.nextStickyMetaCancel=False
        self.processingArgument=0
        self.args=''

    ##
    # Display the current keystroke processing in the status area
    def show(self,text):
        if self.status:
            self.status.SetStatusText(text)
            self.hasshown=True

    ##
    # Attempt to add this keystroke by processing all keymaps in
    # parallel and stop at the first complete match.  The other way
    # that processing stops is if the new keystroke is unknown in all
    # keymaps.  Returns a tuple (skip,unknown,function), where skip is
    # true if the keystroke should be skipped up to the next event
    # handler, unknown is true if the partial keymap doesn't match
    # anything, and function is either None or the function to execute.
    def add(self, key):
        unknown=0
        processed=0
        function=None
        for keymap in self.keymaps:
            if keymap.add(key):
                processed+=1
                if keymap.function:
                    # once the first function is found, we stop processing
                    function=keymap.function
                    break
            if keymap.isUnknown():
                unknown+=1
        if processed>0:
            # at least one keymap is still matching, so continue processing
            self.sofar += key + ' '
            if self.debug: print "add: sofar=%s processed=%d unknown=%d function=%s" % (self.sofar,processed,unknown,function)
        else:
            if unknown==self.num and self.sofar=='':
                # if the keystroke doesn't match the first character
                # in any of the keymaps, don't flag it as unknown.  It
                # is a key that should be processed by the
                # application, not us.
                unknown=0
            if self.debug: print "add: sofar=%s processed=%d unknown=%d skipping %s" % (self.sofar,processed,unknown,key)
        return (processed==0,unknown==self.num,function)

    ##
    # This starts the emacs-style numeric arguments that are ended by
    # the first non-numeric keystroke
    def startArgument(self, key=None):
        self.number=None
        self.scale=1
        if key is not None:
            self.args=key + ' '
        self.processingArgument=1

    ##
    # Helper function to decode a numeric argument keystroke.  It can
    # be a number or, if the first keystroke, the '-' sign.  If C-U is
    # used to start the argumen processing, the numbers don't have to
    # have the Ctrl modifier pressed.
    def getNumber(self, key, musthavectrl=False):
        ctrl=False
        if key[0:2]=='C-':
            key=key[2:]
            ctrl=True
        if musthavectrl and not ctrl:
            return None
        
        # only allow minus sign at first character
        if key=='-' and self.processingArgument==1:
            return -1
        elif key>='0' and key<='9':
            return ord(key)-ord('0')
        return None

    ##
    # Process a numeric keystroke
    def argument(self, key):
        # allow control and a number to work as well
        num=self.getNumber(key)
        if num is None:
            # this keystroke isn't a number, so calculate the final
            # value of the numeric argument and flag that we're done
            if self.number is None:
                self.number=self.defaultNumber
            else:
                self.number=self.scale*self.number
            if self.debug: print "number = %d" % self.number
            self.processingArgument=0
        else:
            # this keystroke IS a number, so process it.
            if num==-1:
                self.scale=-1
            else:
                if self.number is None:
                    self.number=num
                else:
                    self.number=10*self.number+num
            self.args+=key + ' '
            self.processingArgument+=1

    ##
    # The main driver routine.  Get a keystroke and run through the
    # processing chain.
    def process(self, evt):
        key = self.decode(evt)

        if key == self.abortKey:
            self.reset()
            self.show("Quit")
        elif self.nextStickyMetaCancel and key==self.stickyMeta:
            # this must be processed before the check for metaNext,
            # otherwise we'll never be able to process the ESC-ESC-ESC
            # quit sequence
            self.reset()
            self.show("Quit")
        elif self.metaNext:
            # OK, the meta sticky key is down, but it's not a quit
            # sequence
            self.show(self.args+self.sofar+" "+self.stickyMeta)
        elif key.endswith('-') and len(key) > 1 and not key.endswith('--'):
            #modifiers only, if we don't skip these events, then when people
            #hold down modifier keys, things get ugly
            evt.Skip()
        elif key==self.universalArgument:
            # signal the start of a numeric argument
            self.startArgument(key)
            self.show(self.args)
        elif not self.processingArgument and self.getNumber(key,musthavectrl=True) is not None:
            # allow Ctrl plus number keys to also start a numeric argument
            self.startArgument()
            self.argument(key)
        else:
            # OK, not one of those special cases.

            if self.processingArgument:
                # if we're inside a numeric argument chain, show it.
                # Note that processingArgument may get reset inside
                # the call to argument()
                self.argument(key)
                self.show(self.args)

            # Can't use an else here because the flag
            # self.processingArgument may get reset inside
            # self.argument() if the key is not a number.  We don't
            # want to lose that keystroke if it isn't a number so
            # process it as a potential hotkey.
            if not self.processingArgument:
                # So, we're not processing a numeric argument now.
                # Check to see where we are in the processing chain.
                skip,unknown,function=self.add(key)
                if function:
                    # Found a function in one of the keymaps, so
                    # execute it.
                    save=self.number
                    self.reset()
                    if save is not None:
                        function(evt,save)
                    else:
                        function(evt)
                elif unknown:
                    # This is an unknown keystroke combo
                    sf = "%s not defined."%(self.sofar)
                    self.reset()
                    self.show(sf)
                elif skip:
                    # this is the first keystroke and it doesn't match
                    # anything.  Skip it up to the next event handler
                    # to get processed elsewhere.
                    self.reset()
                    evt.Skip()
                else:
                    self.show(self.args+self.sofar)



if __name__ == '__main__':
    #a utility function and class
    class StatusUpdater:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def __call__(self, evt, number=None):
            if number is not None:
                self.frame.SetStatusText("%d x %s" % (number,self.message))
            else:
                self.frame.SetStatusText(self.message)

    class RemoveLocal:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def __call__(self, evt, number=None):
            self.frame.keys.clearLocalKeyMap()
            self.frame.SetStatusText(self.message)

    class ApplyLocal:
        def __init__(self, frame, message):
            self.frame = frame
            self.message = message
        def __call__(self, evt, number=None):
            self.frame.keys.setLocalKeyMap(self.frame.localKeyMap)
            self.frame.SetStatusText(self.message)

    #The frame with hotkey chaining.

    class MainFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, "test")
            self.CreateStatusBar()
            ctrl = self.ctrl = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.WANTS_CHARS|wx.TE_RICH2)
            ctrl.SetFocus()
            ctrl.Bind(wx.EVT_KEY_DOWN, self.KeyPressed, ctrl)

            self.globalKeyMap=KeyMap()
            self.localKeyMap=KeyMap()
            self.keys=KeyProcessor(status=self)
            self.keys.setGlobalKeyMap(self.globalKeyMap)
            self.keys.setLocalKeyMap(self.localKeyMap)

            menuBar = wx.MenuBar()
            self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
            self.menuBar = menuBar

            self.whichkeymap={}
            gmap = wx.Menu()
            self.whichkeymap[gmap]=self.globalKeyMap
            self.menuAddM(menuBar, gmap, "Global", "Global key map")
            self.menuAdd(gmap, "Open \tC-X\tC-F", "Open File", StatusUpdater(self, "open..."))
            self.menuAdd(gmap, "Save File\tC-X\tC-S", "Save Current File", StatusUpdater(self, "saved..."))
            self.menuAdd(gmap, "Sit \tC-X\tC-X\tC-S", "Sit", StatusUpdater(self, "sit..."))
            self.menuAdd(gmap, "Stay \tC-S\tC-X\tC-S", "Stay", StatusUpdater(self, "stay..."))
            self.menuAdd(gmap, "Execute \tCtrl-C Ctrl-C", "Execute Buffer", StatusUpdater(self, "execute buffer..."))
            self.menuAdd(gmap, "New Frame\tC-x 5 2", "New Frame", StatusUpdater(self, "open new frame"))
            self.menuAdd(gmap, "Help\tCtrl-H", "Help", StatusUpdater(self, "show help"))
            self.menuAdd(gmap, "Help\tShift+Z", "Shift Z", StatusUpdater(self, "Shift Z"))
            self.menuAdd(gmap, "Exit\tC-X C-C", "Exit", sys.exit)

            lmap = wx.Menu()
            self.whichkeymap[lmap]=self.localKeyMap
            self.menuAddM(menuBar, lmap, "Local", "Local key map")
            self.menuAdd(lmap, "Turn Off Local Keymap", "Turn off local keymap", RemoveLocal(self, "local keymap removed"))
            self.menuAdd(lmap, "Turn On Local Keymap", "Turn off local keymap", ApplyLocal(self, "local keymap added"))
            self.menuAdd(lmap, "Comment Region\tC-C C-C", "testdesc", StatusUpdater(self, "comment region"))
            self.menuAdd(lmap, "Stay \tC-S C-X C-S", "Stay", StatusUpdater(self, "stay..."))
            self.menuAdd(lmap, "Multi-Modifier \tC-S-a S-C-m", "Shift-Control test", StatusUpdater(self, "pressed Shift-Control-A, Shift-Control-M"))
            self.menuAdd(lmap, "Control a\tC-A", "lower case a", StatusUpdater(self, "pressed Control-A"))
            self.menuAdd(lmap, "Control b\tC-b", "upper case b", StatusUpdater(self, "pressed Control-B"))
            self.menuAdd(lmap, "Control Shift b\tC-S-b", "upper case b", StatusUpdater(self, "pressed Control-Shift-B"))
            self.menuAdd(lmap, "Control RET\tC-RET", "control-return", StatusUpdater(self, "pressed C-RET"))
            self.menuAdd(lmap, "Control SPC\tC-SPC", "control-space", StatusUpdater(self, "pressed C-SPC"))
            self.menuAdd(lmap, "Control Page Up\tC-PRIOR", "control-prior", StatusUpdater(self, "pressed C-PRIOR"))
            self.menuAdd(lmap, "Control F5\tC-F5", "control-f5", StatusUpdater(self, "pressed C-F5"))
            self.menuAdd(lmap, "Meta-X\tM-x", "meta-x", StatusUpdater(self, "pressed meta-x"))
            self.menuAdd(lmap, "Meta-nothing\tM-", "meta-nothing", StatusUpdater(self, "pressed meta-nothing"))
            self.menuAdd(lmap, "Double Meta-nothing\tM- M-", "meta-nothing", StatusUpdater(self, "pressed meta-nothing"))

            #print self.lookup
            self.Show(1)


        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)

            def _spl(st):
                if '\t' in st:
                    return st.split('\t', 1)
                return st, ''

            ns, acc = _spl(name)

            if acc:
                if menu in self.whichkeymap:
                    keymap=self.whichkeymap[menu]
                else:
                    # menu not listed in menu-to-keymap mapping.  Put in
                    # local
                    keymap=self.localKeyMap
                keymap.define(acc, fcn)

                acc=acc.replace('\t',' ')
                #print "acc=%s" % acc
                if wx.Platform == '__WXMSW__':
                    # If windows recognizes the accelerator (e.g. "Ctrl+A") OR
                    # it doesn't recognize the whole accererator text but does
                    # recognize the last part (e.g. "C-A" where it doesn't
                    # know what the "C-" is but does see the "A", it will
                    # automatically process the accelerator before we even see
                    # it.  So, append an ascii zero to the end.
                    menu.SetLabel(id, '%s\t%s\00'%(ns,acc))
                else:
                    # unix doesn't allow displaying arbitrary text as the
                    # accelerator, so we have to just put it in the menu
                    # itself.  This doesn't look very nice, but that's about
                    # all we can do.
                    menu.SetLabel(id, '%s (%s)'%(ns,acc))
            else:
                menu.SetLabel(id,ns)
            menu.SetHelpString(id, desc)

        def menuAddM(self, parent, menu, name, help=''):
            if isinstance(parent, wx.Menu) or isinstance(parent, wx.MenuPtr):
                id = wx.NewId()
                parent.AppendMenu(id, "TEMPORARYNAME", menu, help)

                self.menuBar.SetLabel(id, name)
                self.menuBar.SetHelpString(id, help)
            else:
                parent.Append(menu, name)

        def KeyPressed(self, evt):
            self.keys.process(evt)
    
    app = wx.PySimpleApp()
    frame = MainFrame()
    app.MainLoop()
