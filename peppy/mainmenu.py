# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main menu and actions.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *

from peppy.major import *
from peppy.menu import *
from peppy.buffers import *
from peppy.frame import *
from peppy.debug import *


class NewTab(SelectAction):
    name = _("&Tab")
    alias = _("new-tab")
    tooltip = _("Open a new tab")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:blank")

class New(SelectAction):
    name = _("&Text file")
    alias = _("new-file")
    tooltip = _("New plain text file")
    icon = "icons/page.png"
    key_bindings = {'win': "C-N", }

    def action(self, index=-1):
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
        if text.endswith('~') and text[:-1] == self.initial:
            self.text.ChangeValue('~')
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
        if text.startswith("~/"):
            text = os.path.join(wx.StandardPaths.Get().GetDocumentsDir(),
                                text[2:])
        return text

class OpenFile(SelectAction):
    name = _("&File...")
    alias = _("find-file")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
    key_bindings = {'win': "C-O", 'emacs': "C-X C-F", }

    def action(self, index=-1):
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

    def keyAction(self, number=None):
        cwd=self.frame.cwd() + os.sep
        self.dprint(cwd)
        minibuffer = URLMinibuffer(self.mode, self, label="Find file:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.frame.open(text)


class OpenDialog(SelectAction):
    dialog_message = "Open..."
    
    def action(self, index=-1):
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
    name = _("E&xit")
    tooltip = _("Quit the program.")
    key_bindings = {'win': "C-Q", 'emacs': "C-X C-C"}
    
    def action(self, index=-1):
        Publisher().sendMessage('peppy.request.quit')

class Close(SelectAction):
    name = _("&Close Buffer")
    alias = _("close-buffer")
    tooltip = _("Close current buffer")
    icon = "icons/cross.png"

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.close()

class Revert(SelectAction):
    name = _("&Revert")
    tooltip = _("Revert to last saved version")
    icon = "icons/page_refresh.png"

    def isEnabled(self):
        return self.mode.buffer.stc.CanEdit()

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        dlg = wx.MessageDialog(self.frame, "Revert file from\n\n%s?" % self.mode.buffer.url, "Revert File", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
        retval=dlg.ShowModal()
        dlg.Destroy()
            
        if retval==wx.ID_YES:
            mode.buffer.revert()

class Save(SelectAction):
    name = _("&Save...")
    tooltip = _("Save the current file")
    icon = "icons/disk.png"
    key_bindings = {'win': "C-S", 'emacs': "C-X C-S",}

    def isEnabled(self):
        if self.mode.buffer.readonly or not self.mode.buffer.stc.CanSave():
            return False
        return True

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mode.save()

class SaveAs(SelectAction):
    name = _("Save &As...")
    tooltip = _("Save as a new file")
    icon = "icons/disk_edit.png"
    key_bindings = {'win': "C-S-S", 'emacs': "C-X C-W",}
    
    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))

        paths=None
        if self.mode.buffer:
            saveas=mode.buffer.getFilename()
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

                    mode.save(saveas)
                elif paths!=None:
                    raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))

            dlg.Destroy()

class Undo(BufferModificationAction):
    name = _("Undo")
    tooltip = _("Undo")
    icon = "icons/arrow_turn_left.png"
    key_bindings = {'win': "C-Z", 'emacs': "C-/",}
    
    def isActionAvailable(self):
        return self.mode.stc.CanUndo()

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Undo()


class Redo(BufferModificationAction):
    name = _("Redo")
    tooltip = _("Redo")
    icon = "icons/arrow_turn_right.png"
    key_bindings = {'win': "C-Y", 'emacs': "C-S-/",}
    
    def isActionAvailable(self):
        return self.mode.stc.CanRedo()

    def action(self, index=-1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.stc.Redo()

class Cut(BufferModificationAction):
    name = _("Cut")
    tooltip = _("Cut")
    icon = "icons/cut.png"
    key_bindings = {'win': "C-X"}

    def isActionAvailable(self):
        return self.mode.stc.CanCut()

    def action(self, index=-1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Cut()

class Copy(BufferModificationAction):
    name = _("Copy")
    tooltip = _("Copy")
    icon = "icons/page_copy.png"
    key_bindings = {'win': "C-C"}

    def isActionAvailable(self):
        return self.mode.stc.CanCopy()

    def action(self, index=-1):
        assert self.dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Copy()

class Paste(BufferModificationAction):
    name = _("Paste")
    tooltip = _("Paste")
    icon = "icons/paste_plain.png"
    key_bindings = {'win': "C-V"}

    def isActionAvailable(self):
        return self.mode.stc.CanEdit()

    def action(self, index=-1):
        dprint("rectangle=%s" % self.mode.stc.SelectionIsRectangle())
        return self.mode.stc.Paste()


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

    def action(self, index=0):
        self.frame.changeMajorMode(MajorModeSelect.modes[index])


class MinorModeShow(ToggleListAction):
    name = _("Minor Modes")
    inline = False
    tooltip = _("Show or hide minor mode windows")

    def getItems(self):
        return [m.caption for m in self.mode.minor_panes]

    def isChecked(self, index):
        return self.mode.minor_panes[index].IsShown()

    def action(self, index=0):
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

    def action(self, index=0):
        self.frame.sidebar_panes[index].Show(not self.frame.sidebar_panes[index].IsShown())
        self.frame._mgr.Update()


class ToolbarShow(ToggleAction):
    name = _("&Show Toolbars")
    tooltip = _("Enable or disable toolbar display in this frame")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.frame.show_toolbar
    
    def action(self, index=-1):
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

    def action(self, index=-1):
        self.keyAction(1)

    def keyAction(self, number=None):
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
            wx.CallAfter(action.keyAction)
        else:
            print "%s not found" % text


class MainMenu(IPeppyPlugin):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """

    def possibleModes(self):
        yield BlankMode
    
    default_menu=((None,Menu(_("File")).first()),
                  (_("File"),Menu(_("New")).first()),
                  ((_("File"),_("New")),MenuItem(NewTab).first()),
                  ((_("File"),_("New")),MenuItem(New).first()),
                  (_("File"),Menu(_("Open")).after(_("New"))),
                  ((_("File"),_("Open")),MenuItem(OpenFile).first()),
                  ((_("File"),_("Open")),MenuItem(OpenURL).first()),
                  (_("File"),Separator(_("opensep")).after(_("Open"))),
                  (_("File"),MenuItem(Save).after(_("opensep"))),
                  (_("File"),MenuItem(SaveAs).after(_("opensep"))),
                  (_("File"),MenuItem(Close).after(_("opensep"))),
                  (_("File"),Separator(_("closesep")).after(_("opensep"))),
                  (_("File"),MenuItem(Revert).after(_("opensep"))),
                  (_("File"),Separator(_("quit")).after(_("opensep"))),
                  (_("File"),MenuItem(Exit).last()),
                  (None,Menu(_("Edit")).after(_("File")).first()),
                  (_("Edit"),MenuItem(Undo).first()),
                  (_("Edit"),MenuItem(Redo).first()),
                  (_("Edit"),Separator(_("cut")).first()),
                  (_("Edit"),MenuItem(Cut).first()),
                  (_("Edit"),MenuItem(Copy).first()),
                  (_("Edit"),MenuItem(Paste).first()),
                  (_("Edit"),Separator(_("paste")).first()),
                  (_("Edit"),Separator(_("lastsep")).last()),
                  (None,Menu(_("Format")).after(_("Edit")).first()),
                  (None,Menu(_("View")).before(_("Major Mode"))),
                  (_("View"),MenuItem(MajorModeSelect).first()),
                  (_("View"),MenuItem(MinorModeShow).first()),
                  (_("View"),Separator(_("modes")).first()),
                  (_("View"),MenuItem(SidebarShow).first()),
                  (_("View"),Separator(_("sidebars")).first()),
                  (_("View"),MenuItem(ToolbarShow).first()),
                  (_("View"),Separator(_("menusep"))),
                  (_("View"),Separator(_("end")).last()),
                  (None,Menu(_("Major Mode")).hide()),
                  (None,Menu(_("Minor Mode")).hide().after(_("Major Mode"))),
                  (None,Menu(_("Buffers")).last()),
                  (_("Buffers"),MenuItem(BufferList).first()),
                  (None,Menu(_("Window")).last().after(_("Buffers"))),
                  (_("Window"),Separator(_("tabs")).first()),
                  (_("Window"),MenuItem(NewFrame).first()),
                  (_("Window"),MenuItem(DeleteFrame).first()),
                  (_("Window"),Separator(_("lastsep")).first()),
                  (_("Window"),MenuItem(FrameList).last()),
                  (None,Menu(_("&Help")).last().after(_("Window"))),
                  (_("&Help"),Menu(_("&Tests"))),
                  (_("&Help"),Menu(_("&Samples"))),
                  )
    def getMenuItems(self):
        wx.App_SetMacHelpMenuTitleName(_("&Help"))
        for menu,item in self.default_menu:
            yield (None,menu,item)

    default_tools=((None,Menu(_("File")).first()),
                  (_("File"),MenuItem(New).first()),
                  (_("File"),MenuItem(OpenFile).first()),
                  (_("File"),Separator(_("save")).first()),
                  (_("File"),MenuItem(Save).first()),
                  (_("File"),MenuItem(SaveAs).first()),
                  (_("File"),MenuItem(Close).first()),
                  (None,Menu(_("Edit")).after(_("File")).first()),
                  (_("Edit"),MenuItem(Cut).first()),
                  (_("Edit"),MenuItem(Copy).first()),
                  (_("Edit"),MenuItem(Paste).first()),
                  (_("Edit"),Separator(_("cut")).first()),
                  (_("Edit"),MenuItem(Undo).first()),
                  (_("Edit"),MenuItem(Redo).first()),
                  )
    def getToolBarItems(self):
        for menu,item in self.default_tools:
            yield (None,menu,item)
            
    default_keys=((None, ExecuteCommandByName),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)
