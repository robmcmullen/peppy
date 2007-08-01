# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""MPD (Music Player Daemon) mode.

Major mode for controlling an MPD server.

http://mpd.wikia.com/wiki/MusicPlayerDaemonCommands
"""

import os, struct, mmap
import urllib2
from cStringIO import StringIO

import wx
import wx.lib.newevent

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *

from peppy.lib.mpdclient2 import mpd_connection

class MPDWrapper(mpd_connection):
    def read(self, size=None):
        """Dummy function to satisfy PeppySTC's need to classify the buffer"""

        return "MPD Client"

class MPDHandler(urllib2.BaseHandler):
    def mpd_open(self, req):
        dprint(req)
        url = req.get_host()
        dprint(url)

        comp_mgr = ComponentManager()
        handler = MPDPlugin(comp_mgr)
        fh = MPDWrapper(url, 6600)
        fh.geturl = lambda :"mpd:%s" % url
        fh.info = lambda :{'Content-type': 'text/plain',
                           'Content-length': 0,
                           'Last-modified': 'Sat, 17 Feb 2007 20:29:30 GMT',
                           'Default-mode': MPDMode,
                            }
        
        return fh




class PlayingAction(SelectAction):    
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.isPlaying()

class PrevSong(PlayingAction):
    name = _("Prev Song")
    tooltip = _("Previous Song")
    icon = 'icons/control_start.png'
    keyboard = "-"
    
    def action(self, pos=None):
        print "Previous band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.prevSong()

class NextSong(PlayingAction):
    name = _("Next Song")
    tooltip = _("Next Song")
    icon = 'icons/control_end.png'
    keyboard = "="
    
    def action(self, pos=None):
        print "Previous band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.nextSong()

class StopSong(PlayingAction):
    name = _("Stop")
    tooltip = _("Stop")
    icon = 'icons/control_stop.png'
    keyboard = "S"
    
    def action(self, pos=None):
        print "Previous band!!!"
        mode = self.frame.getActiveMajorMode()
        mode.nextSong()

class PlayPause(SelectAction):
    name = _("Play/Pause Song")
    tooltip = _("Play/Pause Song")
    icon = 'icons/control_play.png'
    keyboard = "SPC"
    
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.isConnected()

    def action(self, pos=None):
        print "Play son!!!"
        mode = self.frame.getActiveMajorMode()
        mode.playPause()


class MPDSTC(NonResidentSTC):
    def openPostHook(self, fh):
        """Save the file handle, which is really the mpd connection"""
        
        self.mpd = fh


class MPDMode(MajorMode):
    """Major mode for controlling a Music Player Daemon.

    ...
    """
    keyword='MPD'
    icon='icons/mpd.ico'

    mmap_stc_class = MPDSTC

    default_settings = {
        'minor_modes': 'MPD Playlist',
        }
    
    def createEditWindow(self,parent):
        """Create the main MPD music search window.

        @param parent: parent window in which to create this window 
        """
        self.stc = self.buffer.stc
        self.mpd = self.stc.mpd
        self.initializeConnection()
        win = wx.ListCtrl(parent)
        return win

    def initializeConnection(self):
        self.last_status = self.mpd.status()
        print self.last_status

        outputs = self.mpd.outputs()

        print 'i got %d output(s)' % len(outputs)

        for output in outputs:
            print "here's an output"
            print "  id:", output.outputid
            print "  name:", output.outputname
            print "  enabled:", ('no', 'yes')[int(output.outputenabled)]

    def isPlaying(self):
        return self.last_status['state'] == 'play'

    def isConnected(self):
        return self.mpd is not None



class PlaylistCtrl(wx.ListCtrl):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.LC_REPORT):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        self.createColumns()

    def createColumns(self):
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Title")
        self.InsertColumn(2, "Artist")
        self.InsertColumn(3, "Time", wx.LIST_FORMAT_RIGHT)

    def replacePlaylist(self, playlist):
        self.DeleteAllItems()
        count = 0
        for track in playlist:
            count += 1
            index = self.InsertStringItem(sys.maxint, str(count))
            if 'title' not in track:
                title = track['file']
            else:
                title = track['title']
            self.SetStringItem(index, 1, title)
            if 'album' not in track:
                album = ''
            else:
                album = track['album']
            self.SetStringItem(index, 2, album)
            self.SetStringItem(index, 3, str(track['time']))


class MPDPlaylist(MinorMode):
    """Minor mode to display the current playlist and controls for
    music playing.
    """
    keyword = "MPD Playlist"
    default_settings={
        'best_width': 400,
        'best_height': 400,
        'min_width': 300,
        'min_height': 100,
        }

    def createWindows(self, parent):
        self.playlist = PlaylistCtrl(parent)
        paneinfo = self.getDefaultPaneInfo(self.keyword)
        paneinfo.Right()
        self.major.addPane(self.playlist, paneinfo)
        dprint(paneinfo)

        self.setupPlaylist()

    def setupPlaylist(self):
        mpd = self.major.mpd
        
        playlist = mpd.playlistinfo()

        print 'i got %d playlist entry item(s)' % len(playlist)

        for output in playlist:
            print output

        self.playlist.replacePlaylist(playlist)


class MPDPlugin(MajorModeMatcherBase,debugmixin):
    """HSI viewer plugin to register modes and user interface.
    """
    implements(IMajorModeMatcher)
    implements(IMinorModeProvider)
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)
    implements(IURLHandler)

    def getURLHandlers(self):
        return [MPDHandler]

    def scanFilename(self, url):
        if url.startswith("mpd:"):
            return MajorModeMAtch(MPDMode, exact=True)
        return None
    
    def possibleModes(self):
        yield MPDMode

    def getMinorModes(self):
        for mode in [MPDPlaylist]:
            yield mode
    
    default_menu=(("MPD",None,Menu(_("MPD")).after("Major Mode")),
                  ("MPD",_("MPD"),MenuItem(PrevSong)),
                  ("MPD",_("MPD"),MenuItem(StopSong)),
                  ("MPD",_("MPD"),MenuItem(PlayPause)),
                  ("MPD",_("MPD"),MenuItem(NextSong)),
                   )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("MPD",None,Menu(_("MPD")).after("Major Mode")),
                  ("MPD",_("MPD"),MenuItem(PrevSong)),
                  ("MPD",_("MPD"),MenuItem(StopSong)),
                  ("MPD",_("MPD"),MenuItem(PlayPause)),
                  ("MPD",_("MPD"),MenuItem(NextSong)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

