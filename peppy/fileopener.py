# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Classes to manage file opening.

All of the code that handles the opening of new files has been refactored into
this module from frame.py.

"""

import os, threading

import wx

import peppy.vfs as vfs
from peppy.debug import debugmixin, dprint
from peppy.stcinterface import NonResidentSTC
from peppy.majormodematcher import MajorModeMatcherDriver
from peppy.major import BlankMode

from peppy.buffers import *


class FileOpenerExceptionHandled(Exception):
    """This exception is raised to show that the error message has been printed
    by the FileOpener and no further exception processing is necessary.
    """
    pass


class FileOpener(debugmixin):
    """Open a URL into an existing BufferFrame
    
    """
    debuglevel = 0
    
    def __init__(self, frame, url, modecls=None, mode_to_replace=None, force_new_tab=False, created_from_url=None, canonicalize=True, options=None):
        """Create an opener for the specified url
        
        Transient class that loads a file and creates a new tab in the user
        interface.  Depending on settings, the file may be loaded by a thread.
        
        @param url: URL of the file to open
        
        @param modecls: (optional) L{MajorMode} sublass to be used to edit
        the file
        
        @param mode_to_replace: (optional) if used, this L{MajorMode} instance
        will be replaced in the GUI with the newly created major mode.
        
        @param force_new_tab: (optional) force a new tab to be reused,
        regardless of preference settings that would otherwise cause a tab to
        be replaced.
        
        @param create_from_url: (optional) the URL of the buffer that was
        used to generate this URL.  This is not typically used unless you're
        creating a new file in the mem: filesystem and want a working directory
        on the local filesystem to be available if needed to save a copy.
        
        @param canonicalize: (optional) whether or not the URL should be
        canonicalized before searching the existing buffer list.  This is used
        in the rare case where a fragment or query string is significant to
        locating the data on the file system.
        
        @param options: (optional) a dict of options to be passed to the major
        mode's showInitialPosition method
        """
        self.frame = frame
        self.buffer = None
        self.url = vfs.normalize(url)
        if 'mode' in self.url.query:
            self.modecls = self.url.query['mode']
        else:
            self.modecls = modecls
        self.mode_to_replace = mode_to_replace
        self.force_new_tab = force_new_tab
        self.created_from_url = created_from_url
        self.canonicalize = canonicalize
        self.options = options
        
        self.progress = None
        self.dprint(self)
    
    def __str__(self):
        return "Opening %s in %s; mode=%s; replacing %s; options=%s" % (str(self.url), str(self.frame), str(self.modecls), str(self.mode_to_replace), str(self.options))
        
    def open(self):
        """Open a tab in the current frame to edit the given URL.
        """
        if self.findBufferIfAlreadyLoaded():
            self.dprint("Found %s in current buffer list" % self.url)
            self.findMajorModeClassFromString()
            self.frame.tabs.newBuffer(self.url, self.buffer, self.modecls, self.mode_to_replace, self.force_new_tab, self.options)
        else:
            self.openNewBuffer()
    
    def findBufferIfAlreadyLoaded(self):
        if self.canonicalize:
            self.dprint("Looking for %s in current buffer list" % self.url)
            try:
                self.buffer = BufferList.findBufferByURL(self.url)
            except NotImplementedError:
                # This means that the vfs implementation doesn't recognize the
                # filesystem type.  This is the first place in the loading chain
                # that the error can be encountered, so check for it here and load
                # a new plugin if necessary.
                self.findNewFilesystemPlugin()
        return bool(self.buffer)
    
    def findNewFilesystemPlugin(self):
        """Look in plugins for support for a previously unloaded filesystem
        """
        found = False
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            assert self.dprint("Checking %s" % plugin)
            plugin.loadVirtualFileSystem(self.url)
            try:
                self.buffer = BufferList.findBufferByURL(self.url)
                found = True
                break
            except NotImplementedError:
                pass
        if not found:
            self.finalizeAfterFailedLoad("Unknown URI scheme for %s" % self.url)
    
    def openNewBuffer(self):
        """Open a URL that hasn't previously been loaded
        
        """
        self.getLoadingBuffer()
        self.determineMajorMode()
        if self.useThreadedLoading():
            self.dprint("Using threaded loader for %s" % str(self.url))
            self.frame.tabs.newBuffer(self.url, self.buffer, mode_to_replace=self.mode_to_replace, new_tab=self.force_new_tab)
            self.mode_to_replace = self.frame.getActiveMajorMode()
            wx.CallAfter(self.startThreadedLoad)
        else:
            self.dprint("Using non-threaded loader for %s" % str(self.url))
            self.startNonThreadedLoad()
    
    def getLoadingBuffer(self):
        """Creates a temporary L{LoadingBuffer} instance used to determine the
        major mode
        
        """
        try:
            self.buffer = LoadingBuffer(self)
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            self.finalizeAfterFailedLoad(error)
            raise FileOpenerExceptionHandled
    
    def useThreadedLoading(self):
        return wx.GetApp().classprefs.load_threaded and self.modecls.preferThreadedLoading(self.url)
    
    def determineMajorMode(self):
        """If the major mode is specified by name or class, use that; otherwise
        scan the buffer to determine the major mode
        """
        try:
            if self.modecls:
                self.findMajorModeClassFromString()
            else:
                self.scanBufferForMajorMode()
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            self.finalizeAfterFailedLoad(error)
            raise FileOpenerExceptionHandled

    def findMajorModeClassFromString(self):
        """Change the major mode class to a MajorMode object if it's currently
        a string
        
        """
        if isinstance(self.modecls, basestring):
            self.modecls = MajorModeMatcherDriver.matchKeyword(self.modecls, self.buffer, self.url)
            if not self.modecls:
                self.finalizeAfterFailedLoad("Unrecognized major mode keyword '%s'" % self.modecls)
    
    def scanBufferForMajorMode(self):
        """Use the L{MajorModeMatcherDriver} to match the buffer's data to a
        major mode that can display it.
        """
        self.modecls = MajorModeMatcherDriver.match(self.buffer, url=self.url)
        self.dprint("found major mode = %s" % self.modecls)

    def startNonThreadedLoad(self):
        #traceon()
        wx.SetCursor(wx.StockCursor(wx.CURSOR_WATCH))
        try:
            self.dprint("Loading data for %s into buffer" % str(self.url))
            self.buffer = self.buffer.clone()
            self.buffer.openGUIThreadStart()
            self.buffer.openBackgroundThread()
            if self.force_new_tab:
                mode_to_replace = None
            self.finalizeAfterSuccessfulLoad()
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            self.finalizeAfterFailedLoad(error)
        wx.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def startThreadedLoad(self):
        #traceon()
        self.buffer = self.buffer.clone()
        self.dprint("Replaced LoadingBuffer with %s" % self.buffer)
        self.buffer.openGUIThreadStart()
        self.progress = self.mode_to_replace.status_info
        self.progress.startProgress(u"Loading %s" % self.url, message=str(self.mode_to_replace))
        thread = BufferLoadThread(self)
        wx.GetApp().cooperativeYield()
        thread.start()

    def finalizeAfterSuccessfulLoad(self):
        try:
            self.dprint("Successful load of %s" % str(self.url))
            self.buffer.openGUIThreadSuccess()
            assert self.dprint("buffer=%s" % self.buffer)
        except:
            import traceback
            error = traceback.format_exc()
            self.finalizeAfterFailedLoad(error)
            return
        
        if self.progress:
            self.progress.stopProgress("Parsing...")
            wx.GetApp().cooperativeYield()

        assert self.dprint("mode to replace = %s" % self.mode_to_replace)
        mode = self.frame.tabs.newMode(self.buffer, mode_to_replace=self.mode_to_replace)
        assert self.dprint("major mode=%s" % mode)
        
        self.buffer.restoreFromAutosaveIfExists()
        
        #raceoff()
        assert self.dprint("after addViewer")
        mode.showInitialPosition(self.url, self.options)
        msg = mode.getWelcomeMessage()
        mode.status_info.setText(msg)

    def finalizeAfterFailedLoad(self, error):
        #traceoff()
        msg = "Failed opening %s.\n" % unicode(self.url)
        buffer = Buffer.createErrorBuffer(self.url, error)
        mode = self.frame.tabs.newMode(buffer, mode_to_replace=self.mode_to_replace)
        assert self.dprint("major mode=%s" % mode)
        if self.progress:
            self.progress.stopProgress(msg)
        else:
            mode.status_info.setText(msg)


class LoadingSTC(NonResidentSTC):
    def __init__(self, text):
        self.text = text

    def GetText(self):
        return self.text


class LoadingMode(BlankMode):
    """A temporary Major Mode to load another mode in the background
    
    """
    keyword = 'Loading...'
    temporary = False
    stc_class = LoadingSTC

    def createPostHook(self):
        self.showBusy(True)

class LoadingBuffer(BufferVFSMixin, debugmixin):
    """A temporary buffer used to determine which major mode to use
    
    """
    def __init__(self, opener):
        BufferVFSMixin.__init__(self, opener.url, opener.created_from_url, opener.canonicalize)
        self.opener = opener
        self.busy = True
        self.readonly = False
        self.permanent = False
        self.modified = False
        self.defaultmode = LoadingMode
        
        self.stc = LoadingSTC(unicode(self.raw_url))
    
    def isTimestampChanged(self):
        """Override so that we don't attempt to pop up any dialogs when loading
        a file"""
        return False
    
    def clone(self):
        """Get a real Buffer instance from this temporary buffer"""
        return Buffer(self.raw_url, self.opener.modecls, self.created_from_url)

    def addViewer(self, mode):
        pass

    def removeViewer(self, mode):
        pass

    def removeAllViewsAndDelete(self):
        pass
    
    def save(self, url):
        pass

    def getTabName(self):
        return self.defaultmode.keyword
    
    def startChangeDetection(self):
        pass


class BufferLoadThread(threading.Thread, debugmixin):
    """Background file loading thread.
    """
    def __init__(self, opener):
        threading.Thread.__init__(self)
        
        self.opener = opener

    def run(self):
        self.dprint(u"starting to load %s" % unicode(self.opener.buffer.url))
        try:
            self.opener.buffer.openBackgroundThread(self.opener.progress.message)
            wx.CallAfter(self.opener.finalizeAfterSuccessfulLoad)
            self.dprint(u"successfully loaded %s" % unicode(self.opener.buffer.url))
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.dprint("Exception: %s" % str(e))
            wx.CallAfter(self.opener.finalizeAfterFailedLoad, str(e))
