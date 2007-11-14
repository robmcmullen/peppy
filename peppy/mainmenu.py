# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main menu and actions.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *
from peppy.actions.base import *
from peppy.actions.minibuffer import *
from peppy.actions.gotoline import *
from peppy.actions.pypefind import *

from peppy.lib.processmanager import *

from peppy.major import *
from peppy.fundamental import *
from peppy.menu import *
from peppy.buffers import *
from peppy.frame import *
from peppy.debug import *


class NewTab(SelectAction):
    alias = "new-tab"
    name = "&Tab"
    tooltip = "Open a new tab"
    default_menu = (("File/New", 1), 1.0)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:blank")

class New(SelectAction):
    alias = "new-file"
    name = "&Text file"
    tooltip = "New plain text file"
    icon = "icons/page.png"
    default_menu = ("File/New", 1.1)
    key_bindings = {'win': "C-N", 'mac': "C-N"}

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:untitled")

class URLMinibuffer(CompletionMinibuffer):
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
        for path in glob.glob(text+"*"):
            if os.path.isdir(path):
                path += os.sep
            #dprint(path)
            if replace > 0:
                path = "~" + os.sep + path[replace:]
            paths.append(path)
        paths.sort()
        return paths

    def convert(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            text = os.path.join(wx.StandardPaths.Get().GetDocumentsDir(),
                                text[2:])
        return text

class OpenFileGUI(SelectAction):
    alias = "gui-find-file"
    name = "&File..."
    tooltip = "Open a file"
    icon = "icons/folder_page.png"
    default_menu = (("File/Open", 2), 1) 
    key_bindings = {'default': "C-O", 'emacs': "C-X C-S-F" }

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

            for path in paths:
                assert self.dprint("open file %s:" % path)
                # Force the loader to use the file: protocol
                self.frame.open("file:%s" % path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

class OpenFile(SelectAction):
    alias = "find-file"
    name = "&File using Minibuffer..."
    tooltip = "Open a file"
    default_menu = ("File/Open", 2)
    key_bindings = {'emacs': "C-X C-F", }

    def action(self, index=-1, multiplier=1):
        cwd=self.frame.cwd()
        if not cwd.endswith(os.sep):
            cwd += os.sep
        self.dprint(cwd)
        minibuffer = URLMinibuffer(self.mode, self, label="Find file:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.frame.open(text)


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
        

class OpenURL(OpenDialog):
    name = "&URL..."
    tooltip = "Open a buffer using a URL"
    default_menu = ("File/Open", 3)
    key_bindings = {'emacs': "C-X C-A", }

    dialog_message = "Open URL"


class Exit(SelectAction):
    alias = "exit-peppy-to-return-again-soon"
    name = "E&xit"
    tooltip = "Quit the program."
    default_menu = ("File", -1000)
    key_bindings = {'default': "C-Q", 'emacs': "C-X C-C"}
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().quit()

class Close(SelectAction):
    alias = "close-buffer"
    name = "&Close Buffer"
    tooltip = "Close current buffer"
    default_menu = ("File", 809)
    icon = "icons/cross.png"

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

    def isEnabled(self):
        return self.mode.buffer.stc.CanEdit()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        dlg = wx.MessageDialog(self.frame, "Revert file from\n\n%s?" % self.mode.buffer.url, "Revert File", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
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

class SaveAs(SelectAction):
    alias = "save-buffer-as"
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    default_menu = ("File", 802)
    key_bindings = {'default': "C-S-S", 'emacs': "C-X C-W",}
    
    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))

        paths=None
        if self.mode.buffer:
            saveas = self.mode.buffer.getFilename()
            cwd = self.frame.cwd()
            assert self.dprint("cwd = %s, path = %s" % (cwd, saveas))
            saveas=os.path.basename(saveas)

            wildcard="*.*"
            dlg = wx.FileDialog(
                self.frame, message="Save File", defaultDir=cwd, 
                defaultFile=saveas, wildcard=wildcard,
                style=wx.SAVE| wx.CHANGE_DIR | wx.OVERWRITE_PROMPT)

            # FIXME: bug in linux: setting defaultFile to some
            # non-blank string causes directory to be set to
            # current working directory.  If defaultFile == "",
            # working directory is set to the specified
            # defaultDir.           
            dlg.SetDirectory(cwd)
            
            retval=dlg.ShowModal()
            if retval==wx.ID_OK:
                # This returns a Python list of files that were selected.
                paths = dlg.GetPaths()
                if len(paths)>0:
                    saveas=paths[0]
                    assert self.dprint("save file %s:" % saveas)

                    self.mode.save(saveas)
                elif paths!=None:
                    raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))

            dlg.Destroy()

class OpenFundamental(SelectAction):
    name = "&Open Sample Text"
    tooltip = "Open some sample text"
    default_menu = "&Help/Samples"

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:demo.txt")

class WordWrap(ToggleAction):
    alias = "word-wrap"
    name = "&Word Wrap"
    tooltip = "Toggle word wrap in this view"
    default_menu = ("View", 301)

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'setWordWrap')

    def isChecked(self):
        return self.mode.classprefs.word_wrap
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setWordWrap(not self.mode.classprefs.word_wrap)
    
class LineNumbers(ToggleAction):
    alias = "line-numbers"
    name = "&Line Numbers"
    tooltip = "Toggle line numbers in this view"
    default_menu = ("View", -300)

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'setLineNumbers')

    def isChecked(self):
        return self.mode.classprefs.line_numbers
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setLineNumbers(not self.mode.classprefs.line_numbers)

class Folding(ToggleAction):
    alias = "code-folding"
    name = "&Folding"
    tooltip = "Toggle folding in this view"
    default_menu = ("View", 302)

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'setFolding')

    def isChecked(self):
        return self.mode.classprefs.folding
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setFolding(not self.mode.classprefs.folding)

class RunScript(SelectAction):
    alias = "run-script"
    name = "Run"
    tooltip = "Run this script through the interpreter"
    icon = 'icons/script_go.png'
    default_menu = ("Tools", 1)
    key_bindings = {'default': "F5"}

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'startInterpreter')
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and not hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.startInterpreter()


class RunScriptWithArgs(RunScript):
    alias = "run-script-with-args"
    name = "Run with Args"
    tooltip = "Open a file"
    icon = "icons/script_edit.png"
    default_menu = ("Tools", 2)
    
    # If subclassing another action, make sure to reset global_id, or the
    # menu system will use the existing global id for the new action
    global_id = None
    key_bindings = {'default': "C-F5"}

    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Arguments:",
                                    initial = self.mode.getScriptArgs())
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.startInterpreter(text)


class StopScript(RunScript):
    alias = "stop-script"
    name = "Stop"
    tooltip = "Stop the currently running script"
    icon = 'icons/stop.png'
    default_menu = ("Tools", 3)
    global_id = None
    key_bindings = {'win': "C-CANCEL", 'emacs': "C-CANCEL", 'mac': 'C-.'}
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.stopInterpreter()


class Undo(STCModificationAction):
    alias = "undo"
    name = "Undo"
    tooltip = "Undo"
    icon = "icons/arrow_turn_left.png"
    default_menu = ("Edit", 0)
    key_bindings = {'default': "C-Z", 'emacs': "C-/",}
    
    def isActionAvailable(self):
        return self.mode.stc.CanUndo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Undo()


class Redo(STCModificationAction):
    alias = "redo"
    name = "Redo"
    tooltip = "Redo"
    icon = "icons/arrow_turn_right.png"
    default_menu = ("Edit", 1)
    key_bindings = {'win': "C-Y", 'emacs': "C-S-/", 'mac': "C-S-Z"}
    
    def isActionAvailable(self):
        return self.mode.stc.CanRedo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Redo()

class Cut(STCModificationAction):
    alias = "cut-primary-selection"
    name = "Cut"
    tooltip = "Cut"
    icon = "icons/cut.png"
    default_menu = ("Edit", -100)
    key_bindings = {'win': "C-X", 'mac': "C-X"}

    def isActionAvailable(self):
        return self.mode.stc.CanCut()

    def action(self, index=-1, multiplier=1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Cut()

class Copy(STCModificationAction):
    alias = "copy-primary-selection"
    name = "Copy"
    tooltip = "Copy"
    icon = "icons/page_copy.png"
    default_menu = ("Edit", 101)
    key_bindings = {'win': "C-C", 'mac': "C-C"}

    def isActionAvailable(self):
        return self.mode.stc.CanCopy()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Copy()

class Paste(STCModificationAction):
    alias = "paste-from-clipboard"
    name = "Paste"
    tooltip = "Paste"
    icon = "icons/paste_plain.png"
    default_menu = ("Edit", 102)
    key_bindings = {'win': "C-V", 'mac': "C-V"}

    def isActionAvailable(self):
        return self.mode.stc.CanEdit()

    def action(self, index=-1, multiplier=1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Paste()

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
        return hasattr(mode.editwin, 'PasteAtColumn')

    def action(self, index=-1, multiplier=1):
        self.mode.stc.PasteAtColumn()


class ElectricReturn(TextModificationAction):
    alias = "electric-return"
    name = "Electric Return"
    tooltip = "Indent the next line following a return"
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'RET',}

    def action(self, index=-1, multiplier=1):
        self.mode.stc.electricReturn()


class EOLModeSelect(BufferBusyActionMixin, RadioAction):
    name="Line Endings"
    inline=False
    tooltip="Switch line endings"
    default_menu = ("Transform", -999)

    items = ['Unix (LF)', 'DOS/Windows (CRLF)', 'Old-style Apple (CR)']
    modes = [wx.stc.STC_EOL_LF, wx.stc.STC_EOL_CRLF, wx.stc.STC_EOL_CR]

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode.editwin, 'GetEOLMode')

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)

    def getIndex(self):
        eol = self.mode.stc.GetEOLMode()
        return EOLModeSelect.modes.index(eol)
                                           
    def getItems(self):
        return EOLModeSelect.items

    def action(self, index=-1, multiplier=1):
        self.mode.stc.ConvertEOLs(EOLModeSelect.modes[index])
        Publisher().sendMessage('resetStatusBar')


class MajorModeSelect(BufferBusyActionMixin, RadioAction):
    name="Major Mode"
    inline=False
    tooltip="Switch major mode"
    default_menu = ("View", 0)

    modes=None
    items=None

    def initPreHook(self):
        currentmode = self.mode
        modes = MajorModeMatcherDriver.getCompatibleMajorModes(currentmode.stc_class)

        modes.sort(key=lambda s:s.keyword)
        assert self.dprint(modes)
        MajorModeSelect.modes = modes
        names = [m.keyword for m in modes]
        MajorModeSelect.items = names

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)

    def getIndex(self):
        modecls = self.mode.__class__
        assert self.dprint("searching for %s in %s" % (modecls, MajorModeSelect.modes))
        if modecls is not None.__class__:
            return MajorModeSelect.modes.index(modecls)
        return 0
                                           
    def getItems(self):
        return MajorModeSelect.items

    def action(self, index=-1, multiplier=1):
        self.frame.changeMajorMode(MajorModeSelect.modes[index])


class MinorModeShow(ToggleListAction):
    name = "Minor Modes"
    inline = False
    tooltip = "Show or hide minor mode windows"
    default_menu = ("View", 1)

    def getItems(self):
        return [m.caption for m in self.mode.minor_panes]

    def isChecked(self, index):
        return self.mode.minor_panes[index].IsShown()

    def action(self, index=-1, multiplier=1):
        self.mode.minor_panes[index].Show(not self.mode.minor_panes[index].IsShown())
        self.mode._mgr.Update()


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
            self.dprint("executing %s: %s" % (text, action))
            wx.CallAfter(action.action)
        else:
            self.frame.SetStatusText("%s not a known action" % text)


class DescribeAction(ActionNameMinibufferMixin, SelectAction):
    name = "&Describe Action"
    alias = "describe-action"
    tooltip = "Describe an action by name"

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
        dprint("HERE!!!")
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
    key_bindings = {'default': "M-ESC ESC", }
    
    def action(self, index=-1, multiplier=1):
        self.mode.removeMinibuffer()


class WordCount(SelectAction):
    name = "&Word Count"
    tooltip = "Word count in region or document"
    default_menu = ("Tools", -500)
    key_bindings = {'default': "M-=", }

    def action(self, index=-1, multiplier=1):
        s = self.mode.editwin
        (start, end) = s.GetSelection()
        if start==end:
            text = s.GetText()
        else:
            text = s.GetTextRange(start, end)
        chars = len(text)
        words = len(text.split())
        lines = len(text.splitlines())
        self.frame.SetStatusText("%d chars, %d words, %d lines" % (chars, words, lines))


class MainMenu(IPeppyPlugin):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """

    def getMajorModes(self):
        yield FundamentalMode
        yield BlankMode

    def getActions(self):
        return [NewTab, New,
                OpenFileGUI, OpenFile, OpenURL,
                Save, SaveAs, Close, Revert, Exit,

                Undo, Redo, Cut, Copy, Paste, PasteAtColumn,

                RunScript, RunScriptWithArgs, StopScript,

                MajorModeSelect, MinorModeShow, SidebarShow,
                ToolbarShow, 

                EOLModeSelect, WordWrap, LineNumbers, Folding,

                BufferList,

                NewFrame, DeleteFrame, FrameList,

                FindText, ReplaceText, GotoLine,
                
                ExecuteActionByName, DescribeAction,
                
                CancelMinibuffer, ElectricReturn,

                OpenFundamental,
                ]

    def getCompatibleActions(self, mode):
        if issubclass(mode, FundamentalMode):
            return [WordCount]
        return []
