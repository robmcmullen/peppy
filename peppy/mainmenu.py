# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main menu and actions.
"""

import os

import wx

from peppy import *

from major import *
from menu import *
from buffers import *
from debug import *
from trac.core import *


class NewTab(SelectAction):
    name = _("New &Tab")
    tooltip = _("Open a new Tab")
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:blank")

class New(SelectAction):
    name = _("&New File...")
    tooltip = _("New file")
    icon = "icons/page.png"
    key_bindings = {'win': "C-N", }

    def action(self, pos=-1):
        self.frame.open("about:untitled")



class OpenFile(SelectAction):
    name = _("&Open File...")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
    key_bindings = {'win': "C-O", 'emacs': "C-X C-F", }

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

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

class OpenURL(SelectAction):
    name = _("Open URL...")
    tooltip = _("Open a file through a URL")
    icon = "icons/folder_page.png"
    key_bindings = {'emacs': "C-X C-A", }

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        wildcard="*"
        cwd=os.getcwd()
        dlg = wx.TextEntryDialog(
            self.frame, message="Open URL", defaultValue="",
            style=wx.OK|wx.CANCEL)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            url = dlg.GetValue()

            assert self.dprint("open url %s:" % url)
            self.frame.open(url)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()


class Exit(SelectAction):
    name = _("E&xit")
    tooltip = _("Quit the program.")
    key_bindings = {'win': "C-Q", 'emacs': "C-X C-C"}
    
    def action(self, pos=-1):
        self.frame.app.quit()

class Close(SelectAction):
    name = _("&Close")
    tooltip = _("Close current file")
    icon = "icons/cross.png"

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.close()

class Revert(SelectAction):
    name = _("&Revert")
    tooltip = _("Revert to last saved version")
    icon = "icons/page_refresh.png"

    def isEnabled(self):
        mode=self.frame.getActiveMajorMode()
        if mode and mode.buffer.stc.CanEdit():
            return True
        return False

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        mode=self.frame.getActiveMajorMode()
        dlg = wx.MessageDialog(self.frame, "Revert file from\n\n%s?" % mode.buffer.url, "Revert File", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
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
        mode=self.frame.getActiveMajorMode()
        if mode:
            if mode.buffer.readonly:
                return False
            return True
        return False

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.save()

class SaveAs(SelectAction):
    name = _("Save &As...")
    tooltip = _("Save as a new file")
    icon = "icons/disk_edit.png"
    key_bindings = {'win': "C-S-S", 'emacs': "C-X C-W",}
    
    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        mode=self.frame.getActiveMajorMode()
        paths=None
        if mode and mode.buffer:
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

                    mode.buffer.save(saveas)
                elif paths!=None:
                    raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))

            dlg.Destroy()

class Undo(BufferModificationAction):
    name = _("Undo")
    tooltip = _("Undo")
    icon = "icons/arrow_turn_left.png"
    key_bindings = {'win': "C-Z", 'emacs': "C-/",}
    
    def isActionAvailable(self, mode):
        return mode.stc.CanUndo()

    def modify(self, mode, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        return mode.stc.Undo()


class Redo(BufferModificationAction):
    name = _("Redo")
    tooltip = _("Redo")
    icon = "icons/arrow_turn_right.png"
    key_bindings = {'win': "C-Y", 'emacs': "C-S-/",}
    
    def isActionAvailable(self, mode):
        return mode.stc.CanRedo()

    def modify(self, mode, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        return mode.stc.Redo()

class Cut(BufferModificationAction):
    name = _("Cut")
    tooltip = _("Cut")
    icon = "icons/cut.png"
    key_bindings = {'win': "C-X"}

    def isActionAvailable(self, mode):
        return mode.stc.CanCut()

    def modify(self, mode, pos=-1):
        dprint("rectangle=%s" % mode.stc.SelectionIsRectangle())
        return mode.stc.Cut()

class Copy(BufferModificationAction):
    name = _("Copy")
    tooltip = _("Copy")
    icon = "icons/page_copy.png"
    key_bindings = {'win': "C-C"}

    def isActionAvailable(self, mode):
        return mode.stc.CanCopy()

    def modify(self, mode, pos=-1):
        assert self.dprint("rectangle=%s" % mode.stc.SelectionIsRectangle())
        return mode.stc.Copy()

class Paste(BufferModificationAction):
    name = _("Paste")
    tooltip = _("Paste")
    icon = "icons/paste_plain.png"
    key_bindings = {'win': "C-V"}

    def isActionAvailable(self, mode):
        return mode.stc.CanEdit()

    def modify(self, mode, pos=-1):
        dprint("rectangle=%s" % mode.stc.SelectionIsRectangle())
        return mode.stc.Paste()



class MainMenu(Component):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    default_menu=((None,Menu(_("File")).first()),
                  (_("File"),MenuItem(New).first()),
                  (_("File"),MenuItem(OpenFile).after(_("&New File..."))),
                  (_("File"),MenuItem(OpenURL).after(_("&Open File..."))),
                  (_("File"),Separator(_("opensep")).after(_("Open URL..."))),
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
                  (_("View"),Separator(_("modes"))),
                  (_("View"),MenuItem(SidebarShow)),
                  (_("View"),Separator(_("menusep"))),
                  (_("View"),Separator(_("end")).last()),
                  (None,Menu(_("Major Mode")).hide()),
                  (None,Menu(_("Minor Mode")).hide().after(_("Major Mode"))),
                  (None,Menu(_("Buffers")).last()),
                  (_("Buffers"),MenuItem(BufferList).first()),
                  (None,Menu(_("Window")).last().after(_("Buffers"))),
                  (_("Window"),MenuItem(NewTab).first()),
                  (_("Window"),Separator(_("tabs")).first()),
                  (_("Window"),MenuItem(NewFrame).first()),
                  (_("Window"),MenuItem(DeleteFrame).first()),
                  (_("Window"),Separator(_("lastsep")).first()),
                  (_("Window"),MenuItem(FrameList).last()),
                  (None,Menu(_("&Help")).last().after(_("Window"))),
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
