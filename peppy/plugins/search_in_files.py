# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Major mode to search in files for a string pattern.

Major mode to search for pattern matches from files in a directory or in
a project.
"""

import os, time, fnmatch, heapq, re

import wx
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs
from peppy.buffers import BufferList
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


class SearchModeActionMixin(object):
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'isSearchRunning')
    

class StartSearch(SearchModeActionMixin, SelectAction):
    """Start a new search for a pattern in files."""
    name = "Start Search"
    icon = 'icons/search-start.png'
    default_menu = ("Actions", 10)

    def isEnabled(self):
        return not self.mode.isSearchRunning()

    def action(self, index=-1, multiplier=1):
        self.mode.OnStartSearch(None)


class StopSearch(SearchModeActionMixin, SelectAction):
    """Stop a currently running search."""
    name = "Stop Search"
    icon = 'icons/search-stop.png'
    default_menu = ("Actions", 11)

    def isEnabled(self):
        return self.mode.isSearchRunning()

    def action(self, index=-1, multiplier=1):
        self.mode.OnStopSearch(None)


class AbstractSearchMethod(object):
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
    def isValid(self):
        return False
    
    def getErrorString(self):
        raise NotImplementedError
    
    def getPrefix(self):
        return ""
    
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

    def getMatchGenerator(self, url, matcher):
        if isinstance(url, vfs.Reference):
            if url.scheme != "file":
                dprint("vfs not threadsafe; skipping %s" % unicode(url).encode("utf-8"))
                return
            url = unicode(url.path).encode("utf-8")
        fh = open(url, "rb")
        return matcher.iterMatches(url, fh)

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
    
    def setUIDefaults(self):
        if not self.ui.GetValue():
            self.ui.SetValue(self.mode.buffer.cwd())
    
    def getPrefix(self):
        prefix = unicode(self.pathname)
        if not prefix.endswith(os.sep):
            prefix += os.sep
        return prefix
    
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
    
    def getPrefix(self):
        url = self.current_project.getTopURL()
        prefix = unicode(url.path)
        if not prefix.endswith("/"):
            prefix += "/"
        return prefix
    
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
    
    def setUIDefaults(self):
        pass
    
    class STCFH(object):
        """Mock file handler to wrap an existing STC instance to create an
        iterator over each line
        
        """
        def __init__(self, stc):
            self.stc = stc
            self.line = 0
        
        def __iter__(self):
            return self
        
        def next(self):
            if self.line < self.stc.GetLineCount():
                line = self.stc.GetLine(self.line)
                self.line += 1
                return line
            raise StopIteration
        
        def close(self):
            pass
    
    def getMatchGenerator(self, item, matcher):
        url, buf = item
        stc = buf.stc
        if hasattr(stc, "GetLine") and hasattr(stc, "GetLineCount"):
            fh = OpenDocsSearchMethod.STCFH(stc)
            return matcher.iterMatches(url, fh)
        else:
            return iter([])

    def iterFiles(self, ignorer):
        """Iterate through open files, returning the sort item that will
        later be used in the call to threadedSearch
        
        """
        docs = BufferList.getBuffers()
        for buf in docs:
            if not buf.permanent:
                yield (str(buf.url), buf)

class AbstractStringMatcher(object):
    """Base class for string matching.
    
    The L{match} method must be defined in subclasses to return True if
    the line matches the criteria offered by the subclass.
    """
    def __init__(self, string):
        self.string = string
    
    def iterMatches(self, url, fh):
        """Iterator for lines in a file, calling L{match} on each line and
        yielding a L{SearchResult} if match is found.
        
        """
        try:
            index = 0
            for line in fh:
                line = line.rstrip("\r\n")
                if self.match(line):
                    result = SearchResult(url, index + 1, line)
                    yield result
                index += 1
        except UnicodeDecodeError:
            pass
        finally:
            fh.close()
    
    def isValid(self):
        return bool(self.string)

class ExactStringMatcher(AbstractStringMatcher):
    def match(self, line):
        return self.string in line

class IgnoreCaseStringMatcher(ExactStringMatcher):
    def __init__(self, string):
        self.string = string.lower()
    
    def match(self, line):
        return self.string in line.lower()

class RegexStringMatcher(AbstractStringMatcher):
    def __init__(self, string, match_case):
        try:
            if not match_case:
                flags = re.IGNORECASE
            else:
                flags = 0
            self.cre = re.compile(string, flags)
        except re.error:
            self.cre = None
        self.last_match = None
    
    def match(self, line):
        self.last_match = self.cre.search(line)
        return self.last_match is not None
    
    def isValid(self):
        return bool(self.cre)

class AbstractSearchType(object):
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
class TextSearchType(AbstractSearchType):
    def __init__(self, mode):
        AbstractSearchType.__init__(self, mode)
    
    def getName(self):
        return "Text Search"
    
    def getUI(self, parent):
        self.ui = wx.Panel(parent, -1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.case = wx.CheckBox(self.ui, -1, _("Match Case"))
        hbox.Add(self.case, 0, wx.EXPAND)
        self.regex = wx.CheckBox(self.ui, -1, _("Regular Expression"))
        hbox.Add(self.regex, 0, wx.EXPAND)
        self.ui.SetSizer(hbox)
        return self.ui
    
    def setUIDefaults(self):
        pass

    def getStringMatcher(self, search_text):
        if self.regex.IsChecked():
            return RegexStringMatcher(search_text, self.case.IsChecked())
        else:
            if self.case.IsChecked():
                return ExactStringMatcher(search_text)
            else:
                return IgnoreCaseStringMatcher(search_text)

class WildcardListIgnorer(object):
    def __init__(self, string):
        self.patterns = string.split(";")
    
    def __call__(self, filename):
        for pat in self.patterns:
            if fnmatch.fnmatchcase(filename, pat):
                return True
        return False


class OptionStack(object):
    """Abstract class to represent a group of options controlled by a pulldown
    menu where each option has some GUI elements that are presented in a
    L{WidgetStack} object.
    
    """
    def __init__(self):
        self.options = []
        self.option = None
        self.widget_stack = None
        
    def loadOptions(self, mode):
        raise NotImplementedError
    
    def setOption(self, option):
        self.option = option
        self.showUI()
    
    def setIndex(self, index):
        option = self.options[index]
        self.setOption(option)
    
    def getNames(self):
        names = [n.getName() for n in self.options]
        return names
    
    def addUI(self, stack):
        for n in self.options:
            n.getUI(stack)
            stack.AddWidget(n.ui)
        self.widget_stack = stack
    
    def showUI(self):
        self.widget_stack.RaiseWidget(self.option.ui)
        self.option.setUIDefaults()
    
    def reset(self):
        if self.option is None:
            self.setIndex(0)
        else:
            self.showUI()

class SearchMethodStack(OptionStack):
    def loadOptions(self, mode):
        self.options = [DirectorySearchMethod(mode),
                        ProjectSearchMethod(mode),
                        OpenDocsSearchMethod(mode)]
        extra = []
        Publisher().sendMessage('search_in_files.search_method.provider', extra)
        if extra:
            for cls in extra:
                try:
                    method = cls(mode)
                    self.options.append(method)
                except Exception, e:
                    eprint("Search method %s failed to initiate.\n%s" % (cls, e))

class SearchTypeStack(OptionStack):
    def loadOptions(self, mode):
        self.options = [TextSearchType(mode)]
        extra = []
        Publisher().sendMessage('search_in_files.text_search_type.provider', extra)
        if extra:
            for cls in extra:
                try:
                    method = cls(mode)
                    self.options.append(method)
                except Exception, e:
                    import traceback
                    error = traceback.format_exc()
                    eprint("Search method %s failed to initiate.\n%s" % (cls, error))


class SearchSTC(UndoMixin, NonResidentSTC):
    """Dummy STC just to prevent other modes from being able to change their
    major mode to this one.
    """
    def __init__(self, parent=None, copy=None):
        NonResidentSTC.__init__(self, parent, copy)
        self.search_string = None
        self.search_method = SearchMethodStack()
        self.search_type = SearchTypeStack()
        self.search_domain = None
        self.results = []
        self.prefix = ""
    
    def loadSearchOptions(self, mode):
        self.search_method.loadOptions(mode)
        self.search_type.loadOptions(mode)
    
    def getShortDisplayName(self, url):
        return "Search"
    
    def update(self, url):
        self.search_method.reset()
        self.search_type.reset()
    
    def clearSearchResults(self):
        self.results = []
        self.prefix = ""
    
    def setPrefix(self, prefix):
        self.prefix = prefix
    
    def getSearchResults(self):
        return self.results
    
    def addSearchResult(self, result):
        self.results.append(result)
    
    def addNewResultsToGUI(self, mode):
        current = mode.list.GetItemCount()
        future = len(self.results)
        if future > current:
            for result in self.results[current:future]:
                result.checkPrefix(self.prefix)
            mode.appendListItems(self.results[current:future])


class SearchResult(object):
    def __init__(self, url, line, text):
        self.short = url
        self.url = url
        self.line = line
        self.text = text
    
    def checkPrefix(self, prefix):
        if self.url.startswith(prefix):
            self.short = self.url[len(prefix):]


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
        self.mode.status_info.stopProgress(text)
        self.cleanup()
    
    def cleanup(self):
        self.mode.showSearchButton(False)
        self.mode.list.ResizeColumns()


class SearchThread(threading.Thread):
    def __init__(self, stc, matcher, ignorer, updater):
        threading.Thread.__init__(self)
        self.stc = stc
        self.matcher = matcher
        self.ignorer = ignorer
        self.updater = updater
        self.output = None
        self.interval = 0.5
        self.matches = 0
        self.init_time = time.time()
        self.stop_request = False
    
    def run(self):
        try:
            method = self.stc.search_method.option
            sort_order = []
            for item in method.iterFiles(self.ignorer):
                sort_order.append(item)
                if self.stop_request:
                    self.updater.reportFailure("Aborted while determining file sort order")
                    return
            sort_order.sort()
            
            num_urls = len(sort_order)
            start = time.time()
            for item in sort_order:
                self.matches += 1
                gen = method.getMatchGenerator(item, self.matcher)
                for result in gen:
#                    dprint(result)
                    self.stc.addSearchResult(result)
#                time.sleep(0.1)
                if self.stop_request:
                    break
                now = time.time()
                if now - start > self.interval:
                    self.updater.updateStatus(self.matches, num_urls)
                    start = now
            self.showStats()
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            eprint(error)
            self.updater.reportFailure(str(e))
    
    def showStats(self):
        self.updater.reportSuccess("Finished searching %d files in %.2f seconds" % (self.matches, time.time() - self.init_time))
    
    def stopSearch(self):
        self.stop_request = True



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
        self.buffer.stc.loadSearchOptions(self)
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, -1, "Search for:")
        hbox.Add(label, 0, wx.ALIGN_CENTER)
        self.search_text = wx.TextCtrl(panel, -1,)
        hbox.Add(self.search_text, 5, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, _("Search type:"))
        hbox.Add(text, 0, wx.ALIGN_CENTER)
        self.options = wx.Choice(panel, -1, choices = self.buffer.stc.search_type.getNames())
        self.options.SetSelection(0) # prevent MSW indeterminate initial state
        self.Bind(wx.EVT_CHOICE, self.OnOptions, self.options)
        hbox.Add(self.options, 1, wx.EXPAND)
        self.options_panel = WidgetStack(panel, -1)
        self.buffer.stc.search_type.addUI(self.options_panel)
        hbox.Add(self.options_panel, 5, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, _("Search in:"))
        hbox.Add(text, 0, wx.ALIGN_CENTER)
        self.domain = wx.Choice(panel, -1, choices = self.buffer.stc.search_method.getNames())
        self.domain.SetSelection(0) # prevent MSW indeterminate initial state
        self.Bind(wx.EVT_CHOICE, self.OnDomain, self.domain)
        hbox.Add(self.domain, 1, wx.EXPAND)
        self.domain_panel = WidgetStack(panel, -1)
        self.buffer.stc.search_method.addUI(self.domain_panel)
        hbox.Add(self.domain_panel, 5, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, -1, "Ignore names:")
        hbox.Add(label, 0, wx.ALIGN_CENTER)
        self.ignore_filenames = wx.TextCtrl(panel, -1,)
        self.ignore_filenames.SetValue(".git;.svn;.bzr;*.o;*.a;*.so;*.dll;*~;*.bak;*.exe;*.pyc")
        hbox.Add(self.ignore_filenames, 5, wx.EXPAND)
        
        self.search_button_running = {
            False: _("Start"),
            True: _("Stop"),
            }
        self.search_button = wx.Button(panel, -1, self.search_button_running[False])
        self.Bind(wx.EVT_BUTTON, self.OnToggleSearch, self.search_button)
        hbox.Add(self.search_button, 0, wx.EXPAND)
        
        vbox.Add(hbox, 0, wx.EXPAND)
        
        panel.SetSizer(vbox)

        sizer.Add(panel, 0, wx.EXPAND)
    
    def showInitialPosition(self, url, options=None):
        self.buffer.stc.update(url)
        wx.CallAfter(self.resetList)
    
    def OnDomain(self, evt):
        sel = evt.GetSelection()
        self.buffer.stc.search_method.setIndex(sel)
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def OnOptions(self, evt):
        sel = evt.GetSelection()
        self.buffer.stc.search_type.setIndex(sel)
        wx.CallAfter(self.resetList)
        
        # Make sure the focus is back on the list so that the keystroke
        # commands work
        wx.CallAfter(self.list.SetFocus)
    
    def OnToggleSearch(self, evt):
        state = self.isSearchRunning()
        if state:
            self.OnStopSearch(evt)
        else:
            self.OnStartSearch(evt)
    
    def OnStartSearch(self, evt):
        if not self.isSearchRunning():
            self.showSearchButton(True)
            method = self.buffer.stc.search_method.option
            if method.isValid():
                status = SearchStatus(self)
                matcher = self.buffer.stc.search_type.option.getStringMatcher(self.search_text.GetValue())
                ignorer = WildcardListIgnorer(self.ignore_filenames.GetValue())
                if matcher.isValid():
                    self.buffer.stc.clearSearchResults()
                    self.buffer.stc.setPrefix(method.getPrefix())
                    self.resetList()
                    self.status_info.startProgress("Searching...")
                    self.thread = SearchThread(self.buffer.stc, matcher, ignorer, status)
                    self.thread.start()
                else:
                    self.setStatusText("Invalid search string.")
            else:
                self.setStatusText(method.getErrorString())
    
    def OnStopSearch(self, evt):
        if self.isSearchRunning():
            self.thread.stopSearch()
            self.showSearchButton(False)
    
    def isSearchRunning(self):
        return self.thread is not None and self.thread.isAlive()
    
    def showSearchButton(self, running=None):
        if running is None:
            running = self.isSearchRunning()
        self.search_button.SetLabel(self.search_button_running[running])
    
    def idlePostHook(self):
        pass
        
    def createColumns(self, list):
        list.InsertSizedColumn(0, "File", min=100, max=250, greedy=False)
        list.InsertSizedColumn(1, "Line", min=10, greedy=False)
        list.InsertSizedColumn(2, "Match", min=300, greedy=True, ok_offscreen=True)

    def getListItems(self):
        return self.buffer.stc.getSearchResults()
    
    def getItemRawValues(self, index, item):
        return (unicode(item.short), item.line, unicode(item.text).replace("\r", ""), item.url)
    
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
        self.frame.findTabOrOpen(values[3], options={'line':values[1] - 1})

class SearchModePlugin(IPeppyPlugin):
    """Plugin to advertise the presence of the Search sidebar
    """
    def getMajorModes(self):
        yield SearchMode

    def getActions(self):
        return [SearchInFiles, StartSearch, StopSearch]
