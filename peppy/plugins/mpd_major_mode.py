# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""MPD (Music Player Daemon) mode.

Major mode for controlling an MPD server.

http://mpd.wikia.com/wiki/MusicPlayerDaemonCommands shows the commands
available to the mpd server.  I was confused about the difference
between a song and a songid in a status message, and id and pos in the
currentsong message...  It appears that"song" and "id" refer to the
position in the current playlist, and "id" and "songid" refer to the
position in the original unshuffled playlist.
"""

import os, struct, mmap
import urllib2
from cStringIO import StringIO

import wx
import wx.lib.newevent
import wx.lib.stattext

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *

from peppy.lib.mpdclient2 import mpd_connection

class MPDWrapper(mpd_connection):
    """Wrapper around mpd_connection to save state information.

    Small wrapper around mpdclient2's mpd_connection object to save
    state information about the mpd instance.  All views into the mpd
    instance and all minor modes that access the mpd object will then
    share the same information, rather than having to look somewhere
    else to find it.
    """
    def __init__(self, *args, **kw):
        mpd_connection.__init__(self, *args, **kw)

        self.save_mute = -1
        self.last_status = {'state': 'stop'}
        
    def isPlaying(self):
        """True if playing music; false if paused or stopped."""
        return self.last_status['state'] == 'play'

    def getStatus(self):
        self.last_status = self.status()
        #print self.last_status

    def playPause(self):
        """User method to play or pause.

        Called to play music either from a stopped state or to resume
        from pause.
        """
        state = self.last_status['state']
        if state == 'play':
            self.pause(1)
        elif state == 'pause':
            # resume playing
            self.pause(0)
        else:
            self.play()

    def stopPlaying(self):
        """User method to stop playing."""
        state = self.last_status['state']
        if state != 'stop':
            self.stop()

    def prevSong(self):
        """User method to skip to previous song.

        Usable only when playing.
        """
        state = self.last_status['state']
        if state != 'stop':
            self.previous()

    def nextSong(self):
        """User method to skip to next song.

        Usable only when playing.
        """
        state = self.last_status['state']
        if state != 'stop':
            self.next()

    def volumeUp(self, step):
        """Increase volume, usable at any time.

        Volume ranges from 0 - 100 inclusive.

        @param step: step size to increase
        """
        vol = int(self.last_status['volume']) + step
        if vol > 100: vol = 100
        self.setvol(vol)
        self.save_mute = -1

    def volumeDown(self, step):
        """Decrease volume, usable at any time.

        Volume ranges from 0 - 100 inclusive.

        @param step: step size to increase
        """
        vol = int(self.last_status['volume']) - step
        if vol < 0: vol = 0
        self.setvol(vol)
        self.save_mute = -1

    def setMute(self):
        """Mute or unmute, usable at any time

        Mute volume or restore muted sound to previous volume level.
        """
        if self.save_mute < 0:
            self.save_mute = int(self.last_status['volume'])
            vol = 0
        else:
            vol = self.save_mute
            self.save_mute = -1
        self.setvol(vol)



class PlayingAction(SelectAction):    
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.mpd.isPlaying()

class PrevSong(PlayingAction):
    name = _("Prev Song")
    tooltip = _("Previous Song")
    icon = 'icons/control_start.png'
    keyboard = "-"
    
    def action(self, pos=None):
        print "Previous song!!!"
        mode = self.frame.getActiveMajorMode()
        mode.mpd.prevSong()
        mode.update()

class NextSong(PlayingAction):
    name = _("Next Song")
    tooltip = _("Next Song")
    icon = 'icons/control_end.png'
    keyboard = "="
    
    def action(self, pos=None):
        print "Next song!!!"
        mode = self.frame.getActiveMajorMode()
        mode.mpd.nextSong()
        mode.update()

class StopSong(PlayingAction):
    name = _("Stop")
    tooltip = _("Stop")
    icon = 'icons/control_stop.png'
    keyboard = "S"
    
    def action(self, pos=None):
        print "Stop playing!!!"
        mode = self.frame.getActiveMajorMode()
        mode.mpd.stopPlaying()
        mode.update()

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
        mode.mpd.playPause()
        mode.update()

class Mute(PlayPause):
    name = _("Mute")
    tooltip = _("Mute the volume")
    icon = 'icons/sound_mute.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.setMute()
        mode.update()

class VolumeUp(PlayPause):
    name = _("Increase Volume")
    tooltip = _("Increase the volume")
    icon = 'icons/sound.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.volumeUp(mode.settings.volume_step)
        mode.update()

class VolumeDown(PlayPause):
    name = _("Decrease Volume")
    tooltip = _("Decrease the volume")
    icon = 'icons/sound_low.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.volumeDown(mode.settings.volume_step)
        mode.update()

class MPDSTC(NonResidentSTC):
    def openPostHook(self, fh):
        """Save the file handle, which is really the mpd connection"""
        
        self.mpd = fh


class MPDMode(MajorMode):
    """Major mode for controlling a Music Player Daemon.

    ...
    """
    debug_level = 0
    keyword='MPD'
    icon='icons/mpd.ico'

    mmap_stc_class = MPDSTC

    default_settings = {
        'minor_modes': 'MPD Playlist,MPD Currently Playing',
        'update_interval': 1,
        'volume_step': 10,
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
        self.mpd.getStatus()
        dprint(self.mpd.last_status)
        
        outputs = self.mpd.outputs()

        print 'i got %d output(s)' % len(outputs)

        for output in outputs:
            print "here's an output"
            print "  id:", output.outputid
            print "  name:", output.outputname
            print "  enabled:", ('no', 'yes')[int(output.outputenabled)]

    def update(self):
        self.mpd.getStatus()
        self.idle_update_menu = True
        for minor in self.minors:
            self.dprint(minor.window)
            minor.window.update()

    def reset(self):
        self.mpd.getStatus()
        self.idle_update_menu = True
        for minor in self.minors:
            self.dprint(minor.window)
            minor.window.reset()

    def isConnected(self):
        return self.mpd is not None




class PlaylistCtrl(wx.ListCtrl):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.LC_REPORT, mpd=None):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        self.mpd = mpd
        self.createColumns()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)
        self.Bind(wx.EVT_LEFT_UP, self.OnEndDrag)

        self.default_font = self.GetFont()
        self.bold_font = wx.Font(self.default_font.GetPointSize(), 
                                 self.default_font.GetFamily(),
                                 self.default_font.GetStyle(),wx.BOLD)
        
        self.songindex = -1
        self.dragging = None

    def createColumns(self):
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Title")
        self.InsertColumn(2, "Artist")
        self.InsertColumn(3, "Time", wx.LIST_FORMAT_RIGHT)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        self.mpd.play(index)
        evt.Skip()
        
    def OnStartDrag(self, evt):
        index = evt.GetIndex()
        print "beginning drag of item %d" % index
        self.dragging = index

    def _getDropIndex(self, x, y):
        """Find the index to insert the new item, given x & y coords."""

        # Find insertion point.
        index, flags = self.HitTest((x, y))

        if index == wx.NOT_FOUND: # not clicked on an item
            if (flags & (wx.LIST_HITTEST_NOWHERE|wx.LIST_HITTEST_ABOVE|wx.LIST_HITTEST_BELOW)): # empty list or below last item
                index = self.GetItemCount() # append to end of list
            elif (self.GetItemCount() > 0):
                if y <= self.GetItemRect(0).y: # clicked just above first item
                    index = 0 # append to top of list
                else:
                    index = self.GetItemCount() + 1 # append to end of list
        else: # clicked on an item
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)

            # If the user is dropping into the lower half of the rect, we want to insert _after_ this item.
            # Correct for the fact that there may be a heading involved
            if y > (rect.y - self.GetItemRect(0).y + rect.height/2):
                index = index + 1

        return index

    def OnEndDrag(self, evt):
        if self.dragging:
            x = evt.GetX()
            y = evt.GetY()
            index = self._getDropIndex(x, y)
            print "dropping item %d at %s -> index=%d" % (self.dragging, (x,y), index)

            self.mpd.move(self.dragging, index)
            self.reset()
            self.update()
            self.dragging = None
        
    def reset(self, mpd=None):
        if mpd is not None:
            self.mpd = mpd
        playlist = self.mpd.playlistinfo()
        list_count = self.GetItemCount()
        index = 0
        for track in playlist:
            if index >= list_count:
                self.InsertStringItem(sys.maxint, str(index+1))
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

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)

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
            
    def update(self):
        status = self.mpd.status()
        if status['state'] == 'stop':
            self.highlightSong(-1)
        else:
            self.highlightSong(int(status['song']))


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

        # NOTE: the standard wx.StaticText automatically word wrapped
        # text even though I set Wrap(-1).  Fixed by using the
        # GenStaticText control
        self.title = wx.lib.stattext.GenStaticText(self, -1, ' ', style=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE)
        
        self.sizer.Add(self.title, 0, wx.EXPAND)

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

    def reset(self, mpd=None):
        if mpd is not None:
            self.mpd = mpd
        track = self.mpd.currentsong()
        if track:
            dprint("currentsong: \n%s" % track)
            dprint("status: \n%s" % self.mpd.last_status)
            if 'title' not in track:
                title = track['file']
            else:
                title = track['title']
                if 'artist' in track:
                    title += " -- %s" % track['artist']
            self.title.SetLabel(title)
            self.slider.SetRange(0, int(track['time']))
            self.songid = int(track['id'])
        else:
            self.title.SetLabel('')
            self.slider.SetRange(0,1)
            self.slider.SetValue(0)
            self.songid = -1
        self.user_scrolling = False

    def update(self):
        status = self.mpd.status()
        if status['state'] == 'stop':
            self.slider.SetValue(0)
        else:
            if int(status['songid']) != self.songid:
                self.reset()

            if not self.user_scrolling:
                self.dprint(status)
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
                  ("MPD",_("MPD"),MenuItem(NextSong)),
                  ("MPD",_("MPD"),Separator("volume")),
                  ("MPD",_("MPD"),MenuItem(VolumeUp)),
                  ("MPD",_("MPD"),MenuItem(VolumeDown)),
                  ("MPD",_("MPD"),MenuItem(Mute)),
                   )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("MPD",None,Menu(_("MPD")).after("Major Mode")),
                  ("MPD",_("MPD"),MenuItem(PrevSong)),
                  ("MPD",_("MPD"),MenuItem(StopSong)),
                  ("MPD",_("MPD"),MenuItem(PlayPause)),
                  ("MPD",_("MPD"),MenuItem(NextSong)),
                  ("MPD",_("MPD"),Separator("volume")),
                  ("MPD",_("MPD"),MenuItem(VolumeDown)),
                  ("MPD",_("MPD"),MenuItem(VolumeUp)),
                  ("MPD",_("MPD"),MenuItem(Mute)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

