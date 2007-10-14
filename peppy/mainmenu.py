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
    alias = _("new-tab")
    name = _("&Tab")
    tooltip = _("Open a new tab")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:blank")

class New(SelectAction):
    alias = _("new-file")
    name = _("&Text file")
    tooltip = _("New plain text file")
    icon = "icons/page.png"
    key_bindings = {'win': "C-N", }

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
    alias = _("gui-find-file")
    name = _("&File...")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
    key_bindings = {'win': "C-O" }

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
    alias = _("find-file")
    name = _("&File using Minibuffer...")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
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
    name = _("&URL...")
    tooltip = _("Open a buffer using a URL")
    icon = "icons/folder_page.png"
    key_bindings = {'emacs': "C-X C-A", }

    dialog_message = "Open URL"


class Exit(SelectAction):
    alias = _("exit-peppy-to-return-again-soon")
    name = _("E&xit")
    tooltip = _("Quit the program.")
    key_bindings = {'win': "C-Q", 'emacs': "C-X C-C"}
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().quit()

class Close(SelectAction):
    alias = _("close-buffer")
    name = _("&Close Buffer")
    tooltip = _("Close current buffer")
    icon = "icons/cross.png"

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.closeBuffer()

class Revert(SelectAction):
    alias = _("revert-buffer")
    name = _("&Revert")
    tooltip = _("Revert to last saved version")
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
    alias = _("save-buffer")
    name = _("&Save...")
    tooltip = _("Save the current file")
    icon = "icons/disk.png"
    key_bindings = {'win': "C-S", 'emacs': "C-X C-S",}

    def isEnabled(self):
        if self.mode.buffer.readonly or not self.mode.buffer.stc.CanSave():
            return False
        return True

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mode.save()

class SaveAs(SelectAction):
    alias = _("save-buffer-as")
    name = _("Save &As...")
    tooltip = _("Save as a new file")
    icon = "icons/disk_edit.png"
    key_bindings = {'win': "C-S-S", 'emacs': "C-X C-W",}
    
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
    name = _("&Open Sample Text")
    tooltip = _("Open some sample text")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:demo.txt")

class WordWrap(ToggleAction):
    alias = _("word-wrap")
    name = _("&Word Wrap")
    tooltip = _("Toggle word wrap in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.word_wrap
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setWordWrap(not self.mode.classprefs.word_wrap)
    
class LineNumbers(ToggleAction):
    alias = _("line-numbers")
    name = _("&Line Numbers")
    tooltip = _("Toggle line numbers in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.line_numbers
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setLineNumbers(not self.mode.classprefs.line_numbers)

class Folding(ToggleAction):
    alias = _("code-folding")
    name = _("&Folding")
    tooltip = _("Toggle folding in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.folding
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setFolding(not self.mode.classprefs.folding)

class RunScript(SelectAction):
    alias = _("run-script")
    name = _("Run")
    tooltip = _("Run this script through the interpreter")
    icon = 'icons/control_start.png'
    key_bindings = {'win': "F5", 'emacs': "F5", }
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and not hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.startInterpreter()


class RunScriptWithArgs(RunScript):
    alias = _("run-script-with-args")
    name = _("Run with Args")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
    key_bindings = {'default': "C-F5", }

    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Arguments:",
                                    initial = self.mode.getCommandLineArgs())
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.startInterpreter(text)


class StopScript(SelectAction):
    alias = _("stop-script")
    name = _("Stop")
    tooltip = _("Stop the currently running script")
    icon = 'icons/control_stop.png'
    key_bindings = {'win': "C-CANCEL", 'emacs': "C-CANCEL", }
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.stopInterpreter()


class Undo(BufferModificationAction):
    alias = _("undo")
    name = _("Undo")
    tooltip = _("Undo")
    icon = "icons/arrow_turn_left.png"
    key_bindings = {'win': "C-Z", 'emacs': "C-/",}
    
    def isActionAvailable(self):
        return self.mode.stc.CanUndo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Undo()


class Redo(BufferModificationAction):
    alias = _("redo")
    name = _("Redo")
    tooltip = _("Redo")
    icon = "icons/arrow_turn_right.png"
    key_bindings = {'win': "C-Y", 'emacs': "C-S-/",}
    
    def isActionAvailable(self):
        return self.mode.stc.CanRedo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Redo()

class Cut(BufferModificationAction):
    alias = _("cut-primary-selection")
    name = _("Cut")
    tooltip = _("Cut")
    icon = "icons/cut.png"
    key_bindings = {'win': "C-X"}

    def isActionAvailable(self):
        return self.mode.stc.CanCut()

    def action(self, index=-1, multiplier=1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Cut()

class Copy(BufferModificationAction):
    alias = _("copy-primary-selection")
    name = _("Copy")
    tooltip = _("Copy")
    icon = "icons/page_copy.png"
    key_bindings = {'win': "C-C"}

    def isActionAvailable(self):
        return self.mode.stc.CanCopy()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Copy()

class Paste(BufferModificationAction):
    alias = _("paste-from-clipboard")
    name = _("Paste")
    tooltip = _("Paste")
    icon = "icons/paste_plain.png"
    key_bindings = {'win': "C-V"}

    def isActionAvailable(self):
        return self.mode.stc.CanEdit()

    def action(self, index=-1, multiplier=1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Paste()

class PasteAtColumn(Paste):
    alias = _("paste-at-column")
    name = _("Paste at Column")
    tooltip = _("Paste selection indented to the cursor's column")
    icon = "icons/paste_plain.png"

    def action(self, index=-1, multiplier=1):
        self.mode.stc.PasteAtColumn()


class ElectricReturn(BufferModificationAction):
    alias = _("electric-return")
    name = _("Electric Return")
    tooltip = _("Indent the next line following a return")
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'RET',}

    def action(self, index=-1, multiplier=1):
        self.mode.stc.electricReturn()


class EOLModeSelect(BufferBusyActionMixin, RadioAction):
    name="Line Endings"
    inline=False
    tooltip="Switch line endings"

    items = ['Unix (LF)', 'DOS/Windows (CRLF)', 'Old-style Apple (CR)']
    modes = [wx.stc.STC_EOL_LF, wx.stc.STC_EOL_CRLF, wx.stc.STC_EOL_CR]

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
    name=_("Major Mode")
    inline=False
    tooltip=_("Switch major mode")

    modes=None
    items=None

    def initPreHook(self):
        currentmode = self.mode
        # FIXME: this should instead only get those major modes that
        # are in active plugins
        modes = MajorModeMatcherDriver.getActiveModes()

        # Only display those modes that use the same type of STC as
        # the current mode.
        modes = [m for m in modes if m.stc_class == currentmode.stc_class]
        
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
    name = _("Minor Modes")
    inline = False
    tooltip = _("Show or hide minor mode windows")

    def getItems(self):
        return [m.caption for m in self.mode.minor_panes]

    def isChecked(self, index):
        return self.mode.minor_panes[index].IsShown()

    def action(self, index=-1, multiplier=1):
        self.mode.minor_panes[index].Show(not self.mode.minor_panes[index].IsShown())
        self.mode._mgr.Update()


class SidebarShow(ToggleListAction):
    name=_("Sidebars")
    inline=False
    tooltip=_("Show or hide sidebar windows")

    def getItems(self):
        return [m.caption for m in self.frame.sidebar_panes]

    def isChecked(self, index):
        return self.frame.sidebar_panes[index].IsShown()

    def action(self, index=-1, multiplier=1):
        self.frame.sidebar_panes[index].Show(not self.frame.sidebar_panes[index].IsShown())
        self.frame._mgr.Update()


class ToolbarShow(ToggleAction):
    alias = _("show-toolbar")
    name = _("&Show Toolbars")
    tooltip = _("Enable or disable toolbar display in this frame")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.frame.show_toolbar
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.frame.show_toolbar = not self.frame.show_toolbar
        self.frame.switchMode()
    

class ExecuteCommandByName(SelectAction):
    name = _("&Execute Command")
    tooltip = _("Execute a command by name")
    key_bindings = {'win': "M-X", 'emacs': "M-X", }

    def createList(self):
        """Generate list of possible names to complete.

        For all the currently active actions, find all the names and
        aliases under which the action could be called, and add them
        to the list of possible completions.
        """
        frame = self.frame
        dprint(frame.menumap.actions)
        dprint(frame.toolmap.actions)
        # FIXME: ignoring those actions that only have keyboard
        # equivalents
        #dprint(frame.keys.actions)
        self.map = {}
        for actions in [frame.menumap.actions, frame.toolmap.actions]:
            if actions is None:
                continue
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

    def action(self, index=-1, multiplier=1):
        # FIXME: ignoring number right now
        self.createList()
        minibuffer = StaticListCompletionMinibuffer(self.mode, self,
                                                    label="M-X",
                                                    list = self.sorted)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        if text in self.map:
            action = self.map[text]
            print "executing %s: %s" % (text, action)
            wx.CallAfter(action.action)
        else:
            print "%s not found" % text


class CancelMinibuffer(SelectAction):
    alias = _("cancel-minibuffer")
    name = _("Cancel Minibuffer")
    tooltip = _("Cancel any currently active minibuffer")
    icon = 'icons/control_stop.png'
    key_bindings = {'default': "M-ESC ESC", }
    
    def action(self, index=-1, multiplier=1):
        self.mode.removeMinibuffer()


class MainMenu(IPeppyPlugin):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """

    def getMajorModes(self):
        yield FundamentalMode
    
    default_menu=((None,None,Menu(_("File")).first()),
                  (None,_("File"),Menu(_("New")).first()),
                  (None,(_("File"),_("New")),MenuItem(NewTab).first()),
                  (None,(_("File"),_("New")),MenuItem(New).first()),
                  (None,_("File"),Menu(_("Open")).after(_("New"))),
                  (None,(_("File"),_("Open")),MenuItem(OpenFileGUI).first()),
                  (None,(_("File"),_("Open")),MenuItem(OpenFile).first()),
                  (None,(_("File"),_("Open")),MenuItem(OpenURL).first()),
                  (None,_("File"),Separator(_("opensep")).after(_("Open"))),
                  (None,_("File"),MenuItem(Save).after(_("opensep"))),
                  (None,_("File"),MenuItem(SaveAs).after(_("opensep"))),
                  (None,_("File"),MenuItem(Close).after(_("opensep"))),
                  (None,_("File"),Separator(_("closesep")).after(_("opensep"))),
                  (None,_("File"),MenuItem(Revert).after(_("opensep"))),
                  (None,_("File"),Separator(_("quit")).after(_("opensep"))),
                  (None,_("File"),MenuItem(Exit).last()),
                  (None,None,Menu(_("Edit")).after(_("File")).first()),
                  (None,_("Edit"),MenuItem(Undo).first()),
                  (None,_("Edit"),MenuItem(Redo).first()),
                  (None,_("Edit"),Separator(_("cut")).first()),
                  (None,_("Edit"),MenuItem(Cut).first()),
                  (None,_("Edit"),MenuItem(Copy).first()),
                  (None,_("Edit"),MenuItem(Paste).first()),
                  (None,_("Edit"),Separator(_("paste")).first()),
                  (None,_("Edit"),Separator(_("lastsep")).last()),
                  (None,None,Menu(_("Format")).after(_("Edit")).first()),
                  (None,None,Menu(_("View")).before(_("Major Mode"))),
                  (None,_("View"),MenuItem(MajorModeSelect).first()),
                  (None,_("View"),MenuItem(MinorModeShow).first()),
                  (None,_("View"),Separator(_("modes")).first()),
                  (None,_("View"),MenuItem(SidebarShow).first()),
                  (None,_("View"),Separator(_("sidebars")).first()),
                  (None,_("View"),MenuItem(ToolbarShow).first()),
                  (None,_("View"),Separator(_("menusep"))),
                  (None,_("View"),Separator(_("end")).last()),
                  (None,None,Menu(_("Tools")).after(_("View")).before(_("Major Mode"))),
                  (None,_("Tools"),MenuItem(RunScript).first()),
                  (None,_("Tools"),MenuItem(RunScriptWithArgs).first()),
                  (None,_("Tools"),MenuItem(StopScript).first()),
                  (None,_("Tools"),Separator(_("run")).first()),
                  (None,_("Tools"),Separator(_("end")).last()),
                  (None,None,Menu(_("Major Mode")).hide()),
                  (None,None,Menu(_("Minor Mode")).hide().after(_("Major Mode"))),
                  (None,None,Menu(_("Buffers")).last()),
                  (None,_("Buffers"),MenuItem(BufferList).first()),
                  (None,None,Menu(_("Window")).last().after(_("Buffers"))),
                  (None,_("Window"),Separator(_("tabs")).first()),
                  (None,_("Window"),MenuItem(NewFrame).first()),
                  (None,_("Window"),MenuItem(DeleteFrame).first()),
                  (None,_("Window"),Separator(_("lastsep")).first()),
                  (None,_("Window"),MenuItem(FrameList).last()),
                  (None,None,Menu(_("&Help")).last().after(_("Window"))),
                  (None,_("&Help"),Menu(_("&Tests"))),
                  (None,_("&Help"),Menu(_("&Samples"))),
                  (None,(_("&Help"),_("&Samples")),MenuItem(OpenFundamental).first()),
                  ("Fundamental",_("Edit"),MenuItem(PasteAtColumn).after(_("Paste")).before(_("paste"))),
                  ("Fundamental",_("Edit"),MenuItem(FindText)),
                  ("Fundamental",_("Edit"),MenuItem(ReplaceText)),
                  ("Fundamental",_("Edit"),MenuItem(GotoLine)),
                  ("Fundamental",_("Format"),MenuItem(EOLModeSelect)),
                  ("Fundamental",_("Format"),Separator()),
                  ("Fundamental",_("View"),MenuItem(WordWrap)),
                  ("Fundamental",_("View"),MenuItem(LineNumbers)),
                  ("Fundamental",_("View"),MenuItem(Folding)),
                  ("Fundamental",_("View"),Separator(_("cmdsep"))),
                  ("Fundamental",None,Menu(_("&Transform")).after(_("Edit"))),
                  )
    
    def getMenuItems(self):
        wx.App_SetMacHelpMenuTitleName(_("&Help"))
        for mode, menu, item in self.default_menu:
            yield (mode,menu,item)

    default_tools=((None,None,Menu(_("File")).first()),
                  (None,_("File"),MenuItem(New).first()),
                  (None,_("File"),MenuItem(OpenFile).first()),
                  (None,_("File"),Separator(_("save")).first()),
                  (None,_("File"),MenuItem(Save).first()),
                  (None,_("File"),MenuItem(SaveAs).first()),
                  (None,_("File"),MenuItem(Close).first()),
                  (None,None,Menu(_("Edit")).after(_("File")).first()),
                  (None,_("Edit"),MenuItem(Cut).first()),
                  (None,_("Edit"),MenuItem(Copy).first()),
                  (None,_("Edit"),MenuItem(Paste).first()),
                  (None,_("Edit"),Separator(_("cut")).first()),
                  (None,_("Edit"),MenuItem(Undo).first()),
                  (None,_("Edit"),MenuItem(Redo).first()),
                  )
    def getToolBarItems(self):
        for mode, menu, item in self.default_tools:
            yield (mode, menu, item)
            
    default_keys=((None, ExecuteCommandByName),
                  (None, CancelMinibuffer),
                  ("Fundamental",ElectricReturn),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)
