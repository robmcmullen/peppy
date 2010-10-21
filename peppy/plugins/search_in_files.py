# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Major mode to search in files for a string pattern.

Major mode to search for pattern matches from files in a directory or in
a project.
"""

import os, time, fnmatch, heapq

import wx
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs
from peppy.list_mode import *
from peppy.stcinterface import *
from peppy.actions import *
from peppy.yapsy.plugins import *
from peppy.lib.controls import DirBrowseButton2
from peppy.lib.threadutils import *
from peppy.third_party.WidgetStack import WidgetStack


class SearchInFiles(SelectAction):
    """Display and edit key bindings."""
    name = "In Files..."
    icon = 'icons/page_white_find.png'
    default_toolbar = False
    default_menu = (("Tools/Search", -400), 100)

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:search")


class AbstractSearchMethod(object):
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
    def isValid(self):
        return False
    
    def getErrorString(self):
        raise NotImplementedError
    
    def iterFilesInDir(self, dirname, ignorer):
        # Nice algorithm from http://pinard.progiciels-bpi.ca/notes/Away_from_os.path.walk.html
        stack = [dirname]
        while stack:
            directory = heapq.heappop(stack)
            for base in os.listdir(directory):
                if not ignorer(base):
                    name = os.path.join(directory, base)
                    if os.path.isdir(name):
                        if not os.path.islink(name):
                            heapq.heappush(stack, name)
                    else:
                        yield name


    def threadedSearch(self, url, matcher):
        if isinstance(url, vfs.Reference):
            if url.scheme != "file":
                dprint("vfs not threadsafe; skipping %s" % unicode(url).encode("utf-8"))
                return
            url = unicode(url.path).encode("utf-8")
        fh = open(url, "rb")
        bytes = fh.read()
        fh.close()
        try:
            for index, line in enumerate(bytes.split("\n")):
                if matcher(line):
                    result = SearchResult(url, index + 1, line)
                    yield result
        except UnicodeDecodeError:
            return

class DirectorySearchMethod(AbstractSearchMethod):
    def __init__(self, mode):
        AbstractSearchMethod.__init__(self, mode)
        self.pathname = ""
    
    def isValid(self):
        return bool(self.pathname)
    
    def getErrorString(self):
        if not self.isValid():
            return "Invalid directory name"
    
    def getName(self):
        return "Directory"
    
    def getUI(self, parent):
        self.ui = DirBrowseButton2(parent, -1, changeCallback=self.OnChanged)
        return self.ui
    
    def OnChanged(self, evt):
        self.pathname = evt.GetString()
        dprint(self.pathname)
    
    def setUIDefaults(self):
        if not self.ui.GetValue():
#            self.ui.SetValue(self.mode.buffer.cwd())
            self.ui.SetValue("/work/bin")
    
    def iterFiles(self, ignorer):
        return self.iterFilesInDir(self.pathname, ignorer)


class ProjectSearchMethod(AbstractSearchMethod):
    def __init__(self, mode):
        AbstractSearchMethod.__init__(self, mode)
        self.projects = []
        self.current_project = None
    
    def getName(self):
        return "Project"
    
    def isValid(self):
        return self.current_project is not None
    
    def getErrorString(self):
        if self.current_project is None:
            return "Project must be specified before searching"
    
    def getUI(self, parent):
        self.ui = wx.Choice(parent, -1, choices = [])
        self.ui.Bind(wx.EVT_CHOICE, self.OnProject)
        return self.ui
    
    def OnProject(self, evt):
        sel = evt.GetSelection()
        self.current_project = self.projects[sel]
    
    def setUIDefaults(self):
        project_map = ProjectPlugin.getKnownProjects()
        self.ui.Clear()
        sort_order = []
        for url, project in project_map.iteritems():
            dprint("%s: %s" % (url, project))
            long_name = "%s (%s)" % (project.getProjectName(), unicode(url))
            sort_order.append((long_name, project))
        sort_order.sort()
        self.projects = [s[1] for s in sort_order]
        self.ui.AppendItems([s[0] for s in sort_order])
        self.setChoiceFromCurrent()
    
    def setChoiceFromCurrent(self):
        index = 0
        for p in self.projects:
            if p == self.current_project:
                self.ui.SetSelection(index)
                return
            index += 1
        self.current_project = None
    
    def iterFiles(self, ignorer):
        url = self.current_project.getTopURL()
        dir = unicode(url.path)
        return self.iterFilesInDir(dir, ignorer)


class OpenDocsSearchMethod(AbstractSearchMethod):
    def __init__(self, mode):
        AbstractSearchMethod.__init__(self, mode)
        self.cwd = mode.buffer.cwd()
    
    def getName(self):
        return "Open Documents"
    
    def isValid(self):
        return True
    
    def getErrorString(self):
        return None
    
    def getUI(self, parent):
        self.ui = wx.Panel(parent, -1)
        return self.ui
    
    def iterFiles(self, ignorer):
        return []


class StringMatcher(object):
    def __init__(self, string):
        self.string = string
    
    def __call__(self, line):
        return self.string in line
    
    def isValid(self):
        return bool(self.string)


class WildcardListIgnorer(object):
    def __init__(self, string):
        self.patterns = string.split(";")
    
    def __call__(self, filename):
        for pat in self.patterns:
            if fnmatch.fnmatchcase(filename, pat):
                return True
        return False


class SearchSTC(UndoMixin, NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    def __init__(self, parent=None, copy=None):
        NonResidentSTC.__init__(self, parent, copy)
        self.search_string = None
        self.search_methods = []
        self.search_method = None
        self.search_domain = None
        self.widget_stack = None
        self.results = []
    
    def loadSearchMethods(self, mode):
        self.search_methods = [DirectorySearchMethod(mode),
                               ProjectSearchMethod(mode),
                               OpenDocsSearchMethod(mode)]
    
    def setSearchMethod(self, method):
        self.search_method = method
        self.showSearchMethodUI()
    
    def setSearchMethodIndex(self, index):
        method = self.search_methods[index]
        self.setSearchMethod(method)
    
    def getSearchMethodNames(self):
        names = [n.getName() for n in self.search_methods]
        print names
        return names
    
    def addSearchMethodUI(self, stack):
        for n in self.search_methods:
            n.getUI(stack)
            stack.AddWidget(n.ui)
        self.widget_stack = stack
    
    def showSearchMethodUI(self):
        print(self.search_method)
        self.widget_stack.RaiseWidget(self.search_method.ui)
        self.search_method.setUIDefaults()
    
    def getShortDisplayName(self, url):
        return "Search"
    
    def update(self, url):
        if self.search_method is None:
            self.setSearchMethod(self.search_methods[0])
        self.search_method.setUIDefaults()
    
    def clearSearchResults(self):
        self.results = []
    
    def getSearchResults(self):
        return self.results
    
    def addSearchResult(self, result):
        self.results.append(result)
    
    def addNewResultsToGUI(self, mode):
        current = mode.list.GetItemCount()
        future = len(self.results)
        if future > current:
            mode.appendListItems(self.results[current:future])


class SearchResult(object):
    def __init__(self, url, line, text):
        self.url = url
        self.line = line
        self.text = text


class SearchStatus(ThreadStatus):
    def __init__(self, mode):
        ThreadStatus.__init__(self)
        self.mode = mode
    
    def updateStatusGUI(self, perc, text=None):
        self.mode.buffer.stc.addNewResultsToGUI(self.mode)
        self.mode.status_info.updateProgress(int(perc), text)
        
    def reportSuccessGUI(self, text, data):
        self.mode.buffer.stc.addNewResultsToGUI(self.mode)
        self.mode.status_info.stopProgress(text)
        self.cleanup()
        
    def reportFailureGUI(self, text):
        dprint(text)
        self.mode.status_info.stopProgress(text)
        self.cleanup()
    
    def cleanup(self):
        pass


class SearchThread(threading.Thread):
    def __init__(self, stc, matcher, ignorer, updater):
        threading.Thread.__init__(self)
        self.stc = stc
        self.matcher = matcher
        self.ignorer = ignorer
        self.updater = updater
        self.output = None
        self.interval = 0.5
    
    def run(self):
        try:
            method = self.stc.search_method
            sort_order = []
            for url in method.iterFiles(self.ignorer):
                sort_order.append(url)
            sort_order.sort()
            
            num_urls = len(sort_order)
            count = 0
            start = time.time()
            for url in sort_order:
                count += 1
                for result in method.threadedSearch(url, self.matcher):
#                dprint(result)
                    self.stc.addSearchResult(result)
#                time.sleep(0.1)
                now = time.time()
                if now - start > self.interval:
                    self.updater.updateStatus(count, num_urls)
                    start = now
            self.updater.reportSuccess("Finished searching %d files" % count)
        except:
            import traceback
            error = traceback.format_exc()
            self.updater.reportFailure(error)



class SearchMode(ListMode):
    """Search for text in files
    """
    keyword = "Search"
    icon = 'icons/page_white_find.png'
    allow_threaded_loading = False
    
    stc_class = SearchSTC

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:search
        if url.scheme == 'about' and url.path == 'search':
            return True
        return False
    
    def __init__(self, *args, **kwargs):
        ListMode.__init__(self, *args, **kwargs)
        self.thread = None
        
    # Need to add CanUndo, Undo, CanRedo, Redo to the major mode level so that
    # the actions can determine that Undo and Redo should be added to the user
    # interface.  worksWithMajorMode doesn't look at the STC to determine what
    # action to add; only the major mode class
    def CanUndo(self):
        return self.buffer.stc.CanUndo()

    def Undo(self):
        self.buffer.stc.Undo()
        self.resetList()

    def CanRedo(self):
        return self.buffer.stc.CanRedo()

    def Redo(self):
        self.buffer.stc.Redo()
        self.resetList()

    def revertPostHook(self):
        self.resetList()

    def createInfoHeader(self, sizer):
        self.buffer.stc.loadSearchMethods(self)
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, -1, "Search for:")
        hbox.Add(label, 0, wx.ALIGN_CENTER)
        self.search_text = wx.TextCtrl(panel, -1,)
        self.search_text.SetValue("python")
        hbox.Add(self.search_text, 5, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, _("Search in:"))
        hbox.Add(text, 0, wx.ALIGN_CENTER)
        self.domain = wx.Choice(panel, -1, choices = self.buffer.stc.getSearchMethodNames())
        self.Bind(wx.EVT_CHOICE, self.OnDomain, self.domain)
        hbox.Add(self.domain, 1, wx.EXPAND)
        self.domain_panel = WidgetStack(panel, -1)
        self.buffer.stc.addSearchMethodUI(self.domain_panel)
        hbox.Add(self.domain_panel, 5, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, -1, "Ignore names:")
        hbox.Add(label, 0, wx.ALIGN_CENTER)
        self.ignore_filenames = wx.TextCtrl(panel, -1,)
        self.ignore_filenames.SetValue(".git;.svn;.bzr;*.o;*.a;*.so;*.dll;*~;*.bak;*.exe;*.pyc")
        hbox.Add(self.ignore_filenames, 5, wx.EXPAND)
        
        self.search_start = wx.Button(panel, -1, "Start")
        self.Bind(wx.EVT_BUTTON, self.OnStart, self.search_start)
        hbox.Add(self.search_start, 0, wx.EXPAND)
        
        vbox.Add(hbox, 0, wx.EXPAND)
        
#        self.mode_list, names = self.getActiveModesAndNames()
#        self.mode_choice = wx.Choice(panel, -1, choices = names)
#        self.Bind(wx.EVT_CHOICE, self.OnModeChoice, self.mode_choice)
#        hbox.Add(self.mode_choice, 0, wx.EXPAND)
#        
#        global_check = wx.CheckBox(panel, -1, "Show Global Actions")
#        global_check.SetValue(True)
#        self.Bind(wx.EVT_CHECKBOX, self.OnGlobal, global_check)
#        hbox.Add(global_check, 0, wx.EXPAND)
        
        panel.SetSizer(vbox)

        sizer.Add(panel, 0, wx.EXPAND)
        
        dprint(self.buffer)
    
    def showInitialPosition(self, url, options=None):
        self.buffer.stc.update(url)
        wx.CallAfter(self.resetList)
    
    def OnDomain(self, evt):
        sel = evt.GetSelection()
        self.buffer.stc.setSearchMethodIndex(sel)
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def getStringMatcher(self):
        return StringMatcher(self.search_text.GetValue())
    
    def OnStart(self, evt):
        if not self.isThreadRunning():
            method = self.buffer.stc.search_method
            if method.isValid():
                status = SearchStatus(self)
                matcher = self.getStringMatcher()
                ignorer = WildcardListIgnorer(self.ignore_filenames.GetValue())
                if matcher.isValid():
                    self.buffer.stc.clearSearchResults()
                    self.resetList()
                    self.status_info.startProgress("Searching...")
                    self.thread = SearchThread(self.buffer.stc, matcher, ignorer, status)
                    self.thread.start()
                else:
                    self.setStatusText("Invalid search string.")
            else:
                self.setStatusText(method.getErrorString())
    
    def isThreadRunning(self):
        return self.thread is not None and self.thread.isAlive()
    
    def idlePostHook(self):
        pass
        
    def createColumns(self, list):
        list.InsertSizedColumn(0, "URL", min=100, greedy=False)
        list.InsertSizedColumn(1, "Line", min=10, greedy=False)
        list.InsertSizedColumn(2, "Match", min=300, greedy=True)

    def getListItems(self):
        return self.buffer.stc.getSearchResults()
    
    def getItemRawValues(self, index, item):
        return (unicode(item.url), item.line, unicode(item.text))
    
    def appendListItems(self, items):
        self.list.Freeze()
        index = self.list.GetItemCount()
        for item in items:
            self.insertListItem(item, index)
            index += 1
        self.list.Thaw()
    
    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        orig_index = self.list.GetItemData(index)
        values = self.list.itemDataMap[orig_index]
        dprint(values)
        self.frame.open(values[0], options={'line':values[1] - 1})

class SearchModePlugin(IPeppyPlugin):
    """Plugin to advertise the presence of the Search sidebar
    """
    def getMajorModes(self):
        yield SearchMode

    def getActions(self):
        yield SearchInFiles
