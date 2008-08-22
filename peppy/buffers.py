# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc

import peppy.vfs as vfs

from peppy.actions import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.userparams import *
from peppy.lib.bufferedreader import *

from peppy.dialogs import *
from peppy.stcinterface import *
from peppy.stcbase import *
from peppy.major import *
from peppy.debug import *

class BufferList(OnDemandGlobalListAction):
    name = "Documents"
    default_menu = ("Documents", -500)
    inline = True
    
    # keep track of only changes to this on demand action
    localhash = 0
    
    # provide storage for the on demand global list
    storage = []
    
    # flag to indicate that the list should be sorted before the next menu
    # display
    needs_sort = True
    
    @classmethod
    def addBuffer(cls, buf):
        """Convenience function to add a buffer and flag to be sorted"""
        cls.append(buf)
        cls.needsSort()
    
    @classmethod
    def removeBuffer(cls, buf):
        """Convenience function to remove a buffer and flag to be sorted"""
        cls.remove(buf)
        cls.needsSort()
    
    @classmethod
    def findBufferByURL(cls, url):
        url = vfs.canonical_reference(url)
        for buf in cls.storage:
            if buf.isURL(url):
                return buf
        return None

    @classmethod
    def findBuffersByBasename(cls, basename):
        bufs = []
        for buf in cls.storage:
            if buf.isBasename(basename):
                bufs.append(buf)
        return bufs

    @classmethod
    def getBuffers(cls):
        return [buf for buf in cls.storage]

    @staticmethod
    def promptUnsaved():
        unsaved=[]
        for buf in BufferList.storage:
            if buf.modified and not buf.permanent:
                unsaved.append(buf)
        if len(unsaved)>0:
            dlg = QuitDialog(wx.GetApp().GetTopWindow(), unsaved)
            retval=dlg.ShowModal()
            dlg.Destroy()
        else:
            retval=wx.ID_OK

        if retval==wx.ID_OK:
            return True
        return False
            
    def getItems(self):
        return ["%s  (%s)" % (buf.displayname, unicode(buf.url)) for buf in self.storage]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index,BufferList.storage[index]))
        self.frame.setBuffer(BufferList.storage[index])
    
    @classmethod
    def sort(cls):
        """Sort using the decorate, sort, undecorate pattern"""
        decorator = BufferListSort.getSortDecorator(BufferList.storage)
        
        sorted = zip(decorator, BufferList.storage)
        sorted.sort()
        
        #dprint(sorted)
        buffers = [s[-1] for s in sorted]
        BufferList.storage = buffers
        
        cls.calcHash()
    
    @classmethod
    def needsSort(cls):
        cls.needs_sort = True
    
    def dynamic(self):
        """Check to see if the list needs sorting before processing a dynamic
        menu update.
        """
        if self.__class__.needs_sort:
            self.sort()
            self.__class__.needs_sort = False
        OnDemandGlobalListAction.dynamic(self)


class BufferListSort(OnDemandActionMixin, RadioAction):
    name = "Sort Order"
    inline = False
    localize_items = True
    tooltip = "Sort document list"
    default_menu = ("Documents", -999)

    items = ['By Name', 'By Mode', 'Order Loaded']
    sort_index = 0

    @classmethod
    def getSortDecorator(cls, buffers):
        if cls.sort_index == 0:
            decorator = [buffer.displayname for buffer in buffers]
        elif cls.sort_index == 1:
            decorator = [buffer.defaultmode for buffer in buffers]
        elif cls.sort_index == 2:
            decorator = [buffer.order_loaded for buffer in buffers]
        else:
            raise IndexError("Unknown sort order")
        return decorator

    def getIndex(self):
        return BufferListSort.sort_index

    def getItems(self):
        return BufferListSort.items

    def action(self, index=-1, multiplier=1):
        dprint()
        BufferListSort.sort_index = index
        BufferList.needsSort()
    
    def updateOnDemand(self):
        pass


#### Buffers

class BufferVFSMixin(debugmixin):
    """Mixin class that compartmentalizes the interaction with the vfs
    
    """
    def __init__(self, url, created_from_url=None, canonicalize=True):
        """Initialize the mixin.
        
        @param url: url of the buffer
        
        @param created_from_url: (optional) url from which this buffer was
        created.  If this exists, it will be used as a secondary place to look
        for a local filesystem working directory if a working directory can't
        be determined from the real url.
        
        @param canonicalize: whether or not the url should be canonicalized
        before storing in the buffer list.
        """
        self.bfh = None
        self.last_mtime = None
        self.canonicalize = canonicalize
        self.setURL(url)
        self.created_from_url = created_from_url
        
    def setURL(self, url):
        # raw_url stores the entire URL, including query string and fragments
        self.raw_url = vfs.normalize(url)
        if not url:
            url = vfs.normalize("untitled")
        elif self.canonicalize:
            url = vfs.canonical_reference(url)
        else:
            url = vfs.normalize(url)
        self.url = url
        self.saveTimestamp()

    def isURL(self, url):
        if self.canonicalize:
            url = vfs.canonical_reference(url)
        else:
            url = vfs.normalize(url)
        if url == self.url:
            return True
        return False

    def saveTimestamp(self):
        if self.url.scheme == 'file':
            try:
                self.last_mtime = vfs.get_mtime(self.url)
            except OSError:
                self.last_mtime = None

    def isTimestampChanged(self):
        if self.last_mtime is not None and self.url.scheme == 'file':
            mtime = vfs.get_mtime(self.url)
            #dprint("current=%s saved=%s" % (mtime, self.last_mtime))
            return mtime != self.last_mtime
        return False
    
    def getFilename(self):
        return unicode(self.url.path)

    def _cwd(self, url, use_vfs=False):
        """Find a directory in the local filesystem that corresponds to the
        given url.
        """
        if url.scheme == 'file':
            path = os.path.normpath(os.path.dirname(unicode(url.path)))
        else:
            # If it's an absolute path, see if it converts to an existing path
            # in the local filesystem by converting it to a file:// url and
            # seeing if any path components exist
            lastpath = None
            temp = unicode(url.path)
            if not temp.startswith('/'):
                return '/'
            uri = vfs.normalize(unicode(url.path))
            path = os.path.normpath(unicode(uri.path))
            while path != lastpath and path != '/':
                dprint("trying %s" % path)
                if os.path.isdir(path):
                    break
                lastpath = path
                path = os.path.dirname(path)
        return path
            
    def cwd(self, use_vfs=False):
        """Find the current working directory of the buffer.
        
        Can be used in two ways based on use_vfs:
        
        use_vfs == True: uses the vfs to return the directory in the same
        scheme as the buffer
        
        use_vfs == False (the default): find the current working directory
        on the local filesystem.  Some schemes, like tar, for instance, are
        overlays on the current filesystem and the cwd of those schemes with
        this sense of use_vfs will report the overlayed directory.
        """
        if use_vfs:
            if vfs.is_folder(self.url):
                path = vfs.normalize(self.url)
            else:
                path = vfs.get_dirname(self.url)
            return path
        else:
            path = self._cwd(self.url)
            if (not path or path == '/') and self.created_from_url:
                path = self._cwd(self.created_from_url)
        
        if path == '/':
            path = wx.StandardPaths.Get().GetDocumentsDir()
        return path

    def getBufferedReader(self, size=1024):
        assert self.dprint("opening %s as %s" % (unicode(self.url), self.defaultmode))
        if self.bfh is None:
            if vfs.exists(self.url):
                fh = vfs.open(self.url)
                self.bfh = BufferedReader(fh, size)
        if self.bfh:
            self.bfh.seek(0)
        return self.bfh
    
    def closeBufferedReader(self):
        if self.bfh:
            self.bfh.close()
            self.bfh = None


class Buffer(BufferVFSMixin):
    """Abstraction around a file-like object obtained from a url.
    
    Each buffer instance corresponds a unique url, handles the interaction
    between the file-like object that is used to read the data and the
    STCInterface that is used to hold the representation in memory.
    
    The STCInterface provides the low-level access to the file, and there is a
    one-to-one mapping from a buffer to an STCInterface instance.
    """
    count=0
    error_buffer_count = 0

    filenames={}
    
    dummyframe = None
    
    @classmethod
    def initDummyFrame(cls):
        # the Buffer objects have an stc as the base, and they need a
        # frame in which to work.  So, we create a dummy frame here
        # that is never shown.
        Buffer.dummyframe=wx.Frame(None)
        Buffer.dummyframe.Show(False)

    @classmethod
    def loadPermanent(cls, url, defaultmode=None):
        buffer = cls(url, defaultmode)
        buffer.open()
        buffer.permanent = True
    
    @classmethod
    def createErrorBuffer(cls, url, error):
        cls.error_buffer_count += 1
        errurl = "mem:error-%d.txt" % cls.error_buffer_count
        fh = vfs.make_file(errurl)
        fh.write("Failed opening %s.\n\nDetailed error message follows:\n\n" % unicode(url))
        fh.write(error)
        fh.close()
        buffer = Buffer(errurl)
        buffer.openGUIThreadStart()
        buffer.openBackgroundThread()
        buffer.openGUIThreadSuccess()
        return buffer

    def __init__(self, url, defaultmode=None, created_from_url=None):
        BufferVFSMixin.__init__(self, url, created_from_url)
        
        if Buffer.dummyframe is None:
            Buffer.initDummyFrame()

        self.busy = False
        self.readonly = False
        self.defaultmode=defaultmode

        self.guessBinary=False
        self.guessLength=1024
        self.guessPercentage=10

        self.viewer=None
        self.viewers=[]

        self.modified=False
        self.permanent = False

        self.stc=None

    def __del__(self):
        dprint(u"cleaning up buffer %s" % unicode(self.url))

    def addViewer(self, mode):
        self.viewers.append(mode) # keep track of views
        assert self.dprint("views of %s: %s" % (self,self.viewers))
    
    def iterViewers(self):
        """Return an iterator over all the views of this buffer"""
        for view in self.viewers:
            yield view
    
    def numViewers(self):
        """Return the number of views of this buffer"""
        return len(self.viewers)
    
    def forEachView(self, func_name):
        """Call a method for each view of this buffer.
        
        @param func_name: string to be used as the method to call
        """
        for view in self.viewers:
            if hasattr(view, func_name):
                func = getattr(view, func_name)
                self.dprint("calling %s in %s" % (func_name, view))
                func()

    def removeViewer(self,view):
        assert self.dprint("removing view %s of %s" % (view,self))
        if view in self.viewers:
            self.viewers.remove(view)
            if hasattr(view, 'removeDocumentView'):
                view.removeDocumentView()
        else:
            raise ValueError("Bug somewhere.  Major mode %s not found in Buffer %s" % (view,self))
        assert self.dprint("views remaining of %s: %s" % (self,self.viewers))

    def removeAllViewsAndDelete(self):
        # Have to make a copy of self.viewers, because when the viewer
        # closes itself, it removes itself from this list of viewers,
        # so unless you make a copy the for statement is operating on
        # a changing list.
        viewers=self.viewers[:]
        for viewer in viewers:
            assert self.dprint("count=%d" % len(self.viewers))
            assert self.dprint("removing view %s of %s" % (viewer,self))
            viewer.frame.tabs.closeWrapper(viewer)
        assert self.dprint("final count=%d" % len(self.viewers))

        if not self.permanent:
            basename=self.stc.getShortDisplayName(self.raw_url)

            BufferList.removeBuffer(self)
            # Need to destroy the base STC or self will never get garbage
            # collected
            self.stc.Destroy()
            Publisher().sendMessage('buffer.closed', self.url)
            dprint(u"removed buffer %s" % unicode(self.url))
            
            # If we don't have any more buffers with this basename, reset the
            # counter
            if not BufferList.findBuffersByBasename(basename):
                del self.filenames[basename]

    def isBasename(self, basename):
        return basename == self.stc.getShortDisplayName(self.raw_url)

    def setName(self):
        basename=self.stc.getShortDisplayName(self.raw_url)
        if basename in self.filenames:
            count=self.filenames[basename]+1
            self.filenames[basename]=count
            self.displayname=basename+"<%d>"%count
        else:
            self.filenames[basename]=1
            self.displayname=basename
        self.name=u"Buffer #%d: %s" % (self.count,unicode(self.url))

        # Update UI because the filename associated with this buffer
        # may have changed and that needs to be reflected in the menu.
        BufferList.calcHash()
        
    def getTabName(self):
        if self.modified:
            return u"*"+self.displayname
        return self.displayname

    def openGUIThreadStart(self):
        self.dprint(u"url: %s" % unicode(self.url))
        if self.defaultmode is None:
            self.defaultmode = MajorModeMatcherDriver.match(self)
        self.dprint("mode=%s" % (str(self.defaultmode)))

        self.stc = self.defaultmode.stc_class(self.dummyframe)

    def openBackgroundThread(self, progress_message=None):
        self.stc.open(self, progress_message)

    def openGUIThreadSuccess(self):
        # Only increment count on successful buffer loads
        Buffer.count+=1
        self.order_loaded = Buffer.count
        
        self.closeBufferedReader()
        
        self.stc.openSuccess(self)
        
        self.setName()

        self.modified = False
        
        # If it doesn't exist, that means we are creating the file, so it
        # should be writable.
        self.readonly = not (vfs.can_write(self.url) or not vfs.exists(self.url))
        #dprint("readonly = %s" % self.readonly)
        
        self.stc.EmptyUndoBuffer()

        # Add to the currently-opened buffer list
        BufferList.addBuffer(self)

        # Send a message to any interested plugins that a new buffer
        # has been successfully opened.
        Publisher().sendMessage('buffer.opened', self)

    def open(self):
        self.openGUIThreadStart()
        self.openBackgroundThread()
        self.openGUIThreadSuccess()

    def revert(self, encoding=None):
        # don't use the buffered reader: get a new file handle
        self.forEachView('revertPreHook')
        self.stc.revertEncoding(self, encoding=encoding)
        self.modified=False
        self.forEachView('applySettings')
        self.forEachView('revertPostHook')
        self.showModifiedAll()
        
    def save(self, url=None):
        assert self.dprint(u"Buffer: saving buffer %s as %s" % (unicode(self.url), url))
        try:
            if url is None:
                saveas = self.url
            else:
                saveas = vfs.normalize(url)
            self.stc.prepareEncoding()
            fh = vfs.open_write(saveas)
            self.stc.writeTo(fh, saveas)
            fh.close()
            self.stc.SetSavePoint()
            if saveas != self.url:
                self.setURL(saveas)
                self.setName()
            self.modified = False
            self.readonly = not vfs.can_write(saveas)
            self.showModifiedAll()
            self.saveTimestamp()
        except IOError:
            eprint(u"Failed writing to %s" % unicode(self.url))
            raise

    def showModifiedAll(self):
        for view in self.viewers:
            assert self.dprint("notifing: %s modified = %s" % (view, self.modified))
            view.showModified(self.modified)
        Publisher().sendMessage('buffer.modified', self)

    def setBusy(self, state):
        self.busy = state
        for view in self.viewers:
            assert self.dprint("notifing: %s busy = %s" % (view, self.busy))
            view.showBusy(self.busy)

    def startChangeDetection(self):
        if isinstance(self.stc, PeppySTC):
            self.stc.Bind(wx.stc.EVT_STC_CHANGE, self.OnChanged)

    def OnChanged(self, evt):
        #dprint("stc = %s" % self.stc)
        if self.stc.GetModify():
            assert self.dprint("modified!")
            changed=True
        else:
            assert self.dprint("clean!")
            changed=False
        if changed!=self.modified:
            self.modified=changed
            wx.CallAfter(self.showModifiedAll)


class BlankMode(MajorMode, wx.Window):
    """
    A temporary Major Mode to load another mode in the background
    """
    keyword = "Blank"
    icon='icons/application.png'
    temporary = True
    allow_threaded_loading = False
    
    stc_class = NonResidentSTC

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.Window.__init__(self, parent, -1, pos=(9000,9000))
        text = self.buffer.stc.GetText()
        lines = wx.StaticText(self, -1, text, (10,10))
        lines.Wrap(500)
        self.stc = self.buffer.stc
        self.buffer.stc.is_permanent = True

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:blank
        if url.scheme == 'about' and url.path == 'blank':
            return True
        return False


class LoadingSTC(NonResidentSTC):
    def __init__(self, text):
        self.text = text

    def GetText(self):
        return self.text


class LoadingMode(BlankMode):
    """
    A temporary Major Mode to load another mode in the background
    """
    keyword = 'Loading...'
    temporary = False
    stc_class = LoadingSTC

    def createPostHook(self):
        self.showBusy(True)
        wx.CallAfter(self.frame.openThreaded, self.buffer.raw_url,
                     self.buffer, mode_to_replace=self, options=self.buffer.options)

class LoadingBuffer(BufferVFSMixin, debugmixin):
    def __init__(self, url, modecls=None, created_from_url=None, canonicalize=True, options=None):
        BufferVFSMixin.__init__(self, url, created_from_url, canonicalize)
        self.busy = True
        self.readonly = False
        self.permanent = False
        self.modified = False
        self.defaultmode = LoadingMode
        self.options = options
        
        if modecls:
            if isinstance(modecls, basesting):
                self.modecls = MajorModeMatcherDriver.matchKeyword(modecls, self, url=self.raw_url)
                if not self.modecls:
                    raise TypeError("Unrecognized major mode keyword '%s'" % modecls)
            else:
                self.modecls = modecls
        else:
            self.modecls = MajorModeMatcherDriver.match(self, url=self.raw_url)
            self.dprint("found major mode = %s" % self.modecls)
        self.stc = LoadingSTC(unicode(url))
    
    def isTimestampChanged(self):
        """Override so that we don't attempt to pop up any dialogs when loading
        a file"""
        return False
    
    def allowThreadedLoading(self):
        return self.modecls.preferThreadedLoading(self.raw_url)
    
    def clone(self):
        """Get a real Buffer instance from this temporary buffer"""
        return Buffer(self.raw_url, self.modecls, self.created_from_url)

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


class BufferLoadThread(threading.Thread, debugmixin):
    """Background file loading thread.
    """
    def __init__(self, frame, user_url, buffer, mode_to_replace, progress=None, options=None):
        threading.Thread.__init__(self)
        
        self.frame = frame
        self.user_url = user_url
        self.buffer = buffer
        self.mode_to_replace = mode_to_replace
        self.progress = progress
        self.options = options

    def run(self):
        self.dprint(u"starting to load %s" % unicode(self.buffer.url))
        try:
            self.buffer.openBackgroundThread(self.progress.message)
            wx.CallAfter(self.frame.openSuccess, self.user_url, self.buffer,
                         self.mode_to_replace, self.progress, self.options)
            self.dprint(u"successfully loaded %s" % unicode(self.buffer.url))
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.dprint("Exception: %s" % str(e))
            wx.CallAfter(self.frame.openFailure, self.user_url, str(e),
                         self.mode_to_replace, self.progress)
