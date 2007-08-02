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
        print "Previous song!!!"
        mode = self.frame.getActiveMajorMode()
        mode.prevSong()

class NextSong(PlayingAction):
    name = _("Next Song")
    tooltip = _("Next Song")
    icon = 'icons/control_end.png'
    keyboard = "="
    
    def action(self, pos=None):
        print "Next song!!!"
        mode = self.frame.getActiveMajorMode()
        mode.nextSong()

class StopSong(PlayingAction):
    name = _("Stop")
    tooltip = _("Stop")
    icon = 'icons/control_stop.png'
    keyboard = "S"
    
    def action(self, pos=None):
        print "Stop playing!!!"
        mode = self.frame.getActiveMajorMode()
        mode.stop()

class PlayPause(SelectAction):
    name = _("Play/Pause Song")
    tooltip = _("Play/Pause Song")
    icon = 'icons/control_play.png'
    keyboard = "SPC"
    
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.isConnected()

    def action(self, pos=None):
        print "Play song!!!"
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
        'minor_modes': 'MPD Playlist,MPD Currently Playing',
        'update_interval': 1,
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

    def createWindowPostHook(self):
        self.update_timer = wx.Timer(self.editwin)
        self.editwin.Bind(wx.EVT_TIMER, self.OnTimer)

        self.update_timer.Start(self.settings.update_interval*1000)

    def OnTimer(self, evt):
        self.update()

    def initializeConnection(self):
        self.getStatus()
        dprint(self.last_status)
        
        outputs = self.mpd.outputs()

        print 'i got %d output(s)' % len(outputs)

        for output in outputs:
            print "here's an output"
            print "  id:", output.outputid
            print "  name:", output.outputname
            print "  enabled:", ('no', 'yes')[int(output.outputenabled)]

    def getStatus(self):
        self.last_status = self.mpd.status()
        #print self.last_status

    def update(self):
        self.getStatus()
        self.idle_update_menu = True
        for minor in self.minors:
            dprint(minor.window)
            minor.window.update(self.mpd)

    def reset(self):
        self.getStatus()
        self.idle_update_menu = True
        for minor in self.minors:
            dprint(minor.window)
            minor.window.reset(self.mpd)

    def isPlaying(self):
        return self.last_status['state'] == 'play'

    def isConnected(self):
        return self.mpd is not None

    def playPause(self):
        state = self.last_status['state']
        if state == 'play':
            self.mpd.pause(1)
        elif state == 'pause':
            # resume playing
            self.mpd.pause(0)
        else:
            self.mpd.play()
        self.update()

    def stop(self):
        state = self.last_status['state']
        if state != 'stop':
            self.mpd.stop()
        self.update()

    def prevSong(self):
        state = self.last_status['state']
        if state != 'stop':
            self.mpd.previous()
        self.update()

    def nextSong(self):
        state = self.last_status['state']
        if state != 'stop':
            self.mpd.next()
        self.update()



class PlaylistCtrl(wx.ListCtrl):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.LC_REPORT, mpd=None):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        self.mpd = mpd
        self.createColumns()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.default_font = self.GetFont()
        self.bold_font = wx.Font(
                    self.default_font.GetPointSize(), 
                    self.default_font.GetFamily(),
                    self.default_font.GetStyle(),
                    wx.BOLD
                    )
        
        self.songindex = -1

    def createColumns(self):
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Title")
        self.InsertColumn(2, "Artist")
        self.InsertColumn(3, "Time", wx.LIST_FORMAT_RIGHT)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        self.mpd.play(index)
        evt.Skip()
        
    def reset(self, mpd):
        playlist = mpd.playlistinfo()
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

    def highlightSong(self, newindex):
        if newindex == self.songindex:
            return
        
        if self.songindex>0:
            item = self.GetItem(self.songindex)
            item.SetFont(self.default_font)
            self.SetItem(item)
        self.songindex = newindex
        if newindex > 0:
            item = self.GetItem(self.songindex)
            item.SetFont(self.bold_font)
            self.SetItem(item)            
            self.EnsureVisible(newindex)
            
    def update(self, mpd):
        status = mpd.status()
        if status['state'] == 'stop':
            self.highlightSong(-1)
        else:
            self.highlightSong(int(status['songid']))


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
        self.playlist = PlaylistCtrl(parent, mpd=self.major.mpd)
        paneinfo = self.getDefaultPaneInfo(self.keyword)
        paneinfo.Right()
        self.major.addPane(self.playlist, paneinfo)
        dprint(paneinfo)

        self.playlist.reset(self.major.mpd)
        

class CurrentlyPlayingCtrl(wx.Panel,debugmixin):
    """Small control to display current song and stats.

    Displays current title, artist, and album, with controls for
    position in the song and play/pause controls.
    """
    debuglevel = 0

    def __init__(self, parent, minor):
        wx.Panel.__init__(self, parent)
        self.minor = minor

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.title = wx.StaticText(self)
        self.sizer.Add(self.title, flag=wx.EXPAND)

        self.slider = wx.Slider(self)
        self.sizer.Add(self.slider, flag=wx.EXPAND)

        self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderMove)
        self.slider.Bind(wx.EVT_SCROLL_CHANGED, self.OnSliderRelease)

        self.Layout()

        self.mpd = None
        self.songid = -1
        self.user_scrolling = False

    def OnSliderMove(self, evt):
        self.user_scrolling = True
        evt.Skip()
        
    def OnSliderRelease(self, evt):
        self.user_scrolling = False
        dprint(evt.GetPosition())
        self.mpd.seekid(self.songid, evt.GetPosition())

    def reset(self, mpd):
        self.mpd = mpd
        track = mpd.currentsong()
        if track:
            dprint(track)
            if 'title' not in track:
                title = track['file']
            else:
                title = track['title']
            self.title.SetLabel(title)
            self.slider.SetRange(0, int(track['time']))
            self.songid = int(track['id'])
        else:
            self.title.SetLabel('')
            self.slider.SetRange(0,1)
            self.slider.SetValue(0)
            self.songid = -1
        self.user_scrolling = False

    def update(self, mpd):
        status = mpd.status()
        if status['state'] == 'stop':
            self.slider.SetValue(0)
        else:
            if int(status['songid']) != self.songid:
                self.reset(mpd)

            if not self.user_scrolling:
                dprint(status)
                pos, tot = status['time'].split(":")
                self.slider.SetValue(int(pos))

    def OnSize(self, evt):
        self.Refresh()
        evt.Skip()

class MPDCurrentlyPlaying(MinorMode):
    """Minor mode to display the current playlist and controls for
    music playing.
    """
    keyword = "MPD Currently Playing"
    default_settings={
        'best_width': 400,
        'best_height': 100,
        'min_width': 300,
        'min_height': 50,
        }

    def createWindows(self, parent):
        self.playing = CurrentlyPlayingCtrl(parent, self)
        paneinfo = self.getDefaultPaneInfo(self.keyword)
        paneinfo.Right()
        self.major.addPane(self.playing, paneinfo)
        dprint(paneinfo)
        
        self.playing.reset(self.major.mpd)

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

    def possibleModes(self):
        yield MPDMode

    def getMinorModes(self):
        for mode in [MPDPlaylist, MPDCurrentlyPlaying]:
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

