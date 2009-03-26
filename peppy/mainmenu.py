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
    """Open a new tab
    
    Open a blank tab in the current frame.
    """
    alias = "new-tab"
    name = "New Tab"
    default_menu = ("File/New", 1)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:blank", force_new_tab=True)

class CloseTab(SelectAction):
    """Close the current tab"""
    alias = "close-tab"
    name = "Close Tab"

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        tab = self.popup_options['context_tab']
        self.frame.tabs.closeTab(tab)

class MoveTabToNewWindow(SelectAction):
    """Move the current tab to a new window
    
    Creates a new window and moves the current tab from the current window to
    the newly created window.
    """
    alias = "move-tab-to-new-window"
    name = "Move Tab to New Window"
    default_menu = ("Window", 150)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        # If it's called from a popup, use the tab on which it was clicked, not
        # the current mode
        if self.popup_options is not None:
            mode = self.popup_options['mode']
        else:
            mode = self.mode
        BufferFrame(buffer=mode.buffer)
        wx.CallAfter(self.frame.tabs.closeWrapper, mode)

class New(SelectAction):
    """New plain text file
    
    Opens a new tab with a new blank document in Fundamental mode.  This
    document will not be linked to any file on the computer, so it must be
    saved using the L{SaveAs} menu item.
    """
    alias = "new-file"
    name = "Text file"
    icon = "icons/page_white_text_new.png"
    default_menu = (("File/New", 1), -99)
    key_bindings = {'win': "C-n", 'mac': "C-n"}
    osx_minimal_menu = True

    def action(self, index=-1, multiplier=1):
        url = getNewUntitled()
        self.frame.open(url)


class OpenFileGUIMixin(object):
    def openFiles(self, paths):
        for path in paths:
            assert self.dprint("open file %s:" % path)
            # Force the loader to use the file: protocol
            self.frame.open("file:%s" % path)

    def showFileDialog(self):
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
            return paths

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

    def action(self, index=-1, multiplier=1):
        paths = self.showFileDialog()
        if paths:
            self.openFiles(paths)

class OpenFileGUI(OpenFileGUIMixin, SelectAction):
    """Open a file
    
    Opens a file in a new tab in the current window, using the standard "File
    Open" dialog of the platform on which peppy is running.
    """
    alias = "gui-find-file"
    name = "Open File..."
    icon = "icons/folder_page.png"
    default_menu = (("File/Open", 2), 1) 
    key_bindings = {'default': "C-o", 'emacs': "C-x C-S-f" }
    osx_minimal_menu = True

class OpenFileNewWindowGUI(OpenFileGUIMixin, SelectAction):
    """Open a file in a new window
    
    Same as L{OpenFileGUI} except the selected file is opened in a new window
    instead of in a tab in the current window.
    """
    alias = "gui-find-file-new-window"
    name = "Open File in New Window..."
    default_menu = (("File/Open", 2), 2) 

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
    """Open a file using filename completion
    
    Emacs compatibility command that emulates 'find-file'.  This uses the
    minibuffer and tab-completion to provide an alternate way to load files
    rather than using the file open dialog.
    """
    alias = "find-file"
    name = "Open File Using Minibuffer..."
    default_menu = ("File/Open", 10)
    key_bindings = {'emacs': "C-x C-f", }

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
    """Save with new filename using the minibuffer
    
    Emacs compatibility command that emulates 'write-file'.  This uses the
    minibuffer to provide means to enter a filename without using the file
    save dialog.
    """
    alias = "write-file"
    name = "Save &As..."
    icon = "icons/disk_edit.png"
    key_bindings = {'emacs': "C-x C-w",}
    
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
    """Open a file using URL name completion
    
    Similar to L{OpenFile} except allows filename completion using URI schemes
    other than C{file://}
    """
    name = "Open URL Using Minibuffer..."
    default_menu = ("File/Open", 20)
    key_bindings = {'emacs': "C-x C-a", }

    def action(self, index=-1, multiplier=1):
        cwd = str(self.frame.cwd(use_vfs=True))
        self.dprint(cwd)
        minibuffer = URLMinibuffer(self.mode, self, label="Find URL:",
                                    initial = cwd)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        self.frame.open(text)

class SaveURL(SelectAction):
    """Write to a new URL using name completion
    
    Similar to L{SaveAs} except allows filename completion using URI schemes
    other than C{file://}
    """
    alias = "write-url"
    name = "Save to URL Using Minibuffer..."
    key_bindings = {'emacs': "C-x C-y", }

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


class Properties(SelectAction):
    """Display properties of the currently open document"""
    name = "Properties"
    default_menu = ("File", -990)
    
    def action(self, index=-1, multiplier=1):
        pairs = self.mode.getProperties()
        text = "\n".join("%s: %s" % (k,v) for k,v in pairs) + "\n"
        Publisher().sendMessage('peppy.log.info', text)


class Exit(SelectAction):
    """Quit the program.
    
    Exits peppy, prompting to save any files that have been modified but not
    yet saved.
    """
    alias = "exit-peppy-to-return-again-soon"
    name = "E&xit"
    if wx.Platform == '__WXMAC__':
        # Only add the stock ID where we must: on the mac.  It interferes
        # with the emacs style keybindings, and there's no way to disable the
        # automatic Ctrl-Q keybinding AFAICT
        stock_id = wx.ID_EXIT
        key_bindings = {'default': "C-q"}
    else:
        key_bindings = {'default': "C-q", 'emacs': "C-x C-c"}
    default_menu = ("File", -1000)
    osx_minimal_menu = True
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().quit()


class CloseBuffer(SelectAction):
    """Delete the current document from memory
    
    Peppy is a document-centric editor, not a window-centric editor.  A tab that
    shows a view of a document can be deleted, but the document itself is kept
    in memory (and therefore shows up in the Documents menu) until explicitly
    removed using this action.
    
    Note for advanced users: there are other ways to delete a document from
    memory, including the L{ListAllDocuments} menu item.
    """
    alias = "close-buffer"
    name = "&Close Document"
    icon = "icons/cross.png"
    default_menu = ("File", 890)
    key_bindings = {'emacs': "C-x k"}

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.closeBuffer()

class Revert(SelectAction):
    """Revert to last saved version
    
    Throw away all current edits and revert the document to the last saved
    version.
    """
    alias = "revert-buffer"
    name = "&Revert"
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
    """Save the current file
    
    Saves the changes in the current file to the same filename as was loaded
    in.  A backup of the original file can optionally be saved by setting the
    options in the L{BackupFiles} item in the Preferences dialog.
    """
    alias = "save-buffer"
    name = "&Save..."
    icon = "icons/disk.png"
    default_menu = ("File", -801)
    key_bindings = {'default': "C-s", 'emacs': "C-x C-s",}

    def isEnabled(self):
        if self.mode.buffer.readonly or not self.mode.buffer.stc.CanSave():
            return False
        return True

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mode.save()

class SaveAsGUI(SelectAction):
    """Save with new filename using the file save dialog box
    
    The data in the original filename is left unchanged.
    """
    alias = "save-buffer-as"
    name = "Save &As..."
    icon = "icons/disk_edit.png"
    default_menu = ("File", 802)
    key_bindings = {'default': "C-S-s"}
    
    def isEnabled(self):
        return self.mode.buffer.stc.CanSave()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))

        paths=None
        if self.mode.buffer:
            saveas = self.frame.showSaveAs("Save File")
            if saveas:
                self.mode.save(saveas)


class RunMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'startInterpreter')
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and not hasattr(self.mode, 'process')

class RunScript(RunMixin, SelectAction):
    """Run this script through the interpreter
    
    If an interpreter has been set up for this major mode, this action causes
    the file to be saved and the interpreter to run using this file as input.
    Interpreter settings are controlled using the L{JobControlMixin} settings
    of the major mode in the Preferences dialog.
    """
    alias = "run-script"
    name = "Run"
    icon = 'icons/script_go.png'
    default_menu = ("Tools", 1)
    key_bindings = {'default': "F5"}

    def action(self, index=-1, multiplier=1):
        self.mode.startInterpreter()

class RunScriptWithArgs(RunMixin, SelectAction):
    """Run this script through the interpreter with optional arguments
    
    Like L{RunScript}, except provides the capability to specify optional
    arguments to the command line that runs the interpreter.
    """
    alias = "run-script-with-args"
    name = "Run with Args"
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
    """Run an external program on this file
    
    Similar to L{RunScript} except it provides the opportunity to specify the
    entire command line used to process the current file.
    """
    alias = "run-filter"
    name = "Run Filter"
    default_menu = ("Tools", 3)

    def action(self, index=-1, multiplier=1):
        if self.name in self.mode.class_storage:
            last = self.mode.class_storage[self.name]
        else:
            last = ''
        minibuffer = TextMinibuffer(self.mode, self, label="Command line:",
                                    initial = last)
        self.mode.setMinibuffer(minibuffer)
        self.mode.setStatusText("Enter command line, %s will be replaced by full path to file")

    def processMinibuffer(self, minibuffer, mode, text):
        self.mode.class_storage[self.name] = text
        self.mode.startCommandLine(text, expand=True)

class StopScript(RunMixin, SelectAction):
    """Stop the currently running script
    
    If an interpreter is processing the current document, it can be forcefully
    stopped using this command.
    """
    alias = "stop-script"
    name = "Stop"
    icon = 'icons/stop.png'
    default_menu = ("Tools", 9)
    key_bindings = {'win': "C-CANCEL", 'emacs': "C-CANCEL", 'mac': 'C-.'}
    
    def isEnabled(self):
        return hasattr(self.mode, 'startInterpreter') and hasattr(self.mode, 'process')

    def action(self, index=-1, multiplier=1):
        self.mode.stopInterpreter()


class Undo(STCModificationAction):
    """Undo the last undoable action
    
    Note that not all actions are undoable.
    """
    alias = "undo"
    name = "Undo"
    icon = "icons/undo.png"
    default_menu = ("Edit", 0)
    key_bindings = {'default': "C-z", 'emacs': ["C-/", "C-S--",]}
    
    def isActionAvailable(self):
        return self.mode.CanUndo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.Undo()


class Redo(STCModificationAction):
    """Redo the last action that was undone
    
    Applies the last action that was unapplied from the most recent L{Undo}.
    """
    alias = "redo"
    name = "Redo"
    icon = "icons/redo.png"
    default_menu = ("Edit", 1)
    key_bindings = {'win': "C-y", 'emacs': "C-S-/", 'mac': "C-S-z"}
    
    def isActionAvailable(self):
        return self.mode.CanRedo()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        return self.mode.Redo()

class Cut(STCModificationAction):
    """Cut the current selection
    
    Removes the current selection and places it in the clipboard for later
    L{Paste}.
    """
    alias = "cut-primary-selection"
    name = "Cut"
    icon = "icons/cut.png"
    default_menu = ("Edit", -100)
    key_bindings = {'win': "C-x", 'mac': "C-x", 'emacs': "C-w"}

    def isActionAvailable(self):
        return self.mode.CanCut()

    def action(self, index=-1, multiplier=1):
        return self.mode.Cut()

class Copy(BufferBusyActionMixin, SelectAction):
    """Copy the current selection
    
    Copies the current selection and places it in the clipboard for later
    L{Paste}.
    """
    alias = "copy-primary-selection"
    name = "Copy"
    icon = "icons/page_copy.png"
    default_menu = ("Edit", 101)
    key_bindings = {'win': "C-c", 'mac': "C-c", 'emacs': "M-w"}
    key_needs_focus = True
    
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'CanCopy')

    def isActionAvailable(self):
        return self.mode.CanCopy()

    def action(self, index=-1, multiplier=1):
        return self.mode.Copy()

class Paste(STCModificationAction):
    """Paste from the current clipboard
    
    Inserts at the current position or overwrites the current selection with
    the data from the clipboard.  Clipboard data may come from Peppy or an
    external program.
    """
    alias = "paste-from-clipboard"
    name = "Paste"
    icon = "icons/paste_plain.png"
    default_menu = ("Edit", 102)
    key_bindings = {'win': "C-v", 'mac': "C-v", 'emacs': "C-y"}

    def isActionAvailable(self):
        return not self.mode.GetReadOnly()

    def action(self, index=-1, multiplier=1):
        return self.mode.Paste()

class PasteAtColumn(STCModificationAction):
    """Paste selection indented to the cursor's column
    
    Feature only available in text modes where the clipboard text will be
    indented to match the column position of the cursor.  Each subsequent
    line in the clipboard text will be indented to the same level, inserting
    leading spaces if necessary so that the first column of each line of the
    clipboard text matches the cursor's column position.
    
    This is not rectangular paste, however, and any existing text in the lines
    will be shifted over only the number of characters in the respective line
    inserted from the clipboard.  The clipboard text is not converted into a
    rectangular block of text with spaces added to the right margins of lines.    """
    alias = "paste-at-column"
    name = "Paste at Column"
    icon = "icons/paste_plain.png"
    default_menu = ("Edit", 103)
    default_toolbar = False

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'PasteAtColumn')

    def isActionAvailable(self):
        return not self.mode.GetReadOnly()

    def action(self, index=-1, multiplier=1):
        self.mode.PasteAtColumn()

class SelectAll(STCModificationAction):
    """Select all text
    
    Selects all text in the document, but the cursor remains in the same
    position.
    """
    alias = "select-all"
    name = "Select All"
    icon = None
    default_menu = ("Edit", -125)
    default_toolbar = False
    key_bindings = {'win': "C-a", 'mac': "C-a", 'emacs': "C-x h"}
    global_id = None

    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'SelectAll')

    def action(self, index=-1, multiplier=1):
        self.mode.SelectAll()


class MajorModeSelect(BufferBusyActionMixin, RadioAction):
    """Switch major mode
    
    Switch the major mode (i.e.  the view of the document) to a compatible
    major mode.  Some modes will not be available because they can not display
    the data in the document, and these incompatible modes will not be listed.
    """
    name="Major Mode"
    inline=False
    default_menu = ("View", 0)

    def initPreHook(self):
        buffer = self.mode.buffer
        stc_class = buffer.stc.__class__
        assert self.dprint("stc_class=%s" % stc_class)
        modes = MajorModeMatcherDriver.getCompatibleMajorModes(stc_class)

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
    """Show or hide minor mode windows
    
    Minor modes are extra sub-windows that are associated with a tab.
    Note that each tab has its own minor modes and these can be toggled
    individually.  By default, minor mode windows are usually hidden.  Their
    visibility state is toggled here, and their initial visibility can be set
    using the preferences for the major mode.
    """
    name = "Minor Modes"
    inline = False
    default_menu = ("View", 1)

    def getItems(self):
        return self.mode.wrapper.minors.getKeywordOrder()

    def isChecked(self, index):
        return self.mode.wrapper.minors.isVisible(index)

    def action(self, index=-1, multiplier=1):
        self.mode.wrapper.minors.toggle(index)


class SidebarShow(ToggleListAction):
    """Show or hide minor mode windows
    
    Sidebars are sub-windows that are attached to each peppy toplevel window.
    By default, sidebars are usually hidden except for L{SpringTabs} which
    are shown.  Their visibility state is toggled here, and their initial
    visibility can be set using the preferences for the major mode.
    """
    name="Sidebars"
    inline=False
    default_menu = ("View", -100)

    def getItems(self):
        return [m.caption for m in self.frame.sidebar_panes]

    def isChecked(self, index):
        return self.frame.sidebar_panes[index].IsShown()

    def action(self, index=-1, multiplier=1):
        self.frame.sidebar_panes[index].Show(not self.frame.sidebar_panes[index].IsShown())
        self.frame._mgr.Update()


class HideSidebars(SelectAction):
    """Close all sidebars
    
    Hides all sidebars (including L{SpringTabs}) from the current window.
    """
    name = "All Sidebars"
    default_menu = (("View/Hide", 991), 100)
    key_bindings = {'emacs': "C-x 4 1", }

    def action(self, index=-1, multiplier=1):
        for m in self.frame.sidebar_panes:
            m.Show(False)
        self.frame._mgr.Update()

class HideMinorModes(SelectAction):
    """Close all minor modes
    
    Hides all minor modes from the current document.
    """
    name = "All Minor Modes"
    default_menu = ("View/Hide", 110)
    key_bindings = {'emacs': "C-x 4 2", }

    def action(self, index=-1, multiplier=1):
        self.mode.wrapper.minors.hideAll()

class HideAll(SelectAction):
    """Close all sidebars and minor modes
    
    Hides all sidebars from the current window and all minor modes from the
    current document.
    """
    name = "All Sidebars and Minor Modes"
    default_menu = ("View/Hide", 120)
    key_bindings = {'emacs': "C-x 1", }

    def action(self, index=-1, multiplier=1):
        for m in self.frame.sidebar_panes:
            m.Show(False)
        self.frame._mgr.Update()
        self.mode.wrapper.minors.hideAll()


class ToolbarShow(ToggleAction):
    """Enable or disable toolbar display in this window
    
    Toggles the visibility of the toolbar for this window.
    """
    alias = "show-toolbar"
    name = "&Show Toolbars"
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
    """Execute an action by name
    
    In addition to key bindings, menu items, and toolbar buttons, all actions
    have a name and can be performed by using their name.  This action displays
    a minibuffer where action names can be searched using tab completion, and
    the action will be performed once the action name has been selected.
    """
    name = "&Execute Action"
    alias = "execute-action"
    key_bindings = {'default': "M-x", }
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
    """Describe an action by name
    
    Displays help text and keyboard bindings for any action in peppy.
    """
    name = "&Describe Action"
    alias = "describe-action"
    default_menu = ("&Help", -200)
    key_bindings = {'emacs': "C-h a", }

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


class DescribeKey(SelectAction):
    """Look up the action from the keystroke
    
    This shows the action (if any) that is bound to a keystroke.  Using this
    action displays a special minibuffer, which waits for a key sequence.
    The key sequence that is entered is compared to all known key sequences
    for the current mode, and if a match is found, the action and its
    documentation are displayed.  If no match is found, an error is printed.
    """
    name = "&Describe Key"
    alias = "describe-key"
    default_menu = ("&Help", 201)
    key_bindings = {'emacs': "C-h k", }

    def action(self, index=-1, multiplier=1):
        self.frame.keys.setReportNext(self.displayAction)

    def displayAction(self, action):
        if action:
            dprint("looking up docs for %s" % action)
            Publisher().sendMessage('peppy.log.info', action.getHelp())
            self.frame.SetStatusText("Keystroke found.")
        else:
            self.frame.SetStatusText("Unbound keystroke.")


class CancelMinibuffer(SelectAction):
    """Cancel any currently active minibuffer
    
    This is a special key sequence that will remove the minibuffer regardless
    of the state of the minibuffer.
    """
    alias = "cancel-minibuffer"
    name = "Cancel Minibuffer"
    icon = 'icons/control_stop.png'
    key_bindings = {'default': "ESC", 'emacs': "M-ESC ESC", }
    
    def action(self, index=-1, multiplier=1):
        self.mode.removeMinibuffer()


class HelpMinibuffer(SelectAction):
    """Show help for the currently active minibuffer"""
    alias = "help-minibuffer"
    name = "Help on Minibuffer"
    default_menu = ("&Help", 210)
    key_bindings = {'emacs': "C-h m", }
    
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
                Properties, Exit,

                Undo, Redo, Cut, Copy, Paste, PasteAtColumn, SelectAll,

                RunScript, RunScriptWithArgs, RunFilter, StopScript,

                MajorModeSelect, MinorModeShow,
                
                SidebarShow, HideSidebars, HideMinorModes, HideAll,
                
                ToolbarShow, 

                BufferList, BufferListSort,

                Minimize, NewWindow, DeleteWindow, MoveTabToNewWindow,
                BringAllToFront, WindowList,
                
                ExecuteActionByName, DescribeAction, DescribeKey, HelpMinibuffer,
                
                CancelMinibuffer,
                ]
