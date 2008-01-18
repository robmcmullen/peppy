# peppy Copyright (c) 2006-2008 Rob McMullen
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

class SessionManagerPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('session_file', 'session.txt', 'Filename used in the peppy configuration directory\nto store the session information.'),
        BoolParam('save_on_exit', False, 'Whether to save the session on exit'),
        BoolParam('restore_on_start', False, 'Whether to restore the session on startup'),
        )
    
    restore_session_cmdline = True
    
    def activate(self):
        IPeppyPlugin.activate(self)
        # Can't use regular initialActivation method, because we need
        # to wait until the GUI is initialized
        Publisher().subscribe(self.restore, 'peppy.in.mainloop')

    def deactivate(self):
        IPeppyPlugin.deactivate(self)
        Publisher().unsubscribe(self.restore)

    def addCommandLineOptions(self, parser):
        parser.add_option("--no-session", action="store_false",
                          dest="restore_session", default=True,
                          help="Do not restore saved session")

    def processCommandLineOptions(self, options):
        #dprint(options.restore_session)
        self.restore_session_cmdline = options.restore_session

    def getFile(self):
        filename=self.classprefs.session_file
        app = wx.GetApp()
        pathname=app.getConfigFilePath(filename)
        return pathname
    
    def restore(self, msg):
        if not self.restore_session_cmdline:
            # command line overrules all
            return
        
        if not self.classprefs.restore_on_start:
            return
        
        pathname = self.getFile()
        try:
            fh=open(pathname)
        except:
            return

        # Check to see if we've started up, but the existing frame
        # only has something temporary like the title buffer
        frames = WindowList.getFrames()
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

    def requestedShutdown(self):
        pathname = self.getFile()
        if self.classprefs.save_on_exit:
            fh=open(pathname,'w')

            buffers = BufferList.getBuffers()
            dprint(buffers)
            for buf in buffers:
                dprint("url=%s permanent=%s" % (buf.url, buf.permanent))
            frames = WindowList.getFrames()
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

