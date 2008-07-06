# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Main menu and actions.
"""

import os, glob

import wx
from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.actions.base import *
from peppy.actions.minibuffer import *

from peppy.lib.processmanager import *

from peppy.about import *
from peppy.major import *
from peppy.buffers import *
from peppy.frame import *
from peppy.debug import *


class NewTab(SelectAction):
    alias = "new-tab"
    name = "New Tab"
    tooltip = "Open a new tab"
    default_menu = (("File/New", 1), 1)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:blank", force_new_tab=True)

class CloseTab(SelectAction):
    alias = "close-tab"
    name = "Close Tab"
    tooltip = "Close the current tab"

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.tabs.closeTab()

class MoveTabToNewWindow(SelectAction):
    alias = "move-tab-to-new-window"
    name = "Move Tab to New Window"
    tooltip = "Move the current tab to a new window"

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        # If it's called from a popup, use the tab on which it was clicked, not
        # the current mode
        try:
            mode = self.frame.tabs.getContextMenuWrapper().editwin
        except IndexError:
            mode = self.mode
        wx.CallAfter(BufferFrame, buffer=mode.buffer)
        wx.CallAfter(self.frame.tabs.closeWrapper, mode)

class New(SelectAction):
    alias = "new-file"
    name = "Text file"
    tooltip = "New plain text file"
    icon = "icons/page_white_text_new.png"
    default_menu = ("File/New", -99)
    key_bindings = {'win': "C-N", 'mac': "C-N"}

    def action(self, index=-1, multiplier=1):
        self.frame.open(getNewUntitled())

class OpenFileGUI(SelectAction):
    alias = "gui-find-file"
    name = "Open File..."
    tooltip = "Open a file"
    icon = "icons/folder_page.png"
    default_menu = (("File/Open", 2), 1) 
    key_bindings = {'default': "C-O", 'emacs': "C-X C-S-F" }

    def openFiles(self, paths):
        for path in paths:
            assert self.dprint("open file %s:" % path)
            # Force the loader to use the file: protocol
            self.frame.open("file:%s" % path)

    def action(self, index=-1, multiplier=1):
        wildcard="*"
        cwd=self.frame.cwd()
        dlg = wx.FileDialog(
            self.frame, message="Open File", defaultDir=cwd, 
            defaultFile="", wildcard=wildcard, style=wx.OPEN)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()
            self.openFiles(paths)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

class OpenFileNewWindowGUI(OpenFileGUI):
    alias = "gui-find-file-new-window"
    name = "Open File in New Window..."
    tooltip = "Open a file in a new window"
    icon = None
    default_menu = (("File/Open", 2), 2) 
    key_bindings = None
    global_id = None

    def openFiles(self, paths):
        BufferFrame(paths)


class LocalFileMinibuffer(CompletionMinibuffer):
    def setDynamicChoices(self):
        text = self.text.GetValue()
        
        # NOTE: checking for ~ here rather than in OnKeyDown, because
        # OnKeyDown uses keyboard codes instead of strings.  On most
        # keyboards "~" is a shifted value and doesn't show up in the
        # keycodes.  You actually have to check for ord("`") and the
        # shift key, but that's under the assumption that the user
        # hasn't rearranged the keyboard
        if text[:-1] == self.initial:
            if text.endswith('~'):
                self.text.ChangeValue('~')
                self.text.SetInsertionPointEnd()
            elif text.endswith('/') or text.endswith(os.sep):
                self.text.ChangeValue(os.sep)
                self.text.SetInsertionPointEnd()
        elif wx.Platform == "__WXMSW__" and text[:-2] == self.initial:
            if text.endswith(':') and text[-2].isalpha():
                self.text.ChangeValue(text[-2:] + os.sep)
                self.text.SetInsertionPointEnd()
        CompletionMinibuffer.setDynamicChoices(self)

    def complete(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            prefix = wx.StandardPaths.Get().GetDocumentsDir()
            replace = len(prefix) + 1
            text = os.path.join(prefix, text[2:])
        else:
            replace = 0
        # FIXME: need to make this general by putting it in URLInfo
        paths = []
        try:
            # First, try to process the string as a unicode value.  This will
            # work in most cases on Windows and on unix when the locale is
            # set properly.  It returns unicode values
            globs = glob.glob(unicode(text)+"*")
            utf8 = False
        except UnicodeEncodeError:
            # When text is a unicode string but glob.glob is incapable of
            # processing unicode (usually only unix systems in the C/POSIX
            # locale).  It returns plain strings that will be converted using
            # utf-8
            globs = glob.glob(("%s*" % text).encode('utf-8'))
            utf8 = True
        except UnicodeDecodeError:
            # When the text is a utf-8 encoded string, but glob.glob can't
            # handle unicode (again, usually only unix systems in the C/POSIX
            # locale).  It also returns plain strings that need utf-8 decoding
            globs = glob.glob(text.encode('utf-8') + "*")
            utf8 = True
        for path in globs:
            if os.path.isdir(path):
                path += os.sep
            #dprint(path)
            if replace > 0:
                path = "~" + os.sep + path[replace:]
            
            # Always return unicode, so convert if necessary
            if utf8:
                paths.append(path.decode('utf-8'))
            else:
                paths.append(path)
        paths.sort()
        return paths

    def convert(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            text = os.path.join(wx.StandardPaths.Get().GetDocumentsDir(),
                                text[2:])
        return text

class OpenFile(SelectAction):
    alias = "find-file"
    name = "Open File Using Minibuffer..."
    tooltip = "Open a file using filename completion"
    default_menu = ("File/Open", 10)
    key_bindings = {'emacs': "C-X C-F", }

    def action(self, index=-1, multiplier=1):
        cwd=self.frame.cwd()
        if not cwd.endswith(os.sep):
            cwd += os.sep
        self.dprint(cwd)
        minibuffer = LocalFileMinibuffer(self.mode, self, label="Find file:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.frame.open(text)

class SaveAs(SelectAction):
    alias = "write-file"
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    key_bindings = {'emacs': "C-X C-W",}
    
    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1, multiplier=1):
        cwd=self.frame.cwd()
        if not cwd.endswith(os.sep):
            cwd += os.sep
        self.dprint(cwd)
        minibuffer = LocalFileMinibuffer(self.mode, self, label="Write file:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        mode.save(text)


class URLMinibuffer(CompletionMinibuffer):
    def setDynamicChoices(self):
        text = self.text.GetValue()
        
        if text[:-1] == self.initial:
            if text.endswith('/') or text.endswith(os.sep):
                uri = vfs.normalize(text)
                change = str(vfs.normalize(uri.scheme + ":"))
                self.text.ChangeValue(change)
                self.text.SetInsertionPointEnd()
        CompletionMinibuffer.setDynamicChoices(self)
    
    def completePath(self, text, uri, path):
        paths = []
        if '/' in path:
            if path.endswith('/'):
                # It's already a directory
                uridir = uri
                pattern = ''
            else:
                # The stuff after the last slash is the pattern to match
                uridir, pattern = path.rsplit('/', 1)
                uridir = vfs.get_dirname(uri)
        elif path == '.':
            # Needed to handle protocols that don't use leading slashes
            uridir = uri
            pattern = ''
        else:
            uridir = vfs.get_dirname(uri)
            pattern = path
            
        self.dprint('dir=%s pattern=%s' % (uridir, pattern))
        for name in vfs.get_names(uridir):
            if not name.startswith(pattern):
                self.dprint("skipping %s because it doesn't start with %s" % (name, pattern))
                continue
            uri = uridir.resolve2(name)
            path = str(uri)
            if vfs.is_folder(uri):
                path = str(uri) + '/'
            else:
                path = str(uri)
            self.dprint(path)
            paths.append(path)
        return paths
    
    def completeScheme(self, text, uri, path):
        paths = []
        # there's no scheme specified by the user, so complete on known
        # schemes
        pattern = text
        for name in vfs.get_file_system_schemes():
            if not name.startswith(pattern):
                self.dprint("skipping %s because it doesn't start with %s" % (name, pattern))
                continue
            paths.append(str(vfs.normalize(name + ":")))
        return paths

    def complete(self, text):
        uri = vfs.normalize(text)
        path = str(uri.path)
        self.dprint("uri=%s text=%s path=%s" % (str(uri), text, path))
        try:
            if ':' in text:
                paths = self.completePath(text, uri, path)
            else:
                paths = self.completeScheme(text, uri, path)
        except:
            import traceback
            error = traceback.format_exc()
            dprint(error)
            paths = []

        paths.sort()
        return paths

    def convert(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            text = os.path.join(wx.StandardPaths.Get().GetDocumentsDir(),
                                text[2:])
        return text

class OpenURL(SelectAction):
    alias = "find-url"
    name = "Open URL Using Minibuffer..."
    tooltip = "Open a file using URL name completion"
    default_menu = ("File/Open", 20)
    key_bindings = {'emacs': "C-X C-A", }

    def action(self, index=-1, multiplier=1):
        cwd = str(self.frame.cwd(use_vfs=True))
        self.dprint(cwd)
        minibuffer = URLMinibuffer(self.mode, self, label="Find URL:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.frame.open(text)

class SaveURL(SelectAction):
    alias = "write-url"
    name = "Save to URL Using Minibuffer..."
    tooltip = "Write to a new URL using name completion"
    key_bindings = {'emacs': "C-X C-Y", }

    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1, multiplier=1):
        cwd = str(self.frame.cwd(use_vfs=True))
        self.dprint(cwd)
        minibuffer = URLMinibuffer(self.mode, self, label="Write to URL:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        mode.save(text)


class OpenDialog(SelectAction):
    dialog_message = "Open..."
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))

        dlg = wx.TextEntryDialog(
            self.frame, message=self.dialog_message, defaultValue="",
            style=wx.OK|wx.CANCEL)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            url = dlg.GetValue()
            self.processURL(url)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

    def processURL(self, url):
        assert self.dprint("open url %s:" % url)
        self.frame.open(url)


class Exit(SelectAction):
    alias = "exit-peppy-to-return-again-soon"
    name = "E&xit"
    tooltip = "Quit the program."
    if wx.Platform == '__WXMAC__':
        # Only add the stock ID where we must: on the mac.  It interferes
        # with the emacs style keybindings, and there's no way to disable the
        # automatic Ctrl-Q keybinding AFAICT
        stock_id = wx.ID_EXIT
    default_menu = ("File", -1000)
    key_bindings = {'default': "C-Q", 'emacs': "C-X C-C"}
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().quit()

class CloseBuffer(SelectAction):
    """Delete the current document from memory"""
    alias = "close-buffer"
    name = "&Close Document"
    icon = "icons/cross.png"
    default_menu = ("File", 890)
    key_bindings = {'emacs': "C-X K"}

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.closeBuffer()

class Revert(SelectAction):
    alias = "revert-buffer"
    name = "&Revert"
    tooltip = "Revert to last saved version"
    default_menu = ("File", -900)
    default_toolbar = False
    icon = "icons/page_refresh.png"
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        dlg = wx.MessageDialog(self.frame, u"Revert file from\n\n%s?" % self.mode.buffer.url, "Revert File", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
        retval=dlg.ShowModal()
        dlg.Destroy()
            
        if retval==wx.ID_YES:
            self.mode.buffer.revert()


class Save(SelectAction):
    alias = "save-buffer"
    name = "&Save..."
    tooltip = "Save the current file"
    icon = "icons/disk.png"
    default_menu = ("File", -801)
    key_bindings = {'default': "C-S", 'emacs': "C-X C-S",}

    def isEnabled(self):
        if self.mode.buffer.readonly or not self.mode.buffer.stc.CanSave():
            return False
        return True

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mode.save()

class SaveAsGUI(SelectAction):
    alias = "save-buffer-as"
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    default_menu = ("File", 802)
    key_bindings = {'default': "C-S-S"}
    
    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))

        paths=None
        if self.mode.buffer:
            saveas = self.frame.showSaveAs("Save File")
            if saveas:
                self.mode.save(saveas)


class OpenFundamental(SelectAction):
    name = "&Open Sample Text"
    tooltip = "Open some sample text"
    default_menu = (("&Help/Samples", -500), 1)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:demo.txt")


class RunMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'startInterpreter')
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and not hasattr(self.mode, 'process')

class RunScript(RunMixin, SelectAction):
    alias = "run-script"
    name = "Run"
    tooltip = "Run this script through the interpreter"
    icon = 'icons/script_go.png'
    default_menu = ("Tools", 1)
    key_bindings = {'default': "F5"}

    def action(self, index=-1, multiplier=1):
        self.mode.startInterpreter()

class RunScriptWithArgs(RunMixin, SelectAction):
    alias = "run-script-with-args"
    name = "Run with Args"
    tooltip = "Open a file"
    icon = "icons/script_edit.png"
    default_menu = ("Tools", 2)
    key_bindings = {'default': "C-F5"}

    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Arguments:",
                                    initial = self.mode.getScriptArgs())
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.startInterpreter(text)

class RunFilter(RunMixin, SelectAction):
    """Run an external program on this file"""
    alias = "run-filter"
    name = "Run Filter"
    default_menu = ("Tools", 3)

    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Command line:",
                                    initial = self.mode.getScriptArgs())
        self.mode.setMinibuffer(minibuffer)
        self.mode.setStatusText("Enter command line, %s will be replaced by full path to file")

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.startCommandLine(text)

class StopScript(RunMixin, SelectAction):
    alias = "stop-script"
    name = "Stop"
    tooltip = "Stop the currently running script"
    icon = 'icons/stop.png'
    default_menu = ("Tools", 9)
    key_bindings = {'win': "C-CANCEL", 'emacs': "C-CANCEL", 'mac': 'C-.'}
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.stopInterpreter()


class Undo(STCModificationAction):
    alias = "undo"
    name = "Undo"
    tooltip = "Undo"
    icon = "icons/undo.png"
    default_menu = ("Edit", 0)
    key_bindings = {'default': "C-Z", 'emacs': "C-/",}
    
    def isActionAvailable(self):
        return self.mode.CanUndo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.Undo()


class Redo(STCModificationAction):
    alias = "redo"
    name = "Redo"
    tooltip = "Redo"
    icon = "icons/redo.png"
    default_menu = ("Edit", 1)
    key_bindings = {'win': "C-Y", 'emacs': "C-S-/", 'mac': "C-S-Z"}
    
    def isActionAvailable(self):
        return self.mode.CanRedo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.Redo()

class Cut(STCModificationAction):
    alias = "cut-primary-selection"
    name = "Cut"
    tooltip = "Cut"
    icon = "icons/cut.png"
    default_menu = ("Edit", -100)
    key_bindings = {'win': "C-X", 'mac': "C-X", 'emacs': "C-W"}

    def isActionAvailable(self):
        return self.mode.CanCut()

    def action(self, index=-1, multiplier=1):
        return self.mode.Cut()

class Copy(STCModificationAction):
    alias = "copy-primary-selection"
    name = "Copy"
    tooltip = "Copy"
    icon = "icons/page_copy.png"
    default_menu = ("Edit", 101)
    key_bindings = {'win': "C-C", 'mac': "C-C", 'emacs': "M-W"}

    def isActionAvailable(self):
        return self.mode.CanCopy()

    def action(self, index=-1, multiplier=1):
        return self.mode.Copy()

class Paste(STCModificationAction):
    alias = "paste-from-clipboard"
    name = "Paste"
    tooltip = "Paste"
    icon = "icons/paste_plain.png"
    default_menu = ("Edit", 102)
    key_bindings = {'win': "C-V", 'mac': "C-V", 'emacs': "C-Y"}

    def isActionAvailable(self):
        return not self.mode.GetReadOnly()

    def action(self, index=-1, multiplier=1):
        return self.mode.Paste()

class PasteAtColumn(Paste):
    alias = "paste-at-column"
    name = "Paste at Column"
    tooltip = "Paste selection indented to the cursor's column"
    icon = "icons/paste_plain.png"
    default_menu = ("Edit", 103)
    default_toolbar = False
    key_bindings = None
    global_id = None

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'PasteAtColumn')

    def action(self, index=-1, multiplier=1):
        self.mode.PasteAtColumn()

class SelectAll(STCModificationAction):
    alias = "select-all"
    name = "Select All"
    tooltip = "Select all text"
    icon = None
    default_menu = ("Edit", -125)
    default_toolbar = False
    key_bindings = {'win': "C-A", 'mac': "C-A", 'emacs': "C-X H"}
    global_id = None

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'SelectAll')

    def action(self, index=-1, multiplier=1):
        self.mode.SelectAll()


class MajorModeSelect(BufferBusyActionMixin, RadioAction):
    name="Major Mode"
    inline=False
    tooltip="Switch major mode"
    default_menu = ("View", 0)

    def initPreHook(self):
        currentmode = self.mode
        modes = MajorModeMatcherDriver.getCompatibleMajorModes(currentmode.stc_class)

        modes.sort(key=lambda s:s.keyword)
        assert self.dprint(modes)
        self.modes = modes
        names = [m.keyword for m in modes]
        self.items = names

    def getIndex(self):
        modecls = self.mode.__class__
        assert self.dprint("searching for %s in %s" % (modecls, self.modes))
        if modecls is not None.__class__:
            return self.modes.index(modecls)
        return 0
                                           
    def getItems(self):
        return self.items

    def action(self, index=-1, multiplier=1):
        self.frame.changeMajorMode(self.modes[index])


class MinorModeShow(ToggleListAction):
    name = "Minor Modes"
    inline = False
    tooltip = "Show or hide minor mode windows"
    default_menu = ("View", 1)

    def getItems(self):
        return self.mode.wrapper.minors.getKeywordOrder()

    def isChecked(self, index):
        return self.mode.wrapper.minors.isVisible(index)

    def action(self, index=-1, multiplier=1):
        self.mode.wrapper.minors.toggle(index)


class SidebarShow(ToggleListAction):
    name="Sidebars"
    inline=False
    tooltip="Show or hide sidebar windows"
    default_menu = ("View", -100)

    def getItems(self):
        return [m.caption for m in self.frame.sidebar_panes]

    def isChecked(self, index):
        return self.frame.sidebar_panes[index].IsShown()

    def action(self, index=-1, multiplier=1):
        self.frame.sidebar_panes[index].Show(not self.frame.sidebar_panes[index].IsShown())
        self.frame._mgr.Update()


class ToolbarShow(ToggleAction):
    alias = "show-toolbar"
    name = "&Show Toolbars"
    tooltip = "Enable or disable toolbar display in this frame"
    default_menu = ("View", -990)

    def isChecked(self):
        return self.frame.show_toolbar
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.frame.show_toolbar = not self.frame.show_toolbar
        self.frame.switchMode()
    

class ActionNameMinibufferMixin(object):
    def __init__(self, label):
        self.label = label
        
    def getActionList(self):
        raise NotImplementedError
        
    def createList(self):
        """Generate list of possible names to complete.

        For all the currently active actions, find all the names and
        aliases under which the action could be called, and add them
        to the list of possible completions.
        """
        self.map = {}
        actions = self.getActionList()
        for action in actions:
            # look at the emacs alias, the class name, and the
            # possibility of the translated class namex
            for name in [action.alias, action.__class__.__name__,
                         _(action.__class__.__name__)]:
                #dprint("name = %s" % name)
                if name and name not in self.map:
                    self.map[name] = action
        self.sorted = self.map.keys()
        self.sorted.sort()
        self.dprint(self.sorted)

    def action(self, index=-1, multiplier=1):
        # FIXME: ignoring number right now
        self.createList()
        minibuffer = StaticListCompletionMinibuffer(self.mode, self,
                                                    label = self.label,
                                                    list = self.sorted,
                                                    initial = "")
        self.mode.setMinibuffer(minibuffer)

class ExecuteActionByName(ActionNameMinibufferMixin, SelectAction):
    name = "&Execute Action"
    alias = "execute-action"
    tooltip = "Execute an action by name"
    key_bindings = {'default': "M-X", }
    default_menu = ("Tools", -600)
    
    def __init__(self, *args, **kwargs):
        ActionNameMinibufferMixin.__init__(self, self.keyboard)
        SelectAction.__init__(self, *args, **kwargs)

    def getActionList(self):
        """Generate list of possible names to complete.

        For all the currently active actions, find all the names and
        aliases under which the action could be called, and add them
        to the list of possible completions.
        """
        frame = self.frame
        self.dprint(frame.menumap.actions)
        actions = frame.menumap.actions.itervalues()
        return actions
    
    def processMinibuffer(self, minibuffer, mode, text):
        if text in self.map:
            action = self.map[text]
            if action.isEnabled():
                self.dprint("executing %s: %s" % (text, action))
                wx.CallAfter(action.action)
            else:
                # FIXME: display the reason why the action is disabled
                self.frame.SetStatusText("%s disabled for current buffer (FIXME: put reason why here)" % text)
        else:
            self.frame.SetStatusText("%s not a known action" % text)


class DescribeAction(ActionNameMinibufferMixin, SelectAction):
    name = "&Describe Action"
    alias = "describe-action"
    tooltip = "Describe an action by name"
    default_menu = ("&Help", -200)

    def __init__(self, *args, **kwargs):
        ActionNameMinibufferMixin.__init__(self, self.alias)
        SelectAction.__init__(self, *args, **kwargs)

    def getActionList(self):
        """Generate list of possible names to complete.

        For all the currently active actions, find all the names and
        aliases under which the action could be called, and add them
        to the list of possible completions.
        """
        frame = self.frame
        self.dprint(frame.menumap.actions)
        actions = frame.menumap.actions.itervalues()
        return actions

    def processMinibuffer(self, minibuffer, mode, text):
        if text in self.map:
            action = self.map[text]
            dprint("looking up docs for %s: %s" % (text, action))
            Publisher().sendMessage('peppy.log.info', action.getHelp())
        else:
            self.frame.SetStatusText("%s not a known action" % text)


class CancelMinibuffer(SelectAction):
    alias = "cancel-minibuffer"
    name = "Cancel Minibuffer"
    tooltip = "Cancel any currently active minibuffer"
    icon = 'icons/control_stop.png'
    key_bindings = {'default': "ESC", 'emacs': "M-ESC ESC", }
    
    def action(self, index=-1, multiplier=1):
        self.mode.removeMinibuffer()


class HelpMinibuffer(SelectAction):
    alias = "help-minibuffer"
    name = "Help on Minibuffer"
    tooltip = "Show help for the currently active minibuffer"
    default_menu = ("&Help", 210)
    key_bindings = {'emacs': "M-S-/ m", }
    
    def isEnabled(self):
        return bool(self.mode.getMinibuffer())
    
    def action(self, index=-1, multiplier=1):
        minibuffer = self.mode.getMinibuffer()
        if minibuffer:
            help = minibuffer.getHelp()
            if help:
                help = u"\n\nHelp for '%s'\n\n%s" % (minibuffer.__class__.__name__, help)
                Publisher().sendMessage('peppy.log.info', help)
            else:
                self.frame.setStatusText("Help not available for current minibuffer")


class MainMenu(IPeppyPlugin):
    """Plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    def activateHook(self):
        Publisher().subscribe(self.getTabMenu, 'tabs.context_menu')
        Publisher().subscribe(self.getFundamentalMenu, 'fundamental.context_menu')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getTabMenu)
        Publisher().unsubscribe(self.getFundamentalMenu)
    
    def getTabMenu(self, msg):
        action_classes = msg.data
        action_classes.extend([NewTab, CloseTab, MoveTabToNewWindow])
        #dprint(action_classes)

    def getFundamentalMenu(self, msg):
        action_classes = msg.data
        # FIXME: the built-in right click menu has a Delete option as well that
        # deletes the current selection.
        action_classes.extend([(-500, Undo), Redo, Cut, Copy, Paste, (-600, SelectAll)])
        #dprint(action_classes)

    def getMajorModes(self):
        yield BlankMode

    def getActions(self):
        return [NewTab, New,
                OpenFileGUI, OpenFileNewWindowGUI, OpenFile, OpenURL,
                Save, SaveAs, SaveAsGUI, SaveURL, CloseBuffer, Revert,
                Exit,

                Undo, Redo, Cut, Copy, Paste, PasteAtColumn, SelectAll,

                RunScript, RunScriptWithArgs, RunFilter, StopScript,

                MajorModeSelect, MinorModeShow, SidebarShow,
                ToolbarShow, 

                BufferList, BufferListSort,

                NewWindow, DeleteWindow, WindowList,
                
                ExecuteActionByName, DescribeAction, HelpMinibuffer,
                
                CancelMinibuffer,

                OpenFundamental,
                ]
