#!/usr/bin/env python

"""
ProjectPane

The ProjectPane module creates a wx frame that handles file management
as well as source control.  The file management operations are similar
to those found in Windows Explorer and Apple's Finder.  You can cut, copy,
and paste files.  Create new files and directories.  And it even deletes
files to the Recycle Bin or Trash.

While the file management utilities are useful, the source control functions
are where the majority of the functionality of the ProjectPane lies.
Currently, the ProjectPane has support for CVS, GIT, and Subversion.  It
is possible to create objects to handle other source control systems
as well (see SourceControl.py).  The ProjectPane uses a non-invasive approach
to handling source control.  It doesn't check files out or browse repositories,
it simply detects directories and files that are under source control and
gives you access to the operations available to that system.  When properly
configured, files and folders under source control will display the status
of the file/folder as a badge on the icon.  The right-click menu gives you
access to source control operations such as status updates, committing,
removing, and reverting to the repository revision.

But it doesn't end there.  Probably the most powerful feature of the ProjectPane
is its diffing utitility and history window.  You can compare your copy
of a file to any previous revision using the history window.  You can also
compare any two repository revisions.  Locating revisions is easy using the
interactive search that filters the visible revisions based on the commit log
messages.

There are several configuration options that allow you to suit the ProjectPane
to your needs.  The general options are listed below:

    File Filters -- this is a space separated list of file globbing patterns
        that you can use to remove files from the tree view.  This is useful
        for eliminating backup files and intermediate build files that you
        won't be using in the editor.

    Editor Notebook Synchronization -- when a file in opened in the editor
        notebook, you can have the ProjectPane automatically show this file
        in the current projects by enabling this feature.

    Diff Program -- you can choose to use an internal visuall diffing program
        or specify an external command.

The source control options are even more extensive.  Each source control
repository has its own set of options.  You can set authentication information
and environment variables for each repository.  It is also possible to use
partial repository paths.  All settings from partial or full repository path
matches will be applied.  The longer the match string, the higher the
precedence. All settings in the Default section have the lowest priority, but
are applied to all repositories.

"""

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__revision__ = "$Revision: 620 $"
__scid__ = "$Id: ProjectPane.py 620 2008-10-02 23:10:31Z CodyPrecord $"

import sys

#-----------------------------------------------------------------------------#
# Imports
import wx
import os
import time
import threading
import stat
import fnmatch
import re
import subprocess
import shutil
import wx.lib.delayedresult

# Local Imports
import peppy.project.editra.ConfigData as ConfigDialog
import peppy.project.editra.ScCommand as ScCommand
import peppy.project.editra.FileIcons as FileIcons
from peppy.editra.eclib.eclutil import AdjustColour

# Editra Imports
profiler = None
ed_msg = None
EOL = '\n'

ODD_PROJECT_COLOR = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT)
EVEN_PROJECT_COLOR = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT)
ODD_BACKGROUND_COLOR = wx.SystemSettings_GetColour(wx.SYS_COLOUR_LISTBOX)
EVEN_BACKGROUND_COLOR = wx.SystemSettings_GetColour(wx.SYS_COLOUR_LISTBOX)

# i18n support
_ = wx.GetTranslation

#-----------------------------------------------------------------------------#

# Context Menu Id's
ID_POPUP_EDIT = wx.NewId()
ID_POPUP_OPEN = wx.NewId()
ID_POPUP_REVEAL = wx.NewId()
ID_POPUP_CUT = wx.NewId()
ID_POPUP_COPY = wx.NewId()
ID_POPUP_PASTE = wx.NewId()
ID_POPUP_REFRESH = wx.NewId()
ID_POPUP_DIFF = wx.NewId()
ID_POPUP_UPDATE = wx.NewId()
ID_POPUP_HISTORY = wx.NewId()
ID_POPUP_COMMIT = wx.NewId()
ID_POPUP_PATCH = wx.NewId()
ID_POPUP_REMOVE = wx.NewId()
ID_POPUP_REVERT = wx.NewId()
ID_POPUP_ADD = wx.NewId()
ID_POPUP_DELETE = wx.NewId()
ID_POPUP_RENAME = wx.NewId()
ID_POPUP_EXEC = wx.NewId()
ID_POPUP_NFOLDER = wx.NewId()
ID_POPUP_NMENU = wx.NewId()

# New File Menu Id's
ID_TXT_FILE = wx.NewId()
ID_C_FILE = wx.NewId()
ID_HTML_FILE = wx.NewId()
ID_PHP_FILE = wx.NewId()
ID_PY_FILE = wx.NewId()

ID_PROJECTPANE = wx.NewId()
ID_PROJECTTREE = wx.NewId()

def UnusedArg(*args):
    """Dummy method to signify unused arguments
    @param arg: anything

    """
    return len(args)

#-----------------------------------------------------------------------------#

class SimpleEvent(wx.PyCommandEvent):
    """Base event to signal that nodes need updating"""
    def __init__(self, etype, eid, value=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value

    def GetValue(self):
        """Get the events value"""
        return self._value

ppEVT_SYNC_NODES = wx.NewEventType()
EVT_SYNC_NODES = wx.PyEventBinder(ppEVT_SYNC_NODES, 1)
class SyncNodesEvent(SimpleEvent):
    """ Event to notify that nodes need updating """
    pass

#-----------------------------------------------------------------------------#

class MyTreeCtrl(wx.TreeCtrl):
    """Base class used for displaying the project files"""
    def __init__(self, parent, id_, pos, size, style, log):
        """ Create the tree control for viewing the projects """
        wx.TreeCtrl.__init__(self, parent, id_, pos, size, style)
        self.log = log

    def OnCompareItems(self, item1, item2):
        """Compare the text of two tree items"""
        tup1 = (int(not(os.path.isdir(self.GetPyData(item1)['path']))),
              self.GetItemText(item1).lower())
        tup2 = (int(not(os.path.isdir(self.GetPyData(item2)['path']))),
              self.GetItemText(item2).lower())
        #self.log.WriteText('compare: ' + t1 + ' <> ' + t2 + '\n')
        if tup1 < tup2:
            return -1
        elif tup1 == tup2:
            return 0
        else:
            return 1

#-----------------------------------------------------------------------------#

class ProjectTree(wx.Panel):
    """ Tree control for holding project nodes """

    def __init__(self, parent, log, size=wx.DefaultSize, **kwargs):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, size=size,
                          style=wx.WANTS_CHARS|wx.NO_BORDER)

        self.log = log

        global ODD_PROJECT_COLOR
        global EVEN_PROJECT_COLOR
        if wx.Platform == '__WXMAC__':
            color = AdjustColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHIGHLIGHT), 15)
        else:
            color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT)
        ODD_PROJECT_COLOR = EVEN_PROJECT_COLOR = color
        self.tree = MyTreeCtrl(self, -1, wx.DefaultPosition, wx.DefaultSize,
                               wx.TR_DEFAULT_STYLE
                               #wx.TR_HAS_BUTTONS
                               | wx.TR_EDIT_LABELS
                               | wx.TR_MULTIPLE
                               | wx.TR_HIDE_ROOT
                               | wx.TR_FULL_ROW_HIGHLIGHT
                               , self.log)

        # Load icons for use later
        self.icons = {}
        self.menuicons = {}
        self.il = None
        self._setupIcons()
        self._menu = None

        # Read configuration
        self.config = ConfigDialog.ConfigData()
        self.srcCtrl = ScCommand.SourceController(self)

        # Threads that watch directories corresponding to open folders
        self.watchers = {}
        
        # Storage for mtimes of files to be able to update status as the
        # filesystem gets modified
        self.path_mtime_storage = {}

        # Information for copy/cut/paste of files
        self.clipboard = {'files' : [], 'delete' : False}

        # Notebook tab is opening because another was closed
        self.isClosing = False

        # Create root of tree
        self.root = self.tree.AddRoot('Projects')
        self.tree.SetPyData(self.root, None)
        self.tree.SetItemImage(self.root, self.icons['folder'],
                               wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.root, self.icons['folder-open'],
                                wx.TreeItemIcon_Expanded)

        # Bind events
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, self.tree)
        #self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
        #self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)
        #self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(EVT_SYNC_NODES, self.OnSyncNode)
        self.Bind(ScCommand.EVT_STATUS, self.OnUpdateStatus)
        self.Bind(ScCommand.EVT_CMD_COMPLETE, self.OnScCommandFinish)

#        # Notebook syncronization
#        try:
#            import extern.flatnotebook as fnb
#            #self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGING,
#            mainw = self.GetGrandParent()
#            nbook = mainw.GetNotebook()
#            nbook.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
#            nbook.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.OnPageClosing)
#            ed_msg.Subscribe(self.OnThemeChange, ed_msg.EDMSG_THEME_CHANGED)
#            if hasattr(ed_msg, 'EDMSG_DSP_FONT'):
#                ed_msg.Subscribe(self.OnUpdateFont, ed_msg.EDMSG_DSP_FONT)
#        except ImportError:
#            pass

        # Setup Context Menu Handlers
        self.Bind(wx.EVT_MENU, self.onPopupEdit, id=ID_POPUP_EDIT)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupOpen(), id=ID_POPUP_OPEN)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupReveal(), id=ID_POPUP_REVEAL)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupCopy(), id=ID_POPUP_COPY)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupCut(), id=ID_POPUP_CUT)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupPaste(), id=ID_POPUP_PASTE)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scStatus(self.getSelectedNodes()),
                  id=ID_POPUP_REFRESH)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupSCDiff(), id=ID_POPUP_DIFF)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scUpdate(self.getSelectedNodes()),
                  id=ID_POPUP_UPDATE)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scHistory(self.getSelectedNodes()),
                  id=ID_POPUP_HISTORY)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scCommit(self.getSelectedNodes()),
                  id=ID_POPUP_COMMIT)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scPatch(self.getSelectedNodes()),
                  id=ID_POPUP_PATCH)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scRemove(self.getSelectedNodes()),
                  id=ID_POPUP_REMOVE)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scRevert(self.getSelectedNodes()),
                  id=ID_POPUP_REVERT)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.scAdd(self.getSelectedNodes()),
                  id=ID_POPUP_ADD)
        self.Bind(wx.EVT_MENU, self.onPopupDelete, id=ID_POPUP_DELETE)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupRename(), id=ID_POPUP_RENAME)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupExecuteCommand(), id=ID_POPUP_EXEC)
        self.Bind(wx.EVT_MENU,
                  lambda evt: self.onPopupNewFolder(), id=ID_POPUP_NFOLDER)


        self.loadProjects()

        #self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        #self.tree.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        #self.tree.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

    def __del__(self):
        """ Clean up resources """
        if ed_msg is not None:
            ed_msg.Unsubscribe(self.OnThemeChange)
            ed_msg.Unsubscribe(self.OnUpdateFont)

        # Kill all watcher threads
        for value in self.watchers.values():
            value.pop()

    def _setupIcons(self):
        """ Setup the icons used by the tree and menus """
        isz = (16, 16)
        il = wx.ImageList(isz[0], isz[1])

        folder = wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz)
        print folder
        folderopen = wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, isz)
        self.icons['folder'] = il.Add(folder)
        self.icons['folder-open'] = il.Add(folderopen)
        self.menuicons['copy'] = wx.ArtProvider_GetBitmap(wx.ART_COPY, wx.ART_OTHER, isz)
        self.menuicons['cut'] = wx.ArtProvider_GetBitmap(wx.ART_CUT, wx.ART_OTHER, isz)
        self.menuicons['paste'] = wx.ArtProvider_GetBitmap(wx.ART_PASTE, wx.ART_OTHER, isz)
        self.menuicons['delete'] = wx.ArtProvider_GetBitmap(wx.ART_DELETE, wx.ART_OTHER, isz)

        self.menuicons['blank'] = FileIcons.getBlankBitmap()
        self.menuicons['sc-commit'] = FileIcons.getScCommitBitmap()
        self.menuicons['sc-patch'] = FileIcons.getScPatchBitmap()
        self.menuicons['sc-add'] = FileIcons.getScAddBitmap()
        self.menuicons['sc-diff'] = FileIcons.getScDiffBitmap()
        self.menuicons['sc-history'] = FileIcons.getScHistoryBitmap()
        self.menuicons['sc-remove'] = FileIcons.getScRemoveBitmap()
        self.menuicons['sc-status'] = FileIcons.getScStatusBitmap()
        self.menuicons['sc-update'] = FileIcons.getScUpdateBitmap()
        self.menuicons['sc-revert'] = FileIcons.getScRevertBitmap()

        self.icons['file'] = il.Add(FileIcons.getFileBitmap())

        # Create badged icons
        for badge in ['uptodate', 'modified', 'conflict',
                      'added', 'merge', 'inaccessible']:
            badgeicon = getattr(FileIcons, 'getBadge' + badge.title() + \
                                'Bitmap')().ConvertToImage()
            badgeicon.Rescale(11, 11, wx.IMAGE_QUALITY_HIGH)
            for icotype in ['file', 'folder', 'folder-open']:
                icon = wx.MemoryDC()
                if icotype == 'file':
                    tbmp = FileIcons.getFileBitmap()
                elif icotype == 'folder':
                    tbmp = folder
                else:
                    tbmp = folderopen

                icon.SelectObject(tbmp)
                icon.SetBrush(wx.TRANSPARENT_BRUSH)
                if wx.Platform == '__WXGTK__':
                    x, y = 3, 4
                else:
                    x, y = 5, 5
                icon.DrawBitmap(wx.BitmapFromImage(badgeicon), x, y, False)
                icon.SelectObject(wx.NullBitmap)
                self.icons[icotype + '-' + badge] = il.Add(tbmp)

        self.icons['project-add'] = il.Add(FileIcons.getProjectAddBitmap())
        self.icons['project-delete'] = il.Add(FileIcons.getProjectDeleteBitmap())

        print self.icons
        print il
        self.tree.SetImageList(il)
        self.il = il # Save reference to the image list

    def saveProjects(self):
        """ Save projects to config file """
        projects = self.config.getProjects()
        self.config.clearProjects()
        for data in self.getProjectData():
            path = data['path']
            if path not in projects:
                data = data.copy()
                if 'watcher' in data:
                    del data['watcher']
                del data['path']
                self.config.addProject(path, options=data)
        self.config.save()

    def loadProjects(self):
        """ Add all projects from config to tree """
        projects = self.config.getProjects()
        for path in sorted(projects.keys()):
            self.addProject(path, options=projects[path], save=False)

    def addProject(self, path, options=dict(), save=True):
        """
        Add a project for the given path

        Required Arguments:
        path -- full path to the project directory

        Returns: tree node for the project

        """
        # Check that project exists before adding it
        if not os.path.exists(path):
            self.config.removeProject(path)
            return

        node = self.tree.AppendItem(self.tree.GetRootItem(),
                                    options.get('name', os.path.basename(path)))
        data = options.copy()
        data['path'] = path
        proj = self.tree.AppendItem(node, '')
        self.tree.AppendItem(proj, '')  # <- workaround for windows
        self.tree.SetItemHasChildren(node)
        self.tree.SetPyData(node, data)
        self.tree.SetItemImage(node, self.icons['folder'],
                               wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(node, self.icons['folder-open'],
                                wx.TreeItemIcon_Expanded)
        
        self.tree.SortChildren(self.tree.GetRootItem())

        if save:
            self.saveProjects()

        self.tree.SetItemBold(node)
        if not(self.tree.GetChildrenCount(self.root, False) % 2):
            self.tree.SetItemBackgroundColour(node, ODD_PROJECT_COLOR)
        else:
            self.tree.SetItemBackgroundColour(node, EVEN_PROJECT_COLOR)
        return node

    def removeSelectedProject(self):
        """ Remove the selected project """
        projects = self.getChildren(self.root)
        for project in self.tree.GetSelections():
            if project in projects:
                self.tree.CollapseAllChildren(project)
                self.tree.Delete(project)
        self.saveProjects()

    def getProjectPaths(self):
        """ Get the paths for all projects """
        paths = []
        for child in self.getChildren(self.root):
            paths.append(self.tree.GetPyData(child)['path'])
        return paths

    def getProjectData(self):
        """ Get the paths and data for all projects """
        paths = []
        for child in self.getChildren(self.root):
            paths.append(self.tree.GetPyData(child))
        return paths

    def getChildren(self, parent):
        """
        Return a generator to loop over all children of given node

        Required Arguments:
        parent -- node to search

        Returns: list of child nodes

        """
        if not parent.IsOk():
            return

        child, cookie = self.tree.GetFirstChild(parent)
        if not child or not child.IsOk():
            return
        yield child
        while True:
            if not parent.IsOk():
                return
            child, cookie = self.tree.GetNextChild(parent, cookie)
            if not child or not child.IsOk():
                return
            yield child

    def OnSyncNode(self, evt):
        """
        Synchronize the tree nodes with the file system changes

        Required Arguments:
        added -- files that were added
        modified -- files that were modified
        deleted -- files that were deleted
        parent -- tree node corresponding to the directory

        """
        added, modified, deleted, parent = evt.GetValue()
        children = {}
        for child in self.getChildren(parent):
            children[self.tree.GetItemText(child)] = child

        # Sort so that files in directories get operated on
        # before the directories themselves
        added = list(reversed(sorted(added)))
        modified = list(reversed(sorted(modified)))
        deleted = list(reversed(sorted(deleted)))

        updates = []

        if children:
            for item in deleted:
                if item in children:
                    node = children[item]
                    if node.IsOk() and self.tree.IsExpanded(node) and \
                       os.path.isdir(self.tree.GetPyData(node)['path']):
                        self.tree.Collapse(node)
                    if node.IsOk():
                        self.tree.Delete(node)

            # Update status on modified files
            for item in modified:
                if item not in children:
                    continue
                updates.append(children[item])

        for item in added:
            if os.path.basename(item) not in children:
                updates.append(self.addPath(parent, item))

        # Update tree icons
        items = []
        for item in updates:
            try:
                if not os.path.isdir(self.tree.GetPyData(item)['path']):
                    items.append(item)
            except ValueError:
                pass

        if items:
            self.scStatus(items)

        self.tree.SortChildren(parent)
        evt.Skip()

    def OnThemeChange(self, msg):
        """Update the icons when a theme change method has been recieved
        from Editra's preference dialog.

        """
        UnusedArg(msg)
        self._setupIcons()
        self.tree.Refresh()

    def OnUpdateFont(self, msg):
        """Update the ui font when a message comes saying to do so."""
        font = msg.GetData()
        if isinstance(font, wx.Font) and not font.IsNull():
            self.tree.SetFont(font)

    def getSelectedNodes(self):
        """ Get the selected items from the tree """
        return self.tree.GetSelections()

    def getSelectedPaths(self):
        """ Get paths associated with selected items """
        paths = []
        for item in self.getSelectedNodes():
            pdata = self.tree.GetPyData(item)
            if pdata is not None:
                paths.append(pdata['path'])
        return paths

    def OnPageClosing(self, evt):
        """ Notebook tab was closed """
        self.isClosing = True
        evt.Skip()

    def OnPageChanged(self, evt):
        """ Notebook tab was changed """
        evt.Skip()

        if not self.config.getSyncWithNotebook():
            return

        # Don't sync when a tab was just closed
        if self.isClosing:
            self.isClosing = False
            return

        notebook = evt.GetEventObject()
        pg_num = evt.GetSelection()
        txt_ctrl = notebook.GetPage(pg_num)

        # With the text control (ed_stc.EditraStc) this will return the full
        # path of the file or a wx.EmptyString if the buffer does not contain
        # an on disk file
        filename = txt_ctrl.GetFileName()
        if filename in self.getSelectedPaths():
            return
        
        self.ensurePathVisible(filename)

    def ensurePathVisible(self, filename):
        for project in self.getChildren(self.root):
            dname = self.tree.GetPyData(project)['path']
            if not os.path.isdir(dname):
                dname = os.path.dirname(dname)
            if not dname.endswith(os.sep):
                dname += os.sep
            if filename.startswith(dname):
                filename = filename[len(dname):].split(os.sep)
                if not self.tree.IsExpanded(project):
                    self.tree.Expand(project)
                folder = project
                try:
                    while filename:
                        name = filename.pop(0)
                        for item in self.getChildren(folder):
                            if self.tree.GetItemText(item) == name:
                                if not self.tree.IsExpanded(item):
                                    self.tree.Expand(item)
                                folder = item
                                continue
                except:
                    pass

                self.tree.UnselectAll()
                self.tree.EnsureVisible(folder)
                self.tree.SelectItem(folder)
                break

    def OnRightDown(self, event):
        """Select tree item on mouse button right down event"""
        item  = self.tree.HitTest(event.GetPosition())[0]
        if item:
            self.log.WriteText("OnRightClick: %s, %s, %s\n" %
                               (self.tree.GetItemText(item),
                                type(item), item.__class__))
            self.tree.SelectItem(item)

    def OnRightUp(self, event):
        """Enable label editing with right clicks"""
        item = self.tree.HitTest(event.GetPosition())[0]
        if item:
            self.log.WriteText("OnRightUp: %s (manually starting label edit)\n"
                               % self.tree.GetItemText(item))
            self.tree.EditLabel(item)

    def OnBeginEdit(self, event):
        """Begin editing of tree item"""
        self.log.WriteText("OnBeginEdit\n")
        event.Skip()

    def OnEndEdit(self, event):
        """ Finish editing tree node label """
        if event.IsEditCancelled():
            return

        node = event.GetItem()
        data = self.tree.GetPyData(node)
        path = data['path']
        # Renaming a project really just changes the label in the tree
        if self.tree.GetItemParent(node) == self.root:
            data['name'] = event.GetLabel()
            self.saveProjects()
        else:
            newpath = os.path.join(os.path.dirname(path), event.GetLabel())
            try:
                os.rename(path, newpath)
                data['path'] = newpath
            except OSError:
                pass

    def OnLeftDClick(self, event):
        """Handle mouse events and update tree"""
        item  = self.tree.HitTest(event.GetPosition())[0]
        if item:
            parent = self.tree.GetItemParent(item)
            if parent.IsOk():
                self.tree.SortChildren(parent)
        event.Skip()

    def OnSize(self, event):
        """Reset Tree dimensions"""
        UnusedArg(event)
        width, height = self.GetClientSizeTuple()
        self.tree.SetDimensions(0, 0, width, height)

    def OnItemExpanding(self, event):
        """
        When an item is expanded, track the contents of that directory

        """
        parent = event.GetItem()
        if not parent:
            return

        data = self.tree.GetPyData(parent)
        if not data:
            return

        path = data['path']
        if not os.path.isdir(path):
            return
        try:
            for item in os.listdir(path):
                self.addPath(parent, item)
        except (OSError, IOError):
            self.tree.SetItemImage(parent, self.icons['folder-inaccessible'],
                                   wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(parent, self.icons['folder-inaccessible'],
                                   wx.TreeItemIcon_Expanded)
            self.tree.Delete(self.tree.GetFirstChild(parent)[0])
            return

        # Delete dummy node from self.addFolder
        self.tree.Delete(self.tree.GetFirstChild(parent)[0])
        self.tree.SortChildren(parent)
        
        self.addDirectoryWatcher(parent)
        self.scStatus([parent])

    def scAdd(self, nodes):
        """ Send an add to repository command to current control system """
        self.scCommand(nodes, 'add')

    def scRemove(self, nodes):
        """
        Send an remove from repository command to current control system

        """
        self.scCommand(nodes, 'remove')

    def scUpdate(self, nodes):
        """ Send an update command to current control system """
        self.scCommand(nodes, 'update')

    def scRevert(self, nodes):
        """ Send an revert command to current control system """
        self.scCommand(nodes, 'revert')

    def scCheckout(self, nodes):
        """ Send an checkout command to current control system """
        self.scCommand(nodes, 'checkout')

    def scStatus(self, nodes):
        """ Send an status command to current control system """
        self.scCommand(nodes, 'status')

    def scHistory(self, nodes):
        """ Open source control history window """
        if not nodes:
            return

        for node in self.getSelectedNodes():
            data = self.tree.GetPyData(node)
            win = HistoryWindow(self, data['path'], node, data)
            win.Show()

    def scCommit(self, nodes):
        """ Commit files to source control """
        if not self.isSingleRepository(nodes):
            return

        while True:
            paths = list()
            for node in nodes:
                try:
                    data = self.tree.GetPyData(node)
                except:
                    data = {}

                if data.get('sclock', None):
                    continue

                if 'path' not in data:
                    continue
                else:
                    paths.append(data['path'])

            ted = ProjCmnDlg.CommitDialog(self, _("Commit Dialog"),
                                          _("Enter your commit message:"),
                                          paths)

            message = u''
            if ted.ShowModal() == wx.ID_OK:
                message = ted.GetValue().strip()

            ted.Destroy()
            if message:
                break

        self.scCommand(nodes, 'commit', message=message)

    def scPatch(self, nodes):
        """ Make patch files for the given nodes """
        self.scCommand(nodes, 'makePatch', callback=self.openPatches)

    def openPatches(self, results):
        """Open the patches in Editra's notebook this method is called as
        a callback from the ScCommand worker thread.
        Parameter -- results list of tuples [(filename, patch text)]

        """
        for result in results:
            wx.CallAfter(self.OpenPatchBuffer, result[1])

    def isSingleRepository(self, nodes):
        """
        Are all selected files from the same repository ?

        Required Arguments:
        nodes -- list of nodes to test

        Returns: boolean indicating if all nodes are in the same repository
            (True), or if they are not (False).

        """
        paths = list()
        for node in nodes:
            # Get node data
            try:
                path = self.tree.GetPyData(node)['path']
            except:
                continue
            paths.append(path)

        if not self.srcCtrl.IsSingleRepository(paths):
            dlg = wx.MessageDialog(self,
               _('You can not execute source control commands across multiple repositories.'),
               _('Selected files are from multiple repositories'),
               style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return True

    def scCommand(self, nodes, command, **options):
        """
        Run a source control command

        Required Arguments:
        nodes -- selected tree nodes
        command -- name of command type to run

        """
        if not self.isSingleRepository(nodes):
            return

        try:
            self.StartBusy()
        except:
            pass

        # Validate nodes
        s_nodes = list()
        for node in nodes:
            if not node.IsOk():
                continue

            # Get node data
            try:
                data = self.tree.GetPyData(node)
            except:
                data = {}

            s_nodes.append((node, data))

        # Check for a callback argument
        callb = None
        if 'callback' in options:
            callb = options['callback']
            del options['callback']
        
        self.srcCtrl.ScCommand(s_nodes, command, callb, **options)

    def OnUpdateStatus(self, evt):
        """ Apply status updates to tree view """
        # The event value is a method for preparing the update data
        args = evt.GetValue()
        if args is not None:
            updates = self.prepUpdates(*args)
        else:
            updates = list()

        for update in list(set(updates)):
            update = list(update)
            method = update.pop(0)
            try:
                if update[0].IsOk():
                    method(*update)
            except:
                pass

    def prepUpdates(self, node, data, status, sc):
        """Prepare the tree updates
        @param node: node to update
        @param data: node data
        @param status: source control status dictionary
        @param sc: Source control system

        """
        updates = list()
        # Update the icons for the file nodes
        if os.path.isdir(data['path']) and node.IsOk():
            for child in self.getChildren(node):
                text = self.tree.GetItemText(child)
                if text not in status:
                    continue

                if os.path.isdir(os.path.join(data['path'], text)):
                    # Closed folder icon
                    icon = self.icons.get('folder-' + \
                                          status[text].get('status', ''))
                    if icon and child.IsOk():
                        updates.append((self.tree.SetItemImage, child,
                                        icon, wx.TreeItemIcon_Normal))
                    # Open folder icon
                    icon = self.icons.get('folder-open-' + \
                                          status[text].get('status', ''))
                    if icon and child.IsOk():
                        updates.append((self.tree.SetItemImage, child,
                                        icon, wx.TreeItemIcon_Expanded))
                    # Update children status if opened
                    if child.IsOk() and self.tree.IsExpanded(child):
                        self.srcCtrl.StatusWithTimeout(sc,
                                                       child,
                                                       self.tree.GetPyData(child))
                else:
                    icon = self.icons.get('file-' + \
                                          status[text].get('status', ''))
                    if icon and child.IsOk():
                        updates.append((self.tree.SetItemImage, child,
                                        icon, wx.TreeItemIcon_Normal))
                    #if 'tag' in status[text]:
                    #    updates.append((self.tree.SetToolTip,
                    #                   wx.ToolTip('Tag: %s' % \
                    #                               status[text]['tag'])))
        elif node.IsOk():
            text = self.tree.GetItemText(node)
            if text in status:
                icon = self.icons.get('file-' + status[text].get('status', ''))
                if icon and node.IsOk():
                    updates.append((self.tree.SetItemImage, node,
                                    icon, wx.TreeItemIcon_Normal))
                #if 'tag' in status[text]:
                #    updates.append((self.tree.SetToolTip,
                #                   wx.ToolTip('Tag: %s' % \
                #                              status[text]['tag'])))
        return updates

    def OpenPatchBuffer(self, patch):
        """ Opening patch texts in a new buffer in Editra
        @param patches: patch (string)

        """
        # The event value holds the text
        mainw = self.GetParent().GetOwnerWindow()
        if hasattr(mainw, 'GetNotebook'):
            nbook = mainw.GetNotebook()
            nbook.NewPage()
            ctrl = nbook.GetCurrentCtrl()
            ctrl.SetText(patch)
            ctrl.FindLexer('diff')

    def OnScCommandFinish(self, evt):
        """ Stops progress indicator when source control command is finished """
        UnusedArg(evt)

        try:
            self.StopBusy()
        except wx.PyDeadObjectError:
            pass

#        cmd = evt.GetValue()

    def endPaste(self, delayedresult):
        """ Stops progress indicator when paste is finished """
        UnusedArg(delayedresult)
        try:
            self.StopBusy()
        except wx.PyDeadObjectError:
            pass

    def compareToPrevious(self, node):
        """ Use opendiff to compare playpen version to repository version """
        try:
            path = self.tree.GetPyData(node)['path']
        except TypeError:
            return

        # Only do files
        if os.path.isdir(path):
            for child in self.getChildren(node):
                self.compareToPrevious(child)
            return

        # Run the actual Diff job
        self.srcCtrl.CompareRevisions(path)

    def addDirectoryWatcher(self, node):
        """
        Add a directory watcher thread to the given node

        Directory watchers keep tree nodes and the file system
        constantly in sync

        Required Arguments:
        node -- the tree node to keep in sync

        """
        # Calling GetPyData on an empty node can cause an
        # AssertionError on windows for some reason so trap it
        # an don't add the watcher
        try:
            data = self.tree.GetPyData(node)
        except wx.PyAssertionError:
            return

        path = data['path']
        # Start a directory watcher to keep branch in sync.
        # When the flag variable is emptied, the thread stops.
        flag = [1]
        thread = threading.Thread(target=self.watchDirectory,
                                           args=(path,),
                                           kwargs={'flag':flag,
                                                   'data':node})
        thread.flag = flag
        thread.start()
        #data['watcher'] = thread
        #self.watchers[data['watcher']] = flag
        #print 'WATCHING', path, self.tree.GetItemText(node)

    def addPath(self, parent, name):
        """
        Add a file system path to the given node

        The new node can be a directory or a file.
        Either one will be handled appropriately.

        Required Arguments:
        parent -- tree node to add the new node to
        name -- name of the item to add

        Returns: newly created node or None if the path isn't a file or
            directory.  It will also return None if the path is being
            filtered out.

        """
        if name.endswith('\r'):
            return

        for pattern in self.config.getFilters():
            if fnmatch.fnmatchcase(name, pattern):
                return

        # On Windows (again...) this can for some reason cause an assertion
        # under certain conditions such as running an svn update from an
        # external program.
        # TODO: find real cause for these issues instead of just trapping them
        try:
            data = self.tree.GetPyData(parent)
        except wx.PyAssertionError:
            data = None

        if data is None:
            return

        parentpath = data['path']
        itempath = os.path.join(parentpath, name)
        if os.path.isdir(itempath):
            node = self.addFolder(parent, name)
        else:
            node = self.addFile(parent, name)
        if self.tree.GetItemParent(parent) == self.root:
            if self.tree.GetItemBackgroundColour(parent) == ODD_PROJECT_COLOR:
                self.tree.SetItemBackgroundColour(node, ODD_BACKGROUND_COLOR)
            else:
                self.tree.SetItemBackgroundColour(node, EVEN_BACKGROUND_COLOR)
        else:
            self.tree.SetItemBackgroundColour(node, self.tree.GetItemBackgroundColour(parent))
        return node

    def addFolder(self, parent, name):
        """
        Add a folder to the given tree node

        Required Arguments:
        parent -- node to add the folder to
        name -- name of node to add

        Returns: newly created node

        """
        parentpath = self.tree.GetPyData(parent)['path']
        node = self.tree.AppendItem(parent, name)
        # Work around Windows bug where folders cannot expand unless it
        # has children.  This item is deleted when the folder is expanded.
        self.tree.AppendItem(node, '')
        fpath = os.path.join(parentpath, name)
        if len(os.listdir(fpath)):
            self.tree.SetItemHasChildren(node)

        self.tree.SetPyData(node, {'path' : fpath})
        self.tree.SetItemImage(node, self.icons['folder'],
                               wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(node, self.icons['folder-open'],
                               wx.TreeItemIcon_Expanded)

        return node

    def addFile(self, parent, name):
        """
        Add a file to the given tree node

        Required Arguments:
        parent -- node to add the file to
        name -- name of node to add

        Returns: newly created node

        """
        parentpath = self.tree.GetPyData(parent)['path']
        node = self.tree.AppendItem(parent, name)
        self.tree.SetPyData(node, {'path':os.path.join(parentpath, name)})
        self.tree.SetItemImage(node, self.icons['file'], wx.TreeItemIcon_Normal)
        return node

    def OnItemCollapsed(self, event):
        """
        When an item is collapsed, quit tracking the folder contents

        """
        item = event.GetItem()
        if not item:
            return

        # Collapse all children first so that their watchers get deleted
        self.tree.CollapseAllChildren(item)

        self.tree.DeleteChildren(item)
        self.tree.AppendItem(item, '')  # <- Dummy node workaround for MSW

        # Kill the watcher thread
        data = self.tree.GetPyData(item)
        if data and 'watcher' in data:
            data['watcher'].flag.pop()
            del self.watchers[data['watcher']]
            del data['watcher']

    def OnSelChanged(self, event):
        """Update what item is currently selected"""
        self.item = event.GetItem()
        if self.item:
            self.log.WriteText("OnSelChanged: %s\n" % \
                                self.tree.GetItemText(self.item))
            if wx.Platform == '__WXMSW__':
                self.log.WriteText("BoundingRect: %s\n" %
                                   self.tree.GetBoundingRect(self.item, True))
            #items = self.tree.GetSelections()
            #print map(self.tree.GetItemText, items)
        event.Skip()

    def origOnContextMenu(self, event):
        """ Handle showing context menu to show the commands """
        #self.log.WriteText("OnContextMenu\n")
        UnusedArg(event)

        # Destroy any existing menu
        if self._menu is not None:
            self._menu.Destroy()
            self._menu = None

        paths = self.getSelectedPaths()

        # Do we have something to paste
        pastable = False
        if len(paths) == 1 and os.path.isdir(paths[0]):
            pastable = not (not (self.clipboard['files']))

        # Is directory controlled by source control
        scenabled = False
        for item in paths:
            if self.srcCtrl.GetSCSystem(item):
                scenabled = True
                break

        # Add or remove
        if scenabled:
            addremove = (ID_POPUP_REMOVE,
                         _("Remove from repository"), 'sc-remove', True)
        else:
            addremove = (ID_POPUP_ADD, _("Add to repository"), 'sc-add', True)

        # New file / folder submenu
        newmenu = wx.Menu()
        newmenu.AppendItem(wx.MenuItem(newmenu, ID_POPUP_NFOLDER, _('Folder')))
        newmenu.AppendSeparator()
        for menu_id, ftype in getFileTypes().iteritems():
            newmenu.AppendItem(wx.MenuItem(newmenu, menu_id, ftype['lbl']))
            self.Bind(wx.EVT_MENU, self.onPopupNewFile, id=menu_id)

        # make a menu
        menu = wx.Menu()
        items = [
            (ID_POPUP_EDIT, _('Edit'), None, True),
            (ID_POPUP_OPEN, _('Open'), None, True),
            (ID_POPUP_REVEAL, _('Open enclosing folder'), None, True),
            (ID_POPUP_NMENU, _('New...'), newmenu, True),
            (None, None, None, None),
            (ID_POPUP_CUT, _('Cut'), 'cut', True),
            (ID_POPUP_COPY, _('Copy'), 'copy', True),
            (ID_POPUP_PASTE, _('Paste'), 'paste', pastable),
            (None, None, None, None),
            (ID_POPUP_EXEC, _('Execute command...'), None, True),
            (None, None, None, None),
            #(ID_POPUP_RENAME, _('Rename'), None, True),
            #(None, None, None, None),
            (ID_POPUP_REFRESH, _("Refresh status"), 'sc-status', scenabled),
            (ID_POPUP_UPDATE, _("Update"), 'sc-update', scenabled),
            (ID_POPUP_DIFF, _("Compare to previous version"),
            'sc-diff', scenabled),
            (ID_POPUP_HISTORY, _("Show revision history"),
             'sc-history', scenabled),
            (ID_POPUP_COMMIT, _("Commit changes"), 'sc-commit', scenabled),
            (ID_POPUP_PATCH, _("Make Patch"), 'sc-patch', scenabled),
            (ID_POPUP_REVERT, _("Revert to repository version"),
             'sc-revert', scenabled),
            addremove,
            (None, None, None, None),
            (ID_POPUP_DELETE, _("Move to %(trash)s") % dict(trash=TRASH),
             'delete', True),
        ]
        for menu_id, title, icon, enabled in items:
            if menu_id is None:
                menu.AppendSeparator()
                continue
            elif icon is not None and not isinstance(icon, basestring):
                item = menu.AppendMenu(menu_id, title, icon)
                item.SetBitmap(self.menuicons['blank'])
                continue

            item = wx.MenuItem(menu, menu_id, _(title))
            if icon:
                item.SetBitmap(self.menuicons[icon])
            else:
                item.SetBitmap(self.menuicons['blank'])
            menu.AppendItem(item)
            item.Enable(enabled)

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self._menu = menu
        self.PopupMenu(self._menu)

    def onPopupNewFolder(self):
        """ Create a new folder from popup menu selection """
        # See onPopupNewFile
        nodes = self.getSelectedNodes()
        if len(nodes):
            node = nodes[0]
        else:
            return

        path = self.tree.GetPyData(node)['path']
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        newpath = os.path.join(path, _("Untitled Folder"))
        i = 1
        while os.path.exists(newpath):
            newpath = re.sub(u'-\d+$', u'', newpath)
            newpath += u'-%d' % i
            i += 1
            #print newpath
        #print newpath
        os.makedirs(newpath)

    def onPopupNewFile(self, event):
        """ Create a new file """
        # Some errors have come in showing that this can under some use cases
        # be called when there is no selection, so check that there is at least
        # one selected node before trying to get it from the list
        nodes = self.getSelectedNodes()
        if len(nodes):
            node = nodes[0]
        else:
            return

        path = self.tree.GetPyData(node)['path']
        if not os.path.isdir(path):
            path = os.path.dirname(path)

        # Determine file type
        e_id = event.GetId()
        file_types = getFileTypes()
        if not file_types.has_key(e_id):
            return

        # Get informatio about file type
        info = file_types[e_id]

        # Create unique name
        newpath = os.path.join(path, 'untitled file' + info['ext'])
        i = 1
        while os.path.exists(newpath):
            newpath = os.path.splitext(newpath)[0]
            newpath = re.sub(r'-\d+$', r'', newpath)
            newpath += '-%d%s' % (i, info['ext'])
            i += 1

        # Write template info
        f_handle = open(newpath, 'w')
        f_handle.write(info.get('template', '').replace('\n', EOL))
        f_handle.close()

    def onPopupEdit(self, event):
        """ Open the current file in the editor """
        return self.OnActivate(event)

    def onPopupExecuteCommand(self):
        """ Execute commands on file system tree """

        ted = wx.TextEntryDialog(self,
              _('The following command will be executed on all selected\n' \
                'files and files contained in selected directories.'),
              _('Enter command to execute on all files'))

        if ted.ShowModal() != wx.ID_OK:
            return

        command = ted.GetValue().strip()
        if not command:
            return

        for item in self.getSelectedPaths():
            if os.path.isdir(item):
                for root, dirs, files in os.walk(item):
                    for fname in files:
                        #print command, os.path.join(root,f)
                        os.system('%s "%s"' % \
                                  (command, os.path.join(root, fname)))
            else:
                #print command, item
                os.system('%s "%s"' % (command, item))

    def onPopupOpen(self):
        """ Open the current file using Finder """
        for fname in self.getSelectedPaths():
            subprocess.call([FILEMAN_CMD, fname])

    def onPopupReveal(self):
        """ Open the Finder to the parent directory """
        for fname in self.getSelectedPaths():
            subprocess.call([FILEMAN_CMD, os.path.dirname(fname)])

    def onPopupRename(self):
        """ Rename the current selection """
        for node in self.getSelectedNodes():
            self.tree.EditLabel(node)

    def onPopupSCDiff(self):
        """ Diff the file to the file in the repository """
        for node in self.getSelectedNodes():
            self.compareToPrevious(node)

    def onPopupCut(self):
        """ Cut the files to the clipboard """
        self.clipboard['files'] = self.getSelectedPaths()
        self.clipboard['delete'] = True
        for item in self.getSelectedNodes():
            self.tree.SetItemTextColour(item, wx.Colour(192, 192, 192))

    def onPopupCopy(self):
        """ Copy the files to the clipboard """
        self.clipboard['files'] = self.getSelectedPaths()
        self.clipboard['delete'] = False

    def onPopupPaste(self):
        """ Paste the files to the selected directory """
        try:
            self.StartBusy()
        except:
            pass

        dest = self.getSelectedPaths()[0]
        if not os.path.isdir(dest):
            dest = os.path.dirname(dest)

        def run(dest):
            """Run the paste job"""
            delete = self.clipboard['delete']
            self.clipboard['delete'] = False
            newclipboard = []
            for i, fname in enumerate(self.clipboard['files']):
                try:
                    newpath = os.path.join(dest, os.path.basename(fname))
                    newclipboard.append(newpath)
                    if delete:
                        shutil.move(fname, newpath)
                    else:
                        if os.path.isdir(fname):
                            shutil.copytree(fname, newpath, True)
                        else:
                            shutil.copy2(fname, newpath)
                except (OSError, IOError), msg:
                    newclipboard.pop()
                    newclipboard.append(fname)
                    # Do we have more files to copy/move?
                    msgmap = dict(filename=fname, errmsg=msg)
                    if i < (len(self.clipboard['files'])-1):
                        rc = wx.MessageDialog(self,
                          _("The system returned the following message when " \
                            "attempting to move/copy %(filename)s: %(errmsg)s. " \
                            "Do you wish to continue?") % msgmap,
                          _('Error occurred when copying/moving files'),
                          style=wx.YES_NO|wx.YES_DEFAULT|wx.ICON_ERROR).ShowModal()
                        if rc == wx.ID_NO:
                            break
                    else:
                        rc = wx.MessageDialog(self,
                          _("The system returned the following message when " \
                            "attempting to move/copy %(filename)s: %(errmsg)s.") % msgmap,
                          _("Error occurred when copying/moving files"),
                          style=wx.OK|wx.ICON_ERROR).ShowModal()
            self.clipboard['files'] = newclipboard

        wx.lib.delayedresult.startWorker(self.endPaste, run, wargs=(dest,))

    def onPopupDelete(self, event):
        """ Delete selected files/directories """
        if event.GetId() != ID_POPUP_DELETE:
            event.Skip()
            return

        projects = self.getChildren(self.root)
        selections = [(x, self.tree.GetPyData(x)['path'])
                      for x in self.getSelectedNodes()]

        def delete():
            """Does the delete"""
            # Delete previously cut files
            for node, path in selections:
                try:
                    Trash.moveToTrash(path)
                except Exception, msg:
                    rc = wx.MessageDialog(self,
                      _('An error occurred when attempting to remove ') + \
                      msg[1] + _('. Do you wish to continue?'),
                      _('Error occurred when removing files'),
                      style=wx.YES_NO|wx.YES_DEFAULT|wx.ICON_ERROR).ShowModal()
                    if rc == wx.ID_NO:
                        break
                    continue

                # If node is a project, remove it
                if node in projects:
                    self.tree.Collapse(node)
                    self.tree.Delete(node)
                    self.saveProjects()

        if selections:
            threading.Thread(target=delete).start()

    def OnActivate(self, event):
        """
        Handles item activations events. (i.e double clicked or
        enter is hit) and passes the clicked on file to be opened in
        the notebook.

        """
        UnusedArg(event)

        files = []
        for node in self.getSelectedNodes():
            fname = self.tree.GetPyData(node)['path']
            try:
                status = os.stat(fname)[0]
                if stat.S_ISDIR(status):
                    if self.tree.IsExpanded(node):
                        self.tree.Collapse(node)
                    else:
                        self.tree.Expand(node)
                elif stat.S_ISREG(status) or stat.S_ISLNK(status):
                    files.append(fname)
            except (IOError, OSError):
                pass

        self.openFiles(files)

    def getCurrentPathMTime(self, path):
        return self.path_mtime_storage.get(path, {})

    def updatePathMTime(self, path):
        mtimes = self.getPathMTime(path)
        self.path_mtime_storage[path] = mtimes
        return mtimes

    @staticmethod
    def getPathMTime(path):
        """ Get last modified times of all items in path """
        fileinfo = {}
        try:
            for item in os.listdir(path):
                try:
                    fileinfo[item] = os.stat(os.path.join(path, item))[stat.ST_MTIME]
                except OSError:
                    pass
        except OSError:
            pass
        return fileinfo

    def watchDirectory(self, path, data=None, flag=True, delay=2):
        """
        Watch a directory for changes

        Required Arguments:
        path -- the path to watch
        func -- callback function with four arguments for added, modified,
                and deleted files and the data passed in
        data -- arbitrary data that will be passed to `func`
        flag -- if flag evaluates to false, the function should exit
        delay -- number of seconds between each poll

        """
        # Continuously compare directory listings for
        delay = max(1, int(delay))
        old = self.getCurrentPathMTime(path)
        
        while True:
            if not flag:
                return
            modified, added = [], []
            new = self.updatePathMTime(path)
            for key, mtime in new.items():
                if key not in old:
                    added.append(key)
                else:
                    if mtime > old[key]:
                        modified.append(key)
                    del old[key]
            deleted = old.keys()

            # Set file list up for next pass
            old = new

            # Do callback if something changed
            if added or modified or deleted:
                evt = SyncNodesEvent(ppEVT_SYNC_NODES, self.GetId(),
                                       (added, modified, deleted, data))
                wx.CallAfter(wx.PostEvent, self, evt)

            # Check for the kill signal every second until the delay is finished
            for i in xrange(delay):
                if not flag:
                    return
                time.sleep(1)
                
            # in peppy, the 'while True' loop is not needed because the view
            # doesn't stay visible all the time.  This watcher thread is
            # only run when needed: when initially expanding a node, or when
            # redisplaying the popup after it's been hidden.
            break

#-----------------------------------------------------------------------------#
if __name__ == '__main__':
    class MyApp(wx.App):
        """ Test Application """
        def OnInit(self):
            """ Frame for showing and testing projects outside of Editra """
            frame = wx.Frame(None, -1, "Hello from wxPython")
            ProjectPane(frame)
            frame.Show(True)
            self.SetTopWindow(frame)
            return True

    APP = MyApp(0)
    APP.MainLoop()

