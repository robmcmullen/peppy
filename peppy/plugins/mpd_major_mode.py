# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""MPD (Music Player Daemon) mode.

Major mode for controlling an MPD server.

http://mpd.wikia.com/wiki/MusicPlayerDaemonCommands shows the commands
available to the mpd server.  I was confused about the difference
between a song and a songid in a status message, and id and pos in the
currentsong message...  It appears that "song" and "id" refer to the
position in the current playlist, and "id" and "songid" refer to the
position in the original unshuffled playlist.
"""

import os, struct, mmap, Queue, threading, time, socket
import urllib2
from cStringIO import StringIO
import cPickle as pickle

import wx
import wx.lib.stattext
import wx.lib.newevent
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager

from peppy.mainmenu import OpenDialog
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.yapsy.plugins import *
from peppy.about import SetAbout
from peppy.lib.iconstorage import *
from peppy.lib.columnsizer import *
from peppy.lib.dropscroller import *
from peppy.lib.nextpanel import *
from peppy.lib.mpdclient2 import mpd_connection

from peppy.about import AddCredit

AddCredit("Nick Welch", "for the public domain mpd client py-libmpdclient2")


def getTitle(track):
    """Convenience function to return title of a track"""
    if 'title' in track:
        title = track['title']
    elif 'file' in track:
        title = os.path.basename(track['file'])
    else:
        title = str(track)
    return title

def getAlbum(track):
    """Convenience function to return album of a track"""
    if 'album' not in track:
        album = ''
    else:
        album = track['album']
    return album

def getArtist(track):
    """Convenience function to return album of a track"""
    if 'artist' not in track:
        artist = ''
    else:
        artist = track['artist']
    return artist

def getTimeString(seconds):
    if seconds < 60:
        minutes = 0
    else:
        minutes = seconds / 60
        seconds = seconds % 60
    if minutes < 60:
        return "%d:%02d" % (minutes, seconds)
    hours = minutes / 60
    minutes = minutes % 60
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def getTime(track):
    """Convenience function to return album of a track"""
    seconds = int(track['time'])
    return getTimeString(seconds)

MpdSongChanged, EVT_MPD_SONG_CHANGED = wx.lib.newevent.NewEvent()
MpdSongTime, EVT_MPD_SONG_TIME = wx.lib.newevent.NewEvent()
MpdPlaylistChanged, EVT_MPD_PLAYLIST_CHANGED = wx.lib.newevent.NewEvent()
MpdLoggedIn, EVT_MPD_LOGGED_IN = wx.lib.newevent.NewEvent()

class MPDCommand(debugmixin):
    # The following commands or changes in attributes generate events
    check_events = {'playlistinfo': MpdPlaylistChanged,
                    'currentsong': MpdSongChanged,
                    'state': MpdSongChanged,
                    'time': MpdSongTime,
                    'login': MpdLoggedIn,
                    }

    # If the attribute changes in status, call the corresponding
    # command
    attribute_change_commands = {'playlist': 'playlistinfo',
                                 'songid': 'currentsong',
                                 }

    def __init__(self, cmd=None, args=[], **kw):
        self.cmd = cmd
        self.args = args
        if kw and 'callback' in kw:
            self.callback = kw['callback']
        else:
            self.callback = None
        if kw and 'sync' in kw:
            self.sync_dict, self.sync_key = kw['sync']
        else:
            self.sync_dict = None
        if kw and 'result' in kw:
            self.retq = kw['result']
        else:
            self.retq = None

    def process(self, mpd, output):
        assert self.dprint("processing cmd=%s, args=%s sync=%s queue=%s" % (self.cmd, str(self.args), self.sync_dict, self.retq))
        if self.cmd is None:
            return

        if mpd.needs_reopen:
            try:
                mpd.setup()
            except:
                assert self.dprint("Still needs reopening.  Will try again next time.")
                return

        try:
            if mpd.do.flush_pending:
                mpd.do.flush()
        except socket.error, e:
            # Not a lot of documentation on socket.error, but I did
            # determine out that e is of class socket.error, and can
            # be accessed like a tuple.
            if isinstance(e[0], str):
                # It's a string error, so it's likely a timeout.  I'm
                # assuming that it's not important enough to attempt
                # to regenerate the connection.
                import traceback
                traceback.print_exc()

                assert self.dprint("Still no connection; flush still pending")
                return
            else:
                # OK, it's an integer value, meaning the error is an
                # underlying operating system error.  Previously, I
                # was checking only for errno.ECONNRESET, but there
                # are other errors that get returned as well.  So, I'm
                # assuming that if we get an operating system error,
                # the connection is never going to come back on its
                # own.  So, we reopen it.
                assert self.dprint("Attempting to reopen connection: e=%s class=%s e[0]=c%s" % (e, e.__class__, str(e[0])))
                mpd.setup()

        try:
            ret = mpd.do.send_n_fetch(self.cmd, self.args)
        except Exception, e:
            assert self.dprint("Caught send_n_fetch exception.  Setting pending_flush=True")
            mpd.do.flush_pending = True
            return

        if self.cmd == 'status':
            self.status(ret, output)
        elif self.cmd in self.check_events:
            #assert self.dprint("setting %s = %s" % (self.cmd, ret))
            setattr(output, self.cmd, ret)
            evt = self.check_events[self.cmd]
            wx.PostEvent(wx.GetApp(), evt(mpd=output, status=output.status))

        if self.callback:
            wx.CallAfter(self.callback, self, ret)

        if self.sync_dict is not None:
            #assert self.dprint("Setting dict[%d] to %s" % (self.sync_key, ret))
            self.sync_dict[self.sync_key] = ret

        if self.retq is not None:
            #assert self.dprint("Setting return value to %s" % ret)
            self.retq.put(ret)
            
    
    def status(self, status, output):
        if 'state' not in status:
            # If state doesn't exist, that means that we don't have
            # permissions for playback.
            status['login'] = False
        else:
            status['login'] = True
        
        # kick off the followup commands if an attribute change means
        # that other data should be updated.  For example, if the
        # playlist attribute changes, that means that the playlist has
        # changed and playlistinfo should be called.
        for attr, cmd in self.attribute_change_commands.iteritems():
            if attr in status:
                if attr not in output.status or status[attr] != output.status[attr]:
                    output.queue.put(MPDCommand(cmd))

        # If one of the check_events attributes has changed, fire a wx
        # event to let the UI know that something has happened.
        for attr, evt in self.check_events.iteritems():
            if attr in status:
                if attr not in output.status or status[attr] != output.status[attr]:
                    assert self.dprint("Posting event %s" % evt)
                    wx.PostEvent(wx.GetApp(), evt(mpd=output, status=status))

        output.status = status


class ThreadedMPD(threading.Thread, debugmixin):
    """Thread control of a mpd instance

    Simple container for an mpd_connection object that provides the
    connection between the GUI thread and the mpd thread.
    """
    def __init__(self, output, queue, host, port, timeout=0.5):
        threading.Thread.__init__(self)
        
        self.output = output
        self.queue = queue
        self.mpd = mpd_connection(host, port, timeout)

        self._want_abort = False
        self.start()

    def shutdown(self):
        self._want_abort = True
        self.queue.put(MPDCommand())

    def run(self):
        while(not self._want_abort):
            cmd = self.queue.get()
            assert self.dprint("queue size=%d" % self.queue.qsize())
            if cmd is not None:
                try:
                    cmd.process(self.mpd, self.output)
                except Exception, e:
                    import traceback
                    traceback.print_exc()
                    #print "Exception: %s" % str(e)

                


class MPDComm(debugmixin):
    """Wrapper around mpd_connection to save state information.

    Small wrapper around mpdclient2's mpd_connection object to save
    state information about the mpd instance.  All views into the mpd
    instance and all minor modes that access the mpd object will then
    share the same information, rather than having to look somewhere
    else to find it.
    """
    def __init__(self, host, port, timeout=0.5):
        self.queue = Queue.Queue()
        self.thread = ThreadedMPD(self, self.queue, host, port, timeout)
        
        self.save_mute = -1
        self.status = {'state': 'stop'}
        self.playlistinfo = []
        self.currentsong = {}
        self.songid = -1

        self.sync_counter = 0
        self.sync_dict = {}
        self.sync_sleep = 0.1
        self.sync_abort = 10
        self.sync_timeout = 0.2
        
        Publisher().subscribe(self.shutdown, 'peppy.shutdown')

    def reset(self):
        self.playlistinfo = []
        self.currentsong = {}
        self.cmd('status')
        
    def shutdown(self, msg=None):
        self.thread.shutdown()

    def cmd(self, cmd, *args):
        self.queue.put(MPDCommand(cmd, args))

    def sync(self, cmd, *args, **kw):
        queue = Queue.Queue()
        self.queue.put(MPDCommand(cmd, args, result=queue))
        assert self.dprint("Waiting for %s" % cmd)
        if 'timeout' in kw:
            timeout = kw['timeout']
        else:
            timeout = self.sync_timeout
        ret = queue.get(True, timeout)
        assert self.dprint("Got result for %s: %s" % (cmd, type(ret)))
        return ret
        
    def sync_dict(self, cmd, *args):
        self.sync_counter += 1
        key = self.sync_counter
        self.queue.put(MPDCommand(cmd, args, sync=(self.sync_dict,key)))
        assert self.dprint("Waiting for %s: key=%d" % (cmd, key))

        count = 0
        while key not in self.sync_dict:
            time.sleep(self.sync_sleep)
            count += 1
            if count >= self.sync_abort:
                self.sync_dict[key] = []
        ret = self.sync_dict[key]
        del self.sync_dict[key]
        return ret

    def callback(self, callback, cmd, *args):
        self.queue.put(MPDCommand(cmd, args, callback=callback))

    def isLoggedIn(self):
        return self.status['login']
        
    def isPlaying(self):
        """True if playing music; false if paused or stopped."""
        return self.status['login'] and self.status['state'] == 'play'

    def playPause(self):
        """User method to play or pause.

        Called to play music either from a stopped state or to resume
        from pause.
        """
        state = self.status['state']
        if state == 'play':
            self.cmd('pause',1)
        elif state == 'pause':
            # resume playing
            self.cmd('pause',0)
        else:
            self.cmd('play')

    def stopPlaying(self):
        """User method to stop playing."""
        state = self.status['state']
        if state != 'stop':
            self.cmd('stop')

    def prevSong(self):
        """User method to skip to previous song.

        Usable only when playing.
        """
        state = self.status['state']
        if state != 'stop':
            self.cmd('previous')

    def nextSong(self):
        """User method to skip to next song.

        Usable only when playing.
        """
        state = self.status['state']
        if state != 'stop':
            self.cmd('next')

    def volumeUp(self, step):
        """Increase volume, usable at any time.

        Volume ranges from 0 - 100 inclusive.

        @param step: step size to increase
        """
        vol = int(self.status['volume']) + step
        if vol > 100: vol = 100
        self.cmd('setvol', vol)
        self.save_mute = -1

    def volumeDown(self, step):
        """Decrease volume, usable at any time.

        Volume ranges from 0 - 100 inclusive.

        @param step: step size to increase
        """
        vol = int(self.status['volume']) - step
        if vol < 0: vol = 0
        self.cmd('setvol', vol)
        self.save_mute = -1

    def setMute(self):
        """Mute or unmute, usable at any time

        Mute volume or restore muted sound to previous volume level.
        """
        if self.save_mute < 0:
            self.save_mute = int(self.status['volume'])
            vol = 0
        else:
            vol = self.save_mute
            self.save_mute = -1
        self.cmd('setvol', vol)


class Login(SelectAction):
    alias = _("mpd-login")
    name = _("Login")
    tooltip = _("Login")
    icon = 'icons/control_start.png'
    key_bindings = {'default': 'L'}
    
    def isEnabled(self):
        mode = self.mode
        return mode.isConnected()

    def action(self, index=-1, multiplier=1):
        mode = self.mode
        wx.CallAfter(mode.loginPassword)

class OpenMPD(OpenDialog):
    alias = _("mpd-open-server")
    name = _("MPD Server...")
    tooltip = _("Open an MPD server through a URL")
    icon = "icons/folder_page.png"

    dialog_message = "Open MPD server.  Specify host[:port]"

    def processURL(self, url):
        if not url.startswith('mpd://'):
            url = 'mpd://' + url
        parts = url.split(':')
        if len(parts) == 2:
            url += ':6600'
        dprint("Attempting to open mpd url: %s" % url)
        self.frame.open(url)

class PlayingAction(SelectAction):
    """Base class for actions that are valid only while playing music.

    Anything that subclasses this action only makes sense while the
    server is playing (or paused).
    """
    def isEnabled(self):
        mode = self.mode
        return mode.mpd.isPlaying()

class ConnectedAction(SelectAction):
    """Base class for actions that only need a working mpd.

    Anything that subclasses this action can still function regardless
    of the play/pause state of the server.
    """
    def isEnabled(self):
        mode = self.mode
        return mode.isConnected() and mode.mpd.isLoggedIn()

class PrevSong(PlayingAction):
    alias = _("previous-song")
    name = _("Prev Song")
    tooltip = _("Previous Song")
    icon = 'icons/control_start.png'
    key_bindings = {'default': ','}
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("Previous song!!!")
        mode = self.mode
        mode.mpd.prevSong()
        mode.update()

class NextSong(PlayingAction):
    alias = _("next-song")
    name = _("Next Song")
    tooltip = _("Next Song")
    icon = 'icons/control_end.png'
    key_bindings = {'default': '.'}
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("Next song!!!")
        mode = self.mode
        mode.mpd.nextSong()
        mode.update()

class StopSong(PlayingAction):
    alias = _("stop")
    name = _("Stop")
    tooltip = _("Stop")
    icon = 'icons/control_stop.png'
    key_bindings = {'default': 'S'}
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("Stop playing!!!")
        mode = self.mode
        mode.mpd.stopPlaying()
        mode.update()

class PlayPause(ConnectedAction):
    alias = _("play-or-pause")
    name = _("Play/Pause Song")
    tooltip = _("Play/Pause Song")
    icon = 'icons/control_play.png'
    key_bindings = {'default': 'P'}
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("Play song!!!")
        mode = self.mode
        mode.mpd.playPause()
        mode.update()

class Mute(ConnectedAction):
    alias = _("mute")
    name = _("Mute")
    tooltip = _("Mute the volume")
    icon = 'icons/sound_mute.png'
    key_bindings = {'default': 'M'}
    
    def action(self, index=-1, multiplier=1):
        mode = self.mode
        mode.mpd.setMute()
        mode.update()

class VolumeUp(ConnectedAction):
    alias = _("volume-up")
    name = _("Increase Volume")
    tooltip = _("Increase the volume")
    icon = 'icons/sound.png'
    key_bindings = {'default': '='}
    
    def action(self, index=-1, multiplier=1):
        mode = self.mode
        mode.mpd.volumeUp(mode.classprefs.volume_step)
        mode.update()

class VolumeDown(ConnectedAction):
    alias = _("volume-down")
    name = _("Decrease Volume")
    tooltip = _("Decrease the volume")
    icon = 'icons/sound_low.png'
    key_bindings = {'default': '-'}
    
    def action(self, index=-1, multiplier=1):
        mode = self.mode
        mode.mpd.volumeDown(mode.classprefs.volume_step)
        mode.update()

class UpdateDatabase(ConnectedAction):
    alias = _("update-mpd-database")
    name = _("Update Database")
    tooltip = _("Rescan the filesystem and update the MPD database")
    icon = 'icons/sound_low.png'
    key_bindings = {'default': 'C-D'}
    
    def action(self, index=-1, multiplier=1):
        mode = self.mode
        status = mode.mpd.cmd('update')

class DeleteFromPlaylist(ConnectedAction):
    alias = _("delete-playlist-entry")
    name = _("Delete Playlist Entry")
    tooltip = _("Delete selected songs from playlist")
    icon = 'icons/sound_low.png'
    key_bindings = {'default': 'DEL'}
    
    def action(self, index=-1, multiplier=1):
        mode = self.mode
        Publisher().sendMessage('mpd.deleteFromPlaylist', mode.mpd)

class MPDSTC(NonResidentSTC):
    def CanSave(self):
        return False
    
    def open(self, url, progress_message=None):
        """Save the file handle, which is really the mpd connection"""
        fh = url.getDirectReader()
        self.mpd = fh


class SongDataObject(wx.CustomDataObject):
    def __init__(self):
        wx.CustomDataObject.__init__(self, "SongData")


class MPDMinorModeMixin(MinorMode):
    @classmethod
    def worksWithMajorMode(self, mode):
        if mode.__class__ == MPDMode:
            return True
        return False

class MPDSearchResults(MPDMinorModeMixin, wx.ListCtrl, ColumnSizerMixin,
                       debugmixin):
    """Minor mode to display the results of a file search.
    """
    keyword = "MPD Search Results"
    default_classprefs = (
        IntParam('best_width', 800),
        IntParam('best_height', 400),
        IntParam('min_width', 300),
        IntParam('min_height', 200),
        )

    def __init__(self, major, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)
        self.major = major
        self.mpd = major.mpd
        self.createColumns()

        self.songindex = -1
        default_font = self.GetFont()
        self.font = wx.Font(major.classprefs.list_font_size, 
                            default_font.GetFamily(),
                            default_font.GetStyle(),
                            default_font.GetWeight())
        self.SetFont(self.font)

        self.artists = []
        self.albums = []

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)

        Publisher().subscribe(self.searchResultsTracks,
                              'mpd.searchResultsTracks')
        Publisher().subscribe(self.searchResultsArtistsAlbums,
                              'mpd.searchResultsArtistsAlbums')

        self.reset(self.mpd)

    def deletePreHook(self):
        Publisher().unsubscribe(self.searchResultsTracks)
        Publisher().unsubscribe(self.searchResultsArtistsAlbums)
        
    def paneInfoHook(self, paneinfo):
        paneinfo.Bottom()

    def createColumns(self):
        self.InsertColumn(0, "Title")
        self.InsertColumn(1, "Time")
        self.InsertColumn(2, "Rating")
        self.InsertColumn(3, "Artist")
        self.InsertColumn(4, "Album")
        self.InsertColumn(5, "Track")
        self.InsertColumn(6, "Genre")
        self.InsertColumn(7, "Filename")

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        filename = self.GetItem(index, 7).GetText()
        assert self.dprint("song %d: %s" % (index, filename))
        self.mpd.cmd('add', filename)
        self.mpd.cmd('status')
        evt.Skip()

    def getSelectedSongs(self):
        songlist = []
        index = self.GetFirstSelected()
        while index != -1:
            filename = self.GetItem(index, 7).GetText()
            assert self.dprint("song %d: %s" % (index, filename))
            songlist.append(filename)
            index = self.GetNextSelected(index)
        return songlist
    
    def OnStartDrag(self, evt):
        index = evt.GetIndex()
        self.dprint("beginning drag of item %d" % index)
        data = SongDataObject()
        songlist = self.getSelectedSongs()
        data.SetData(pickle.dumps(songlist,-1))

        # And finally, create the drop source and begin the drag
        # and drop opperation
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        assert self.dprint("Begining DragDrop\n")
        result = dropSource.DoDragDrop(wx.Drag_AllowMove)
        assert self.dprint("DragDrop completed: %d\n" % result)

    def reset(self, mpd=None):
        if mpd is not None:
            self.mpd = mpd

        all_tracks = []
        for album in self.albums:
            tracks = self.mpd.sync("search", "album", album)
            all_tracks.extend(tracks)
        self.populateTracks(all_tracks)

    def populateTracks(self, tracks):
        index = 0
        list_count = self.GetItemCount()
        for track in tracks:
            if index >= list_count:
                self.InsertStringItem(sys.maxint, getTitle(track))
            else:
                self.SetStringItem(index, 0, getTitle(track))
            self.SetStringItem(index, 1, getTime(track))
            self.SetStringItem(index, 7, track['file'])

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)

        if index > 0:
            self.showIfHidden()
            self.resizeColumns([0,1,-40,-40,-40,-40,-40,0])

    def searchResultsTracks(self, message=None):
        mpd, tracks = message.data
        
        if mpd == self.mpd:
            self.populateTracks(tracks)

    def populate(self, artists, albums):
        self.artists = [i for i in artists]
        self.albums = [i for i in albums]
        self.reset()

    def searchResultsArtistsAlbums(self, message=None):
        mpd, artists, albums = message.data
        
        if mpd == self.mpd:
            self.populate(artists, albums)

    def showIfHidden(self):
        if not self.paneinfo.IsShown():
            self.paneinfo.Show(True)
            self.major._mgr.Update()

    def update(self):
        self.reset()



class MPDListByGenre(NeXTPanel, debugmixin):
    """Control to search through the MPD database to add songs to the
    playlist.

    Displays genre, artist, album, and songs.
    """
    debuglevel = 0

    def __init__(self, parent_win, parent):
        NeXTPanel.__init__(self, parent_win)
        self.parent = parent

        self.Bind(EVT_NEXTPANEL,self.OnPanelUpdate)

        self.lists = ['genre', 'artist', 'album']
        self.shown = 1

        self.Layout()

    def reset(self):
        self.shown = 0
        items = self.getLevelItems(-1, None)
        self.showItems(self.shown, self.lists[self.shown], items)

    def showItems(self, index, keyword, items):
        list = self.GetList(index)
        if list is None:
            assert self.dprint("list at position %d not found!  Creating new list" % index)
            list = self.AppendList(self.parent.major.classprefs.list_width, keyword)
        names = {}
        for item in items:
            #assert self.dprint(item)
            names[str(item[keyword]).decode('utf-8')] = 1
        names = names.keys()
        names.sort()

        #assert self.dprint("before InsertStringItem")
        list.ReplaceItems(names)
        #assert self.dprint("after InsertStringItem")

    def getLevelItems(self, level, item):
        if level < 0:
            return self.parent.mpd.sync("list", "genre")
        if level < len(self.lists) - 1:
            return self.parent.mpd.sync("list", self.lists[level+1], self.lists[level], item)
        return None

    def rebuildLevels(self, level, list, selections):
        assert self.dprint("level=%d selections=%s" % (level, selections))
        self.shown = level + 1
        if self.shown < len(self.lists):
            assert self.dprint("shown=%d" % self.shown)
            self.DeleteAfter(self.shown)

            newitems = []
            for i in selections:
                item = list.GetString(i)
                newitems.extend(self.getLevelItems(level, item))
            self.showItems(self.shown, self.lists[self.shown], newitems)
            self.ensureVisible(self.shown)
        else:
            artists = []
            albums = [list.GetString(i) for i in selections]
            Publisher().sendMessage('mpd.searchResultsArtistsAlbums', (self.parent.mpd, artists, albums))

    def OnPanelUpdate(self, evt):
        assert self.dprint("select on list %d, selections=%s" % (evt.listnum, str(evt.selections)))
        wx.CallAfter(self.rebuildLevels, evt.listnum, evt.list, evt.selections)


class MPDListByPath(NeXTFileManager, debugmixin):
    def __init__(self, parent_win, parent):
        NeXTFileManager.__init__(self, parent_win)
        self.parent = parent
        self.files = {}
        
    def getLevelItems(self, level, item):
        if level<0:
            path = ''
        else:
            path = '/'.join(self.dirtree[0:level+1])
        #assert self.dprint(self.dirtree)
        #assert self.dprint(path)
        items = self.parent.mpd.sync('lsinfo', path)
        names = []
        tracks = []
        for item in items:
            #assert self.dprint(item)
            if item['type'] == 'directory':
                names.append(os.path.basename(item['directory']))
            elif item['type'] == 'file':
                tracks.append(item)

        Publisher().sendMessage('mpd.searchResultsTracks',
                                (self.parent.mpd, tracks))
        return names


class MPDListSearch(wx.Panel, debugmixin):
    """Search the database by keyword
    """
    debuglevel = 0

    def __init__(self, parent_win, parent):
        wx.Panel.__init__(self, parent_win)
        self.parent = parent
        
        self.sizer = wx.GridBagSizer(5,5)
        
        title = wx.StaticText(self, -1, "Search terms:")
        self.sizer.Add(title, (1,0))

        self.searches = []
        self.search = wx.SearchCtrl(self, size=(200,-1), style=wx.TE_PROCESS_ENTER)
        self.search.ShowSearchButton(True)
        self.search.ShowCancelButton(True)
        self.search.SetMenu(self.MakeMenu())
        
        self.sizer.Add(self.search, (1,1))

        options = wx.StaticText(self, -1, "Search by:")
        self.sizer.Add(options, (2,0), flag = wx.ALIGN_CENTER)

        keywords = ['any', 'album', 'artist', 'title', 'filename']
        self.category = wx.RadioBox(self, -1, "", choices=keywords)
        self.sizer.Add(self.category, (2,1))

        self.SetSizer(self.sizer)


        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnSearch, self.search)
        self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnCancel, self.search)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.search)
        ##self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)        

    def OnSearch(self, evt):
        assert self.dprint("OnSearch")
            
    def OnCancel(self, evt):
        assert self.dprint("OnCancel")

    def OnDoSearch(self, evt):
        keyword = self.search.GetValue()
        self.searches.append(keyword)
        self.search.SetMenu(self.MakeMenu())
        assert self.dprint("OnDoSearch: " + self.search.GetValue())
        category = self.category.GetStringSelection()
        items = self.parent.mpd.sync('search', category, keyword, timeout=2.0)
        names = []
        tracks = []
        for item in items:
            #assert self.dprint(item)
            if item['type'] == 'file':
                tracks.append(item)

        Publisher().sendMessage('mpd.searchResultsTracks',
                                (self.parent.mpd, tracks))

    def MakeMenu(self):
        menu = wx.Menu()
        item = menu.Append(-1, "Recent Searches")
        item.Enable(False)
        for txt in self.searches:
            menu.Append(-1, txt)
        return menu

    def reset(self):
        # reset is called by MPDDatabase when the tab is changed, but
        # we don't need to do anyting here.
        pass


class MPDDatabase(wx.Panel, debugmixin):
    """Control to search through the MPD database by pathname.

    Displays pathnames and puts files into the file list.
    """
    debuglevel = 0

    def __init__(self, major, parent):
        wx.Panel.__init__(self, parent)
        self.major = major
        self.mpd = major.mpd

        self.default_font = self.GetFont()
        self.font = wx.Font(major.classprefs.list_font_size, 
                            self.default_font.GetFamily(),
                            self.default_font.GetStyle(),
                            self.default_font.GetWeight())
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.notebook = wx.Notebook(self)
        self.sizer.Add(self.notebook, 1, wx.EXPAND)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        self.pathname = MPDListByPath(self.notebook, self)
        self.pathname.SetFont(self.font)
        self.notebook.AddPage(self.pathname, "Pathname Browser")

        self.genre = MPDListByGenre(self.notebook, self)
        self.genre.SetFont(self.font)
        self.notebook.AddPage(self.genre, "Genre Browser")

        self.search = MPDListSearch(self.notebook, self)
        self.search.SetFont(self.font)
        self.notebook.AddPage(self.search, "Search")

        self.shown = 0
        self.dirtree = []
        
        self.Layout()

    def OnTabChanged(self, evt):
        val = evt.GetSelection()
        page = self.notebook.GetPage(val)
        page.reset()
        evt.Skip()

    def reset(self):
        page = self.notebook.GetCurrentPage()
        page.reset()



class MPDMode(MajorMode, debugmixin):
    """Major mode for controlling a Music Player Daemon.

    ...
    """
    debug_level = 0
    keyword='MPD'
    icon='icons/mpd.ico'

    stc_class = MPDSTC

    default_classprefs = (
        StrParam('minor_modes', 'MPD Playlist, MPD Currently Playing, MPD Search Results'),
        IntParam('update_interval', 1),
        IntParam('volume_step', 10),
        IntParam('list_font_size', 8),
        IntParam('list_width', 100),
        StrParam('password', None),
        )
    
    @classmethod
    def verifyProtocol(cls, url):
        if url.protocol == 'mpd':
            return True
        return False
    
    def createEditWindow(self,parent):
        """Create the main MPD music search window.

        @param parent: parent window in which to create this window 
        """
        self.stc = self.buffer.stc
        self.mpd = self.stc.mpd
        win = MPDDatabase(self, parent)
        return win

    def createPostHook(self):
        Publisher().subscribe(self.showMessages, 'mpd')
        eventManager.Bind(self.OnLogin, EVT_MPD_LOGGED_IN, win=wx.GetApp())
        self.login_shown = False

        self.OnTimer()        
        self.editwin.Bind(wx.EVT_TIMER, self.OnTimer)
        self.update_timer = wx.Timer(self.editwin)
        self.update_timer.Start(self.classprefs.update_interval*1000)

    def loadMinorModesPostHook(self):
        # Don't initialize the MPD connection till all the minor modes
        # are created, because their own initialization depends on
        # message passing from the mpd wrapper
        if isinstance(self.classprefs.password, str):
            self.mpd.cmd('password', self.classprefs.password)
        
        self.mpd.reset()
        assert self.dprint(self.mpd.status)

    def deleteWindowPostHook(self):
        Publisher().unsubscribe(self.showMessages)
        eventManager.DeregisterListener(self.OnLogin)

    def showMessages(self, message=None):
        """debug method to show all pubsub messages."""
        assert self.dprint(str(message.topic))

    def OnTimer(self, evt=None):
        self.update()
        if 'login' in self.mpd.status and not self.mpd.status['login']:
            if not self.login_shown:
                self.login_shown = True
                wx.CallAfter(self.loginPassword)

    def update(self):
        self.mpd.cmd('status')
        self.idle_update_menu = True

    def isConnected(self):
        return self.mpd is not None

    def loginPassword(self):
        dlg = wx.TextEntryDialog(self.editwin,
                                 'Enter MPD password for %s' % self.buffer.url.url,
                                 style=wx.OK | wx.CANCEL | wx.TE_PASSWORD)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.dprint("password: %s" % dlg.GetValue())
            self.mpd.cmd('password', dlg.GetValue())

        dlg.Destroy()

    def OnLogin(self, evt=None):
        self.editwin.reset()
        evt.Skip()



class SongDropTarget(wx.PyDropTarget, debugmixin):
    """Custom drop target modified from the wxPython demo."""
    debuglevel = 0
    
    def __init__(self, window):
        wx.PyDropTarget.__init__(self)
        self.dv = window
        self.width, self.height = window.GetClientSizeTuple()

        # specify the type of data we will accept
        self.data = SongDataObject()
        self.SetDataObject(self.data)

    # some virtual methods that track the progress of the drag
    def OnEnter(self, x, y, d):
        assert self.dprint("OnEnter: %d, %d, %d\n" % (x, y, d))
        return d

    def OnLeave(self):
        assert self.dprint("OnLeave\n")
        self.dv.finishListScroll()

    def OnDrop(self, x, y):
        assert self.dprint("OnDrop: %d %d\n" % (x, y))
        self.dv.finishListScroll()
        return True

    def OnDragOver(self, x, y, d):
        top = self.dv.GetTopItem()
        assert self.dprint("OnDragOver: %d, %d, %d, top=%s" % (x, y, d, top))

        self.dv.processListScroll(x, y)

        # The value returned here tells the source what kind of visual
        # feedback to give.  For example, if wxDragCopy is returned then
        # only the copy cursor will be shown, even if the source allows
        # moves.  You can use the passed in (x,y) to determine what kind
        # of feedback to give.  In this case we return the suggested value
        # which is based on whether the Ctrl key is pressed.
        return d

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        assert self.dprint("OnData: %d, %d, %d\n" % (x, y, d))

        self.dv.finishListScroll()
        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list of lines and give it to the viewer
            songs = pickle.loads(self.data.GetData())
            self.dv.AddSongs(x, y, songs)
            
        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d

class MPDPlaylist(MPDMinorModeMixin, wx.ListCtrl, ColumnSizerMixin,
                  ListDropScrollerMixin, debugmixin):
    """Minor mode to display the current playlist and controls for
    music playing.
    """
    keyword = "MPD Playlist"
    default_classprefs = (
        IntParam('best_width', 400),
        IntParam('best_height', 400),
        IntParam('min_width', 300),
        IntParam('min_height', 100),
        )

    def __init__(self, major, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)
        ListDropScrollerMixin.__init__(self)

        self.major = major
        self.mpd = major.mpd
        self.createColumns()

        default_font = self.GetFont()
        self.font = wx.Font(major.classprefs.list_font_size, 
                            default_font.GetFamily(),
                            default_font.GetStyle(),
                            default_font.GetWeight())
        self.SetFont(self.font)
        self.bold_font = wx.Font(major.classprefs.list_font_size, 
                                 default_font.GetFamily(),
                                 default_font.GetStyle(),wx.BOLD)

        self.dropTarget=SongDropTarget(self)
        self.SetDropTarget(self.dropTarget)

        self.songindex = -1
        self.pending_highlight = -1

        # keep track of playlist index to playlist song id
        self.playlist_cache = []
        
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)

        Publisher().subscribe(self.delete, 'mpd.deleteFromPlaylist')

        eventManager.Bind(self.OnSongChanged, EVT_MPD_SONG_CHANGED, win=wx.GetApp())
        eventManager.Bind(self.OnPlaylistChanged, EVT_MPD_PLAYLIST_CHANGED, win=wx.GetApp())

    def deletePreHook(self):
        Publisher().unsubscribe(self.delete)
        
        eventManager.DeregisterListener(self.OnSongChanged)
        eventManager.DeregisterListener(self.OnPlaylistChanged)

    def createColumns(self):
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Title")
        self.InsertColumn(2, "Artist")
        self.InsertColumn(3, "Time", wx.LIST_FORMAT_RIGHT)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        self.mpd.cmd('play',index)
        evt.Skip()

    def getSelectedSongs(self):
        songlist = []
        index = self.GetFirstSelected()
        while index != -1:
            assert self.dprint("song %d" % (index, ))
            songlist.append(index)
            index = self.GetNextSelected(index)
        return songlist
    
    def delete(self, message=None):
        assert self.dprint(message)

        # Make sure the message relates to our mpd instance
        if message.data == self.mpd:
            songlist = self.getSelectedSongs()
            if songlist:
                sids = [self.playlist_cache[i] for i in songlist]
                for sid in sids:
                    self.mpd.cmd('deleteid', sid)
                self.mpd.cmd('status')
                self.reset()
                self.setSelected([])

    def OnSongChanged(self, evt):
        assert self.dprint("EVENT!!!")
        status = evt.status
        if status['state'] == 'stop':
            self.highlightSong(-1)
        else:
            self.highlightSong(int(status['song']))
        evt.Skip()

    def OnStartDrag(self, evt):
        index = evt.GetIndex()
        self.dprint("beginning drag of item %d" % index)
        
        data = SongDataObject()
        songlist = self.getSelectedSongs()
        data.SetData(pickle.dumps(songlist,-1))

        # And finally, create the drop source and begin the drag
        # and drop opperation
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        assert self.dprint("Begining DragDrop\n")
        result = dropSource.DoDragDrop(wx.Drag_AllowMove)
        assert self.dprint("DragDrop completed: %d\n" % result)

    def AddSongs(self, x, y, songs):
        index = self.getDropIndex(x, y)
        assert self.dprint("At (%d,%d), index=%d, adding %s" % (x, y, index, songs))
        # Looks like the MPD protocol is a bit limited in that you
        # can't add a song at a particular spot; only at the end.  So,
        # we'll have to add them all and then move them (potential
        # race condition if there's another mpd client adding songs at
        # the some time.
        list_count = self.GetItemCount()
        highlight = []
        for song in songs:
            if type(song) == int:
                sid = self.playlist_cache[song]
                assert self.dprint("Moving id=%d (index=%d) to %d" % (sid, song, index))
                self.mpd.sync('moveid', sid, index)
                if song >= index:
                    index += 1
                highlight.append(sid)
            else:
                ret = self.mpd.sync('addid', song)
                sid = int(ret['id'])
                self.mpd.cmd('moveid', sid, index)
                index += 1
                highlight.append(sid)
        self.setSelected(highlight)

    def setSelected(self, ids):
        list_count = self.GetItemCount()
        cache = self.playlist_cache
        for index in range(list_count):
            if cache[index] in ids:
                self.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            else:
                self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

    def playlistChanged(self, msg=None):
        assert self.dprint("message received: msg=%s" % str(msg.topic))
        mpd, status = msg.data
        self.reset(visible=self.songindex)
        self.songChanged(msg)
    
    def OnPlaylistChanged(self, evt):
        status = evt.status
        self.reset(visible=self.songindex)
        self.OnSongChanged(evt)
    
    def reset(self, mpd=None, visible=None):
        if mpd is not None:
            self.mpd = mpd
        playlist = self.mpd.playlistinfo
        list_count = self.GetItemCount()
        index = 0
        cumulative = 0
        cache = []
        show = -1
        for track in playlist:
            if index >= list_count:
                self.InsertStringItem(sys.maxint, str(index+1))
            self.SetStringItem(index, 1, getTitle(track))
            self.SetStringItem(index, 2, getArtist(track))
            self.SetStringItem(index, 3, getTime(track))
            cumulative += int(track['time'])
            if track['file'] == visible:
                show = index
            cache.append(int(track['id']))

            index += 1
        self.playlist_cache = cache
        
        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)
        if show >= 0:
            self.EnsureVisible(show)

        if self.pending_highlight >= 0:
            self.highlightSong(self.pending_highlight)
            self.pending_highlight = -1
        self.resizeColumns([1,0,0,1])

        self.paneinfo.Caption("Playlist: %d songs -- %s" % (index, getTimeString(cumulative)))
        self.major._mgr.Update()

    def appendSong(self, message=None):
        assert self.dprint(message)

        # Make sure the message relates to our mpd instance
        if message.data[0] == self.mpd:
            self.mpd.add(message.data[1])
            self.reset(visible = message.data[1])

    def highlightSong(self, newindex):
        if newindex == self.songindex:
            return

        try:
            # Check to see if indicies are within bounds, because it
            # is possible to get an event here before the songlist is
            # populated.
            if self.songindex >= 0 and self.songindex < self.GetItemCount():
                item = self.GetItem(self.songindex)
                item.SetFont(self.font)
                self.SetItem(item)
            self.songindex = newindex
            if newindex >= 0 and newindex < self.GetItemCount():
                item = self.GetItem(self.songindex)
                item.SetFont(self.bold_font)
                self.SetItem(item)            
                self.EnsureVisible(newindex)
            else:
                # If the new index is out of range, we must have
                # received events out of order, so flag this index for
                # the next time we get a playlistChanged event
                self.pending_highlight = newindex
                self.songindex = -1
                self.dprint("pending_highlight = %d" % self.pending_highlight)
            self.resizeColumns()
        except:
            # Failure probably means that the playlist has changed out
            # from under us by another mpd client.  Just skip it and
            # let the playlist get updated by the next playlist
            # changed message
            pass
            
    def songChanged(self, msg):
        assert self.dprint(str(msg.topic))
        mpd, status = msg.data
        if status['state'] == 'stop':
            self.highlightSong(-1)
        else:
            self.highlightSong(int(status['song']))



class MPDCurrentlyPlaying(MPDMinorModeMixin, wx.Panel, debugmixin):
    """Minor mode to display the current title, artist, and album,
    with controls for position in the song and play/pause controls.
    """
    debuglevel = 0

    keyword = "MPD Currently Playing"
    default_classprefs = (
        IntParam('best_width', 400),
        IntParam('best_height', 100),
        IntParam('min_width', 300),
        IntParam('min_height', 50),
        )

    def __init__(self, major, parent):
        wx.Panel.__init__(self, parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.slider = wx.Slider(self)
        self.sizer.Add(self.slider, flag=wx.EXPAND)

        self.Layout()

        self.major = major
        self.mpd = major.mpd
        self.songid = -1
        self.user_scrolling = False

        self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderMove)
        self.slider.Bind(wx.EVT_SCROLL_CHANGED, self.OnSliderRelease)

        eventManager.Bind(self.OnSongChanged, EVT_MPD_SONG_CHANGED, win=wx.GetApp())
        eventManager.Bind(self.OnSongTime, EVT_MPD_SONG_TIME, win=wx.GetApp())

    def deletePreHook(self):
        eventManager.DeregisterListener(self.OnSongChanged)
        eventManager.DeregisterListener(self.OnSongTime)

    def OnSongChanged(self, evt):
        assert self.dprint("EVENT!!!")
        self.reset()
        evt.Skip()
        
    def OnSongTime(self, evt):
        assert self.dprint("EVENT!!!")
        self.update(evt.status)
        evt.Skip()

    def OnSliderMove(self, evt):
        self.user_scrolling = True
        evt.Skip()
        
    def OnSliderRelease(self, evt):
        self.user_scrolling = False
        assert self.dprint(evt.GetPosition())
        self.mpd.cmd('seekid', self.songid, evt.GetPosition())

    def songChanged(self, msg=None):
        assert self.dprint("songChanged: msg=%s" % str(msg.topic))
        self.reset()

    def reset(self, mpd=None):
        if mpd is not None:
            self.mpd = mpd
        track = self.mpd.currentsong
        if track and self.mpd.status['state'] != 'stop':
            assert self.dprint("currentsong: \n%s" % track)
            assert self.dprint("status: \n%s" % self.mpd.status)
            if 'title' not in track:
                title = track['file']
            else:
                title = track['title']
                if 'artist' in track:
                    title += " -- %s" % track['artist']
            self.paneinfo.Caption(title)
            self.slider.SetRange(0, int(track['time']))
            self.songid = int(track['id'])
        else:
            self.paneinfo.Caption(self.keyword)
            self.slider.SetRange(0,1)
            self.slider.SetValue(0)
            self.songid = -1
        self.major._mgr.Update() # force AUI to update the pane caption
        self.user_scrolling = False

    def songTime(self, msg=None):
        assert self.dprint("msg=%s" % str(msg.topic))
        mpd, status = msg.data
        self.update(status)

    def update(self, status):
        if status['state'] == 'stop':
            self.slider.SetValue(0)
        elif not self.user_scrolling:
            assert self.dprint(status)
            pos, tot = status['time'].split(":")
            self.slider.SetValue(int(pos))

    def OnSize(self, evt):
        self.Refresh()
        evt.Skip()





class MPDHandler(urllib2.BaseHandler, debugmixin):
    def mpd_open(self, req):
        assert self.dprint(req)
        url = req.get_host()
        parts = url.split(":")
        host = parts[0]
        if len(parts) > 1:
            port = int(parts[1])
        else:
            port = 6600
        assert self.dprint(parts)

        fh = MPDComm(host, port)
        fh.geturl = lambda :"mpd:%s" % url
        fh.info = lambda :{'Content-type': 'text/plain',
                           'Content-length': 0,
                           'Last-modified': 'Sat, 17 Feb 2007 20:29:30 GMT',
                            }
        
        return fh


class MPDPlugin(IPeppyPlugin):
    """HSI viewer plugin to register modes and user interface.
    """
    def getURLHandlers(self):
        return [MPDHandler]

    def getMajorModes(self):
        yield MPDMode
    
    def getMinorModes(self):
        for mode in [MPDPlaylist, MPDCurrentlyPlaying, MPDSearchResults]:
            yield mode
    
    default_menu=((None,(_("File"),_("Open")),MenuItem(OpenMPD).first()),
                  ("MPD",None,Menu(_("MPD")).after("Major Mode")),
                  ("MPD",_("MPD"),MenuItem(StopSong)),
                  ("MPD",_("MPD"),MenuItem(PlayPause)),
                  ("MPD",_("MPD"),MenuItem(PrevSong)),
                  ("MPD",_("MPD"),MenuItem(NextSong)),
                  ("MPD",_("MPD"),Separator("volume")),
                  ("MPD",_("MPD"),MenuItem(VolumeUp)),
                  ("MPD",_("MPD"),MenuItem(VolumeDown)),
                  ("MPD",_("MPD"),MenuItem(Mute)),
                  ("MPD",_("MPD"),Separator("playlist")),
                  ("MPD",_("MPD"),MenuItem(DeleteFromPlaylist)),
                  ("MPD",_("MPD"),Separator("database")),
                  ("MPD",_("MPD"),MenuItem(Login)),
                  ("MPD",_("MPD"),MenuItem(UpdateDatabase)),
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

