#!/usr/bin/env python

import sys
import wx

# Based on demo program from
# http://wiki.wxpython.org/index.cgi/Using_Multi-key_Shortcuts

wxkeynames = ("BACK", "TAB", "RETURN", "ESCAPE", "SPACE", "DELETE", "START",
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
              "NUMPAD_DIVIDE")


class KeyMap(object):
    def __init__(self):
        self.lookup={}
        self.reset()
        
        self.modifiers=['C-','S-','M-','A-']
        self.keynames={'RET':'RETURN',
                       'SPC':'SPACE',
                       'TAB':'TAB',
                       }

        self.function=None

    def reset(self):
        self.cur=self.lookup
        self.function=None

    def add(self, key):
        # return True if keystroke is processed by the handler
        if self.cur:
            if key in self.cur:
                self.cur=self.cur[key]
                if not isinstance(self.cur, dict):
                    self.function = self.cur
                    self.cur=None
                return True
            elif self.cur is not self.lookup:
                # if we get here, we're processing a key string but
                # the new key doesn't exist.  Flag as unknown
                # keystroke combo
                self.cur=None
                return True
            else:
                # OK, this is the first keystroke and it doesn't match
                # any of the first keystrokes in our keymap.  It's
                # probably a regular character, so flag it as
                # unprocessed by our handler.
                self.cur=None
        return False

    def isUnknown(self):
        return self.cur==None and self.function==None

    def matchModifier(self,str):
        for m in self.modifiers:
            if str.startswith(m):
                return m
        return None

    def matchKey(self,str):
        key=None
        i=0
        while i<len(str):
            if str[i].isspace():
                i+=1
            else:
                break
        for name in self.keynames:
            if str.startswith(name):
                val=self.keynames[name]
                return i+len(val),val
        for name in wxkeynames:
            if str.startswith(name):
                return i+len(name),name
        if i<len(str):
            return i+1,str[i].upper()
        return i,None

    def split(self,acc):
        if acc.find('\t')>=0:
            keystrokes = [i for i in acc.split('\t') if i]
        else:
            keystrokes=[]
            i=0
            flags={}
            while i<len(acc):
                for m in self.modifiers: flags[m]=False
                # check all modifiers in any order
                j=i
                while j<len(acc):
                    m=self.matchModifier(acc[j:])
                    if m:
                        j+=len(m)
                        flags[m]=True
                    else:
                        break
                print "modifiers found: %s" % str(flags)
                
                chars,key=self.matchKey(acc[j:])
                print "key found: %s" % str(flags)
                keys="".join([m for m in self.modifiers if flags[m]])+key
                print "keystroke = %s" % keys
                keystrokes.append(keys)
                i=j+chars
        print "keystrokes: %s" % keystrokes
        return keystrokes
                

    def define(self,acc,fcn):
        hotkeys = self.lookup
        print "define: acc=%s" % acc
        x = self.split(acc)
        print "define: x=%s" % str(x)
        x = [(i, j==len(x)-1) for j,i in enumerate(x)]
        for name, last in x:
            if last:
                if name in hotkeys:
                    raise Exception("Some other hotkey shares a prefix with this hotkey: %s"%acc)
                hotkeys[name] = fcn
            else:
                if name in hotkeys:
                    if not isinstance(hotkeys[name], dict):
                        raise Exception("Some other hotkey shares a prefix with this hotkey: %s"%acc)
                else:
                    hotkeys[name] = {}
                hotkeys = hotkeys[name]
        return self




class KeyProcessor(object):
    def __init__(self,status=None):
        self.keymaps=[]
        self.num=0
        self.status=status

        self.number=None
        self.defaultNumber=4 # for some reason, XEmacs defaults to 4
        self.scale=1 # scale factor, usually either 1 or -1
        self.universalArgument="C-U"
        self.processingArgument=0

        self.hasshown=False
        self.reset()

        self.wxkeys={}
        self.wxkeymap()

    def wxkeymap(self):
        for i in wxkeynames:
            self.wxkeys[getattr(wx, "WXK_"+i)] = i
        for i in ("SHIFT", "ALT", "CONTROL", "MENU"):
##            self.wxkeys[getattr(wx, "WXK_"+i)] = "MODIFIER_"+i
            self.wxkeys[getattr(wx, "WXK_"+i)] = i+'_MODIFIER'

    def decode(self,evt):
        keycode = evt.GetKeyCode()
        keyname = self.wxkeys.get(keycode, None)
        modifiers = ""
        for mod, ch in ((evt.ControlDown(), 'C-'),
                        (evt.ShiftDown(),   'S-'),
                        (evt.AltDown(),     'A-'),
                        (evt.MetaDown(),    'M-')):
            if mod:
                modifiers += ch

        if keyname is None:
            if 27 < keycode < 256:
                keyname = chr(keycode)
            else:
                keyname = "(%s)unknown" % keycode
        return modifiers + keyname

    def addKeyMap(self,keymap):
        self.keymaps.append(keymap)
        self.num=len(self.keymaps)
        self.reset()

    def reset(self):
        print "reset"
        self.sofar = ''
        for keymap in self.keymaps:
            keymap.reset()
        if self.hasshown:
            self.show('')
            self.hasshown=False
            
        self.number=None
        self.processingArgument=0
        self.args=''

    def show(self,text):
        if self.status:
            self.status.SetStatusText(text)
            self.hasshown=True

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
            self.sofar += key + ' '
            print "add: sofar=%s processed=%d unknown=%d function=%s" % (self.sofar,processed,unknown,function)
        else:
            if unknown==self.num and self.sofar=='':
                unknown=0
            print "add: sofar=%s processed=%d unknown=%d skipping %s" % (self.sofar,processed,unknown,key)
        return (processed==0,unknown==self.num,function)

    def startArgument(self, key):
        self.number=None
        self.scale=1
        self.args=key + ' '
        self.processingArgument=1

    def argument(self, key):
        if key=='-' and self.processingArgument==1:
            self.scale=-1
            self.args+=key + ' '
            self.processingArgument+=1
        elif key>='0' and key<='9':
            if self.number is None:
                self.number=ord(key)-ord('0')
            else:
                self.number=10*self.number+ord(key)-ord('0')
            self.args+=key + ' '
            self.processingArgument+=1
        else:
            if self.number is None:
                self.number=self.defaultNumber
            else:
                self.number=self.scale*self.number
            print "number = %d" % self.number
            self.processingArgument=0
        
    def process(self, evt):
        key = self.decode(evt)
        print key

        if key == 'ESCAPE':
            self.reset()
        elif key.endswith('_MODIFIER'):
            pass
        elif key.endswith('-') and len(key) > 1 and not key.endswith('--'):
            #modifiers only, if we don't skip these events, then when people
            #hold down modifier keys, things get ugly
            evt.Skip()
        elif key==self.universalArgument:
            self.startArgument(key)
            self.show(self.args)
        else:
            if self.processingArgument:
                self.argument(key)
                self.show(self.args)

            # Can't use an else here because the flag
            # self.processingArgument may get reset inside
            # self.argument() if the key is not a number.  We don't
            # want to lose that keystroke if it isn't a number so
            # process it as a potential hotkey.
            if not self.processingArgument:
                skip,unknown,function=self.add(key)
                if function:
                    save=self.number
                    self.reset()
                    if save is not None:
                        function(evt,save)
                    else:
                        function(evt)
                elif unknown:
                    sf = "%s not defined."%(self.sofar)
                    self.reset()
                    self.show(sf)
                elif skip:
                    self.reset()
                    evt.Skip()
                else:
                    self.show(self.args+self.sofar)



#a utility function and class
def _spl(st):
    if '\t' in st:
        return st.split('\t', 1)
    return st, ''

class StatusUpdater:
    def __init__(self, frame, message):
        self.frame = frame
        self.message = message
    def __call__(self, evt, number=None):
        if number is not None:
            self.frame.SetStatusText("%d x %s" % (number,self.message))
        else:
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
        self.keys.addKeyMap(self.localKeyMap)
        self.keys.addKeyMap(self.globalKeyMap)

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
        self.menuAdd(gmap, "Comment Region\tC-CC-C", "testdesc", StatusUpdater(self, "comment region"))
        self.menuAdd(gmap, "New Frame\tC-x 5 2", "New Frame", StatusUpdater(self, "open new frame"))
        self.menuAdd(gmap, "Exit\tC-XC-C", "Exit", sys.exit)

        lmap = wx.Menu()
        self.whichkeymap[lmap]=self.localKeyMap
        self.menuAddM(menuBar, lmap, "Local", "Local key map")
        self.menuAdd(lmap, "Execute \tC-CC-C", "Execute Buffer", StatusUpdater(self, "execute buffer..."))
        self.menuAdd(lmap, "Stay \tC-SC-XC-S", "Stay", StatusUpdater(self, "stay..."))
        self.menuAdd(lmap, "Multi-Modifier \tC-S-aC-S-m", "Shift-Control test", StatusUpdater(self, "pressed Shift-Control-A, Shift-Control-M"))
        self.menuAdd(lmap, "Control a\tC-a", "lower case a", StatusUpdater(self, "pressed Control-A"))
        self.menuAdd(lmap, "Control Shift b\tC-b", "upper case b", StatusUpdater(self, "pressed Control-Shift-B"))
        self.menuAdd(lmap, "Control RET\tC-RET", "control-return", StatusUpdater(self, "pressed C-RET"))
        self.menuAdd(lmap, "Control SPC\tC-SPC", "control-space", StatusUpdater(self, "pressed C-SPC"))
        self.menuAdd(lmap, "Control Page Up\tC-PRIOR", "control-prior", StatusUpdater(self, "pressed C-PRIOR"))
        self.menuAdd(lmap, "Control F5\tC-F5", "control-f5", StatusUpdater(self, "pressed C-F5"))

        #print self.lookup
        self.Show(1)


    def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
        if id == -1:
            id = wx.NewId()
        a = wx.MenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
        menu.AppendItem(a)
        wx.EVT_MENU(self, id, fcn)
        ns, acc = _spl(name)

        if acc:
            if menu in self.whichkeymap:
                keymap=self.whichkeymap[menu]
            else:
                # menu not listed in menu-to-keymap mapping.  Put in
                # local
                keymap=self.localKeyMap
            keymap.define(acc, fcn)

        # unix doesn't allow displaying arbitrary text as the accelerator key.
        #acc=acc.replace('+','-').replace('Ctrl','C').replace('Shift','S').replace('Alt','M')
        acc=acc.replace('\t',' ')
        print "acc=%s" % acc
        if wx.Platform == '__WXMSW__':
            menu.SetLabel(id, '%s\t%s'%(ns,acc))
        else:
            menu.SetLabel(id, '%s (%s)'%(ns,acc))
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

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = MainFrame()
    app.MainLoop()
