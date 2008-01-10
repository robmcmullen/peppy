# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc

import peppy.vfs as vfs

from peppy.menu import *
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
    debuglevel = 0
    name = "Buffers"
    default_menu = ("Buffers", -500)
    inline = True
    
    # provide storage for the on demand global list
    storage = []

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
        return [buf.name for buf in self.storage]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index,BufferList.storage[index]))
        self.frame.setBuffer(BufferList.storage[index])
    

#### Buffers

class BufferVFSMixin(debugmixin):
    """Mixin class that compartmentalizes the interaction with the vfs
    
    """
    def __init__(self, url):
        self.bfh = None
        self.setURL(url)
        
    def setURL(self, url):
        if not url:
            url = vfs.normalize("untitled")
        else:
            url = vfs.canonical_reference(url)
        self.url = url

    def isURL(self, url):
        url = vfs.canonical_reference(url)
        if url == self.url:
            return True
        return False
    
    def getFilename(self):
        return str(self.url.path)

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
        elif self.url.scheme == 'file':
            path = os.path.normpath(os.path.dirname(str(self.url.path)))
            return path
        else:
            # See if the path converts to an existing path in the local
            # filesystem by converting it to a file:// url and seeing if any
            # path components exist
            lastpath = None
            uri = vfs.normalize(str(self.url.path))
            path = os.path.normpath(str(uri.path))
            while path != lastpath:
                #dprint("trying %s" % path)
                if os.path.isdir(path):
                    return path
                lastpath = path
                path = os.path.dirname(path)
        path = os.getcwd()
        return path
            
    def getBufferedReader(self, size=1024):
        assert self.dprint("opening %s as %s" % (str(self.url), self.defaultmode))
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
    debuglevel=0
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
        fh.write("Failed opening %s.\n\nDetailed error message follows:\n\n" % url)
        fh.write(error)
        fh.close()
        buffer = Buffer(errurl)
        buffer.openGUIThreadStart()
        buffer.openBackgroundThread()
        buffer.openGUIThreadSuccess()
        return buffer

    def __init__(self, url, defaultmode=None):
        BufferVFSMixin.__init__(self, url)
        
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
        dprint("cleaning up buffer %s" % self.url)

    def initSTC(self):
        self.stc.Bind(wx.stc.EVT_STC_CHANGE, self.OnChanged)

    def addViewer(self, mode):
        self.viewers.append(mode) # keep track of views
        assert self.dprint("views of %s: %s" % (self,self.viewers))

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
            basename=self.stc.getShortDisplayName(self.url)

            BufferList.remove(self)
            # Need to destroy the base STC or self will never get garbage
            # collected
            self.stc.Destroy()
            Publisher().sendMessage('buffer.closed', self.url)
            dprint("removed buffer %s" % self.url)
            
            # If we don't have any more buffers with this basename, reset the
            # counter
            if not BufferList.findBuffersByBasename(basename):
                del self.filenames[basename]

    def isBasename(self, basename):
        return basename == self.stc.getShortDisplayName(self.url)

    def setName(self):
        basename=self.stc.getShortDisplayName(self.url)
        if basename in self.filenames:
            count=self.filenames[basename]+1
            self.filenames[basename]=count
            self.displayname=basename+"<%d>"%count
        else:
            self.filenames[basename]=1
            self.displayname=basename
        self.name="Buffer #%d: %s" % (self.count,str(self.url))

        # Update UI because the filename associated with this buffer
        # may have changed and that needs to be reflected in the menu.
        BufferList.calcHash()
        
    def getTabName(self):
        if self.modified:
            return "*"+self.displayname
        return self.displayname

    def openGUIThreadStart(self):
        self.dprint("url: %s" % str(self.url))
        if self.defaultmode is None:
            self.defaultmode = MajorModeMatcherDriver.match(self)
        self.dprint("mode=%s" % (str(self.defaultmode)))

        self.stc = self.defaultmode.stc_class(self.dummyframe)

    def openBackgroundThread(self, progress_message=None):
        self.stc.open(self, progress_message)

    def openGUIThreadSuccess(self):
        # Only increment count on successful buffer loads
        Buffer.count+=1
        
        self.closeBufferedReader()
        
        self.setName()

        if isinstance(self.stc,PeppySTC):
            self.initSTC()

        self.modified = False
        
        # If it doesn't exist, that means we are creating the file, so it
        # should be writable.
        self.readonly = not (vfs.can_write(self.url) or not vfs.exists(self.url))
        #dprint("readonly = %s" % self.readonly)
        
        self.stc.EmptyUndoBuffer()

        # Add to the currently-opened buffer list
        BufferList.append(self)

        # Send a message to any interested plugins that a new buffer
        # has been successfully opened.
        Publisher().sendMessage('buffer.opened', self)

    def open(self):
        self.openGUIThreadStart()
        self.openBackgroundThread()
        self.openGUIThreadSuccess()

    def revert(self):
        # don't use the buffered reader: get a new file handle
        fh = vfs.open(self.url)
        self.stc.ClearAll()
        self.stc.readFrom(fh)
        self.modified=False
        self.stc.EmptyUndoBuffer()
        wx.CallAfter(self.showModifiedAll)
        
    def save(self, url=None):
        assert self.dprint("Buffer: saving buffer %s" % (self.url))
        try:
            if url is None:
                saveas = self.url
            else:
                saveas = vfs.normalize(url)
            if vfs.exists(saveas):
                if vfs.is_file(saveas):
                    fh = vfs.open(saveas, vfs.WRITE)
                else:
                    raise OSError("%s exists and is a directory; can't save as file" % saveas)
            else:
                fh = vfs.make_file(saveas)
            self.stc.writeTo(fh)
            fh.close()
            self.stc.SetSavePoint()
            if saveas != self.url:
                self.setURL(saveas)
                self.setName()
            self.modified = False
            self.readonly = not vfs.can_write(saveas)
            self.showModifiedAll()
        except:
            eprint("Failed writing to %s" % self.url)
            raise

    def showModifiedAll(self):
        for view in self.viewers:
            assert self.dprint("notifing: %s modified = %s" % (view, self.modified))
            view.showModified(self.modified)
        wx.GetApp().enableFrames()
        Publisher().sendMessage('buffer.modified', self)

    def setBusy(self, state):
        self.busy = state
        for view in self.viewers:
            assert self.dprint("notifing: %s busy = %s" % (view, self.busy))
            view.showBusy(self.busy)
        wx.GetApp().enableFrames()

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
        wx.CallAfter(self.frame.openThreaded, self.buffer.user_url,
                     self.buffer, mode_to_replace=self)

class LoadingBuffer(BufferVFSMixin, debugmixin):
    debuglevel = 0
    
    def __init__(self, url, modecls=None):
        self.user_url = url
        BufferVFSMixin.__init__(self, url)
        self.busy = True
        self.readonly = False
        self.permanent = False
        self.modified = False
        self.defaultmode = LoadingMode
        
        if modecls:
            self.modecls = modecls
        else:
            self.modecls = MajorModeMatcherDriver.match(self)
            self.dprint("found major mode = %s" % self.modecls)
        self.stc = LoadingSTC(str(url))
    
    def allowThreadedLoading(self):
        return self.modecls.allow_threaded_loading
    
    def clone(self):
        """Get a real Buffer instance from this temporary buffer"""
        return Buffer(self.url, self.modecls)

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
    def __init__(self, frame, user_url, buffer, mode_to_replace, progress=None):
        threading.Thread.__init__(self)
        
        self.frame = frame
        self.user_url = user_url
        self.buffer = buffer
        self.mode_to_replace = mode_to_replace
        self.progress = progress

        self.start()

    def run(self):
        self.dprint("starting to load %s" % self.buffer.url)
        try:
            self.buffer.openBackgroundThread(self.progress.message)
            wx.CallAfter(self.frame.openSuccess, self.user_url, self.buffer,
                         self.mode_to_replace, self.progress)
            self.dprint("successfully loaded %s" % self.buffer.url)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.dprint("Exception: %s" % str(e))
            wx.CallAfter(self.frame.openFailure, self.user_url, str(e),
                         self.mode_to_replace, self.progress)
