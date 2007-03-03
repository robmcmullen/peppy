#!/usr/bin/env python
"""
Main application program.
"""

import os

import wx

from peppy import *

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

    def action(self, pos=-1):
        self.frame.open("about:untitled")



class OpenFile(SelectAction):
    name = _("&Open File...")
    tooltip = _("Open a file")
    icon = "icons/folder_page.png"
    keyboard = "C-X C-F"

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
    keyboard = "C-X C-A"

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
    keyboard = "C-X C-C"
    
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

class Save(SelectAction):
    name = _("&Save...")
    tooltip = _("Save the current file")
    icon = "icons/disk.png"
    keyboard = "C-X C-S"

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
    keyboard = "C-X C-W"
    
    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        mode=self.frame.getActiveMajorMode()
        paths=None
        if mode and mode.buffer:
            saveas=mode.buffer.getFilename()
            cwd = self.frame.cwd()
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


class Undo(SelectAction):
    name = _("Undo")
    tooltip = _("Undo")
    icon = "icons/arrow_turn_left.png"
    keyboard = "C-/"
    
    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.stc.CanUndo()
        return False

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.Undo()


class Redo(SelectAction):
    name = _("Redo")
    tooltip = _("Redo")
    icon = "icons/arrow_turn_right.png"
    keyboard = "C-S-/"
    
    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.stc.CanRedo()
        return False

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.Redo()

class Cut(SelectAction):
    name = _("Cut")
    tooltip = _("Cut")
    icon = "icons/cut.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.stc.CanCut()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Cut()

class Copy(SelectAction):
    name = _("Copy")
    tooltip = _("Copy")
    icon = "icons/page_copy.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.stc.CanCopy()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Copy()

class Paste(SelectAction):
    name = _("Paste")
    tooltip = _("Paste")
    icon = "icons/paste_plain.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            assert self.dprint("mode=%s stc=%s paste=%s" % (viewer,viewer.stc,viewer.stc.CanPaste()))
            return viewer.stc.CanPaste()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Paste()


class MainMenu(Component):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    default_menu=((None,Menu("File").first()),
                  ("File",MenuItem(New).first()),
                  ("File",MenuItem(OpenFile).after("&New File...")),
                  ("File",MenuItem(OpenURL).after("&Open File...")),
                  ("File",Separator("opensep").after("Open URL...")),
                  ("File",MenuItem(Save).after("opensep")),
                  ("File",MenuItem(SaveAs).after("opensep")),
                  ("File",MenuItem(Close).after("opensep")),
                  ("File",Separator("quit").after("opensep")),
                  ("File",MenuItem(Exit).last()),
                  (None,Menu("Edit").after("File").first()),
                  ("Edit",MenuItem(Undo).first()),
                  ("Edit",MenuItem(Redo).first()),
                  ("Edit",Separator("cut").first()),
                  ("Edit",MenuItem(Cut).first()),
                  ("Edit",MenuItem(Copy).first()),
                  ("Edit",MenuItem(Paste).first()),
                  ("Edit",Separator("paste").first()),
                  ("Edit",Separator("lastsep").last()),
                  (None,Menu("View").before("Major Mode")),
                  ("View",MenuItem(NewTab).first()),
                  ("View",Separator("tabs").first()),
                  ("View",MenuItem(NewFrame).first()),
                  ("View",MenuItem(DeleteFrame).first()),
                  ("View",Separator("begin").first()),
                  ("View",Separator("plugins").after("begin")),
                  ("View",MenuItem(SidebarShow).after("plugins")),
                  ("View",MenuItem(FrameList).last()),
                  ("View",Separator("end").last()),
                  (None,Menu("Buffers").before("Major Mode")),
                  ("Buffers",MenuItem(BufferList).first()),
                  (None,Menu("Major Mode").hide()),
                  (None,Menu("Minor Mode").hide().after("Major Mode")),
                  (None,Menu("&Help").last()),
                  )
    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)

    default_tools=((None,Menu("File").first()),
                  ("File",MenuItem(New).first()),
                  ("File",MenuItem(OpenFile).first()),
                  ("File",Separator("save").first()),
                  ("File",MenuItem(Save).first()),
                  ("File",MenuItem(SaveAs).first()),
                  ("File",MenuItem(Close).first()),
                  (None,Menu("Edit").after("File").first()),
                  ("Edit",MenuItem(Cut).first()),
                  ("Edit",MenuItem(Copy).first()),
                  ("Edit",MenuItem(Paste).first()),
                  ("Edit",Separator("cut").first()),
                  ("Edit",MenuItem(Undo).first()),
                  ("Edit",MenuItem(Redo).first()),
                  )
    def getToolBarItems(self):
        for menu,item in self.default_tools:
            yield (None,menu,item)
