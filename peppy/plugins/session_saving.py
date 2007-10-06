# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Session saving and restoration plugin.  Hooks into the configuration
file loading and saving in order to get the cue when to load and save
the list of files.
"""
import os

from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.lib.userparams import *
from peppy.buffers import *
from peppy.frame import *

class SessionSave(ClassPrefs):
    default_classprefs = (
        StrParam('session_file', 'session.txt'),
        BoolParam('save_on_exit', True),
        BoolParam('restore_on_start', True),
        )
    
    @classmethod
    def getFile(cls):
        filename=cls.classprefs.session_file
        app = wx.GetApp()
        pathname=app.getConfigFilePath(filename)
        return pathname
    
    @classmethod
    def restore(cls, msg):
        dprint("Restoring session if %s == True" % cls.classprefs.restore_on_start)
        if not cls.classprefs.restore_on_start:
            return
        
        pathname = cls.getFile()
        try:
            fh=open(pathname)
        except:
            return

        # Check to see if we've started up, but the existing frame
        # only has something temporary like the title buffer
        frames = FrameList.getFrames()
        dprint(frames)
        use_frame = None
        if len(frames) == 1:
            if frames[0].isTitleBufferOnly():
                # FIXME: Yep, it's the title buffer, which should be a
                # temporary buffer but currently it's not marked that
                # way.  Fix that here for the moment
                mode = frames[0].getActiveMajorMode()
                mode.temporary = True
                use_frame = frames[0]
        dprint(use_frame)
        
        args = []
        for line in fh:
            if line.startswith("--- frame"):
                if args:
                    if use_frame:
                        use_frame.loadList(args)
                        use_frame = None
                    else:
                        frame = BufferFrame(args)
                        frame.Show()
                args = []
            elif line.startswith("url "):
                args.append(line[4:].strip())
        if args:
            if use_frame:
                use_frame.loadList(args)
            else:
                frame = BufferFrame(args)
                frame.Show()

    @classmethod
    def save(cls, msg):
        pathname = cls.getFile()
        if cls.classprefs.save_on_exit:
            fh=open(pathname,'w')

            buffers = BufferList.getBuffers()
            dprint(buffers)
            for buf in buffers:
                dprint("url=%s permanent=%s" % (buf.url, buf.permanent))
            frames = FrameList.getFrames()
            dprint(frames)
            for frame in frames:
                modes = frame.getAllMajorModes()
                dprint(frame)
                fh.write("--- frame%s" % os.linesep)
                for mode in modes:
                    dprint(mode.buffer.url)
                    fh.write("url %s%s" % (mode.buffer.url, os.linesep))
        else:
            if os.path.exists(pathname):
                try:
                    os.remove(pathname)
                except:
                    pass

class SessionSavingPlugin(IPeppyPlugin):
    def activate(self):
        IPeppyPlugin.activate(self)
        Publisher().subscribe(SessionSave.restore, 'peppy.in.mainloop')
        Publisher().subscribe(SessionSave.save, 'peppy.config.save')

    def deactivate(self):
        IPeppyPlugin.deactivate(self)
        Publisher().unsubscribe(SessionSave.restore)
        Publisher().unsubscribe(SessionSave.save)
