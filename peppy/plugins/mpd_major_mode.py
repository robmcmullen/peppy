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
import cPickle as pickle

import wx
import wx.lib.stattext
from wx.lib.pubsub import Publisher

from peppy import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *
from peppy.stcinterface import NonResidentSTC

from peppy.about import SetAbout
from peppy.lib.iconstorage import *

from peppy.lib.nextpanel import *
from peppy.lib.mpdclient2 import mpd_connection


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

def getTime(track):
    """Convenience function to return album of a track"""
    seconds = int(track['time'])
    if seconds < 60:
        minutes = 0
    else:
        minutes = seconds / 60
        seconds = seconds % 60
    return "%d:%02d" % (minutes, seconds)


class MPDWrapper(mpd_connection):
    """Wrapper around mpd_connection to save state information.

    Small wrapper around mpdclient2's mpd_connection object to save
    state information about the mpd instance.  All views into the mpd
    instance and all minor modes that access the mpd object will then
    share the same information, rather than having to look somewhere
    else to find it.
    """
    def __init__(self, host, port, timeout=0.5):
        mpd_connection.__init__(self, host, port, timeout)

        self.save_mute = -1
        self.last_status = {'state': 'stop'}
        self.last_playlist = -1
        self.last_songid = -1
        self.check_messages = {'playlist': 'mpd.playlist.changed',
                               'songid': 'mpd.song.changed',
                               'time': 'mpd.song.time',
                               }
        
    def isPlaying(self):
        """True if playing music; false if paused or stopped."""
        return self.last_status['state'] == 'play'

    def cmd(self, cmd, *args):
        try:
            result = self.do.send_n_fetch(cmd, args)
            return result
        except Exception, e:
            print "Exception: %s" % str(e)
        return None

    def getStatus(self, reset=False):
        status = self.cmd('status')
        if status is None:
            Publisher().sendMessage("mpd.ioerror", (self,))
        else:
            #print status
            for k, msg in self.check_messages.iteritems():
                if k in status:
                    if k not in self.last_status or status[k] != self.last_status[k]:
                        dprint("sending msg=%s" % msg)
                        Publisher().sendMessage(msg, (self, status))
            self.last_status = status

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
    """Base class for actions that are valid only while playing music.

    Anything that subclasses this action only makes sense while the
    server is playing (or paused).
    """
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.mpd.isPlaying()

class ConnectedAction(SelectAction):
    """Base class for actions that only need a working mpd.

    Anything that subclasses this action can still function regardless
    of the play/pause state of the server.
    """
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        return mode.isConnected()

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

class PlayPause(ConnectedAction):
    name = _("Play/Pause Song")
    tooltip = _("Play/Pause Song")
    icon = 'icons/control_play.png'
    keyboard = "SPC"
    
    def action(self, pos=None):
        print "Play song!!!"
        mode = self.frame.getActiveMajorMode()
        mode.mpd.playPause()
        mode.update()

class Mute(ConnectedAction):
    name = _("Mute")
    tooltip = _("Mute the volume")
    icon = 'icons/sound_mute.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.setMute()
        mode.update()

class VolumeUp(ConnectedAction):
    name = _("Increase Volume")
    tooltip = _("Increase the volume")
    icon = 'icons/sound.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.volumeUp(mode.settings.volume_step)
        mode.update()

class VolumeDown(ConnectedAction):
    name = _("Decrease Volume")
    tooltip = _("Decrease the volume")
    icon = 'icons/sound_low.png'
    keyboard = "\\"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.volumeDown(mode.settings.volume_step)
        mode.update()

class UpdateDatabase(ConnectedAction):
    name = _("Update Database")
    tooltip = _("Rescan the filesystem and update the MPD database")
    icon = 'icons/sound_low.png'
    keyboard = "C-U"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        mode.mpd.update()
        mode.reset()

class DeleteFromPlaylist(ConnectedAction):
    name = _("Delete Playlist Entry")
    tooltip = _("Delete selected songs from playlist")
    icon = 'icons/sound_low.png'
    keyboard = "BACK"
    
    def action(self, pos=None):
        mode = self.frame.getActiveMajorMode()
        Publisher().sendMessage('mpd.deleteFromPlaylist', mode.mpd)

class MPDSTC(NonResidentSTC):
    def open(self, url):
        """Save the file handle, which is really the mpd connection"""
        fh = url.getDirectReader()
        self.mpd = fh


class SongDataObject(wx.CustomDataObject):
    def __init__(self):
        wx.CustomDataObject.__init__(self, "SongData")


class ColumnSizerMixin(object):
    """Enhancement to ListCtrl to handle column resizing.

    Resizes columns to a fixed size or based on the size of the
    contents, but constrains the whole width to the visible area of
    the list.  Theoretically there won't be any horizontal scrollbars,
    but this doesnt' yet work on GTK, at least.
    """
    def __init__(self, *args, **kw):
        self.resize_flags = None
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnSize(self, evt):
        wx.CallAfter(self.resizeColumns)
        evt.Skip()
        
    def resizeColumns(self, flags=[]):
        """Resize each column according to the flag.

        For each column, the respective flag indicates the following:

        0: smallest width that fits the entire string
        1: smallest width, and keep this column fixed width if possible
        >1: maximum size
        <0: absolute value is the minimum size
        """
        self.Freeze()
        if self.resize_flags is None or len(flags) > 0:
            # have to make copy of list, otherwise are operating on
            # the list that's passed in
            copy = list(flags)
            if len(copy) < self.GetColumnCount():
                copy.extend([0] * (self.GetColumnCount() - len(copy)))
            self.resize_flags = tuple(copy)
            #dprint("resetting flags to %s" % str(self.resize_flags))
            
        flags = self.resize_flags
        fixed_width = 0
        total_width = 0
        num_fixed = 0
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, wx.LIST_AUTOSIZE)
            flag = flags[col]
            if flag > 1:
                after = self.GetColumnWidth(col)
                if after > flag:
                    self.SetColumnWidth(col, flag)
            elif flag < 0:
                after = self.GetColumnWidth(col)
                if after < -flag:
                    self.SetColumnWidth(col, -flag)

            after = self.GetColumnWidth(col)
            total_width += after
            if flag == 1:
                num_fixed += 1
                fixed_width += after
        
        # FIXME: column 3 seems to get cut off by a few pixels when
        # using a bold font.  It seems like the SetColumnWidth
        # algorithm doesn't see the difference in the bold font.
        w, h = self.GetClientSizeTuple()
        dprint("client width = %d, fixed_width = %d" % (w, fixed_width))
        w -= fixed_width
        for col in range(self.GetColumnCount()):
            before = self.GetColumnWidth(col)
            #dprint("col %d: flag=%d before=%d" % (col, flags[col], before))
            if flags[col] != 1:
                self.SetColumnWidth(col, before*w/total_width)
        self.Thaw()

class FileCtrl(wx.ListCtrl, ColumnSizerMixin):
    def __init__(self, mode, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)
        self.mode = mode
        self.mpd = mode.mpd
        self.createColumns()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)

        self.songindex = -1

        self.artists = []
        self.albums = []

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
        dprint("song %d: %s" % (index, filename))
        Publisher().sendMessage('mpd.appendSong', (self.mpd, filename))
        evt.Skip()

    def getSelectedSongs(self):
        songlist = []
        index = self.GetFirstSelected()
        while index != -1:
            filename = self.GetItem(index, 7).GetText()
            dprint("song %d: %s" % (index, filename))
            songlist.append(filename)
            index = self.GetNextSelected(index)
        return songlist
    
    def OnStartDrag(self, evt):
        index = evt.GetIndex()
        print "beginning drag of item %d" % index
        data = SongDataObject()
        songlist = self.getSelectedSongs()
        data.SetData(pickle.dumps(songlist,-1))

        # And finally, create the drop source and begin the drag
        # and drop opperation
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        dprint("Begining DragDrop\n")
        result = dropSource.DoDragDrop(wx.Drag_AllowMove)
        dprint("DragDrop completed: %d\n" % result)

    def reset(self, mpd=None):
        if mpd is not None:
            self.mpd = mpd

        all_tracks = []
        for album in self.albums:
            tracks = self.mpd.search("album", album)
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
        self.resizeColumns([0,1,-40,-40,-40,-40,-40,0])

    def populate(self, artists, albums):
        self.artists = [i for i in artists]
        self.albums = [i for i in albums]
        self.reset()

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
            dprint("list at position %d not found!  Creating new list" % index)
            list = self.AppendList(self.parent.mode.settings.list_width, keyword)
        names = {}
        for item in items:
            #dprint(item)
            names[str(item[keyword]).decode('utf-8')] = 1
        names = names.keys()
        names.sort()

        #dprint("before InsertStringItem")
        list.ReplaceItems(names)
        #dprint("after InsertStringItem")

    def getLevelItems(self, level, item):
        if level < 0:
            return self.parent.mpd.list("genre")
        if level < len(self.lists) - 1:
            return self.parent.mpd.list(self.lists[level+1], self.lists[level], item)
        return None

    def rebuildLevels(self, level, list, selections):
        dprint("level=%d selections=%s" % (level, selections))
        self.shown = level + 1
        if self.shown < len(self.lists):
            dprint("shown=%d" % self.shown)
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
            self.parent.songlist.populate(artists, albums)        

    def OnPanelUpdate(self, evt):
        dprint("select on list %d, selections=%s" % (evt.listnum, str(evt.selections)))
        wx.CallAfter(self.rebuildLevels, evt.listnum, evt.list, evt.selections)


class MPDListByPath(NeXTFileManager):
    def __init__(self, parent_win, parent):
        NeXTFileManager.__init__(self, parent_win)
        self.parent = parent
        self.files = {}
        
    def getLevelItems(self, level, item):
        if level<0:
            path = ''
        else:
            path = '/'.join(self.dirtree[0:level+1])
        #dprint(self.dirtree)
        #dprint(path)
        names = []
        tracks = []
        items = self.parent.mpd.lsinfo(path)
        for item in items:
            #dprint(item)
            if item['type'] == 'directory':
                names.append(os.path.basename(item['directory']))
            elif item['type'] == 'file':
                tracks.append(item)

        self.parent.songlist.populateTracks(tracks)
        return names


class MPDDatabase(wx.Panel, debugmixin):
    """Control to search through the MPD database by pathname.

    Displays pathnames and puts files into the file list.
    """
    debuglevel = 0

    def __init__(self, mode, parent):
        wx.Panel.__init__(self, parent)
        self.mode = mode
        self.mpd = mode.mpd

        self.default_font = self.GetFont()
        self.font = wx.Font(mode.settings.list_font_size, 
                            self.default_font.GetFamily(),
                            self.default_font.GetStyle(),
                            self.default_font.GetWeight())
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Songlist must be created before the pathname and genre
        # browsers, because they try to populate the songlist at init
        # time
        self.songlist = FileCtrl(self.mode, self)
        self.songlist.SetFont(self.font)

        self.notebook = wx.Notebook(self)
        self.sizer.Add(self.notebook, 1, wx.EXPAND)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        self.pathname = MPDListByPath(self.notebook, self)
        self.pathname.SetFont(self.font)
        self.notebook.AddPage(self.pathname, "Pathname Browser")

        self.genre = MPDListByGenre(self.notebook, self)
        self.genre.SetFont(self.font)
        self.notebook.AddPage(self.genre, "Genre Browser")
        #self.Bind(EVT_NEXTPANEL,self.OnPanelUpdate)

        self.sizer.Add(self.songlist, 1, wx.EXPAND)

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






class MPDMode(MajorMode):
    """Major mode for controlling a Music Player Daemon.

    ...
    """
    debug_level = 0
    keyword='MPD'
    icon='icons/mpd.ico'

    stc_class = MPDSTC

    default_settings = {
        'minor_modes': 'MPD Playlist,MPD Currently Playing',
        'update_interval': 1,
        'volume_step': 10,
        'list_font_size': 8,
        'list_width': 100,
        }
    
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

    def createWindowPostHook(self):
        Publisher().subscribe(self.showMessages, 'mpd')

        # Don't initialize the MPD connection till all the minor modes
        # are created, because their own initialization depends on
        # message passing from the mpd.getStatus() method
        self.initializeConnection()

        self.OnTimer()        
        self.editwin.Bind(wx.EVT_TIMER, self.OnTimer)
        self.update_timer = wx.Timer(self.editwin)
        self.update_timer.Start(self.settings.update_interval*1000)

    def showMessages(self, message=None):
        """debug method to show all pubsub messages."""
        dprint(str(message.topic))

    def OnTimer(self, evt=None):
        self.update()

    def initializeConnection(self):
        self.mpd.getStatus()
        dprint(self.mpd.last_status)

    def update(self):
        self.mpd.getStatus()
        self.idle_update_menu = True

    def isConnected(self):
        return self.mpd is not None


class SongDropTarget(wx.PyDropTarget):
    """Custom drop target modified from the wxPython demo."""
    def __init__(self, window):
        wx.PyDropTarget.__init__(self)
        self.dv = window

        # specify the type of data we will accept
        self.data = SongDataObject()
        self.SetDataObject(self.data)

    # some virtual methods that track the progress of the drag
    def OnEnter(self, x, y, d):
        dprint("OnEnter: %d, %d, %d\n" % (x, y, d))
        return d

    def OnLeave(self):
        dprint("OnLeave\n")

    def OnDrop(self, x, y):
        dprint("OnDrop: %d %d\n" % (x, y))
        return True

    def OnDragOver(self, x, y, d):
        #dprint("OnDragOver: %d, %d, %d\n" % (x, y, d))

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
        dprint("OnData: %d, %d, %d\n" % (x, y, d))

        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list of lines and give it to the viewer
            songs = pickle.loads(self.data.GetData())
            self.dv.AddSongs(x, y, songs)
            
        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d

class PlaylistCtrl(wx.ListCtrl, ColumnSizerMixin):
    def __init__(self, mode, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        ColumnSizerMixin.__init__(self)
        self.mpd = mode.mpd
        self.createColumns()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnStartDrag)
        
        default_font = self.GetFont()
        self.font = wx.Font(mode.settings.list_font_size, 
                            default_font.GetFamily(),
                            default_font.GetStyle(),
                            default_font.GetWeight())
        self.SetFont(self.font)
        self.bold_font = wx.Font(mode.settings.list_font_size, 
                                 default_font.GetFamily(),
                                 default_font.GetStyle(),wx.BOLD)

        self.dropTarget=SongDropTarget(self)
        self.SetDropTarget(self.dropTarget)

        self.songindex = -1
        Publisher().subscribe(self.delete, 'mpd.deleteFromPlaylist')
        Publisher().subscribe(self.appendSong, 'mpd.appendSong')
        Publisher().subscribe(self.playlistChanged, 'mpd.playlist.changed')
        Publisher().subscribe(self.songChanged, 'mpd.song.changed')

        # keep track of playlist index to playlist song id
        self.playlist_cache = []

    def createColumns(self):
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Title")
        self.InsertColumn(2, "Artist")
        self.InsertColumn(3, "Time", wx.LIST_FORMAT_RIGHT)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        self.mpd.play(index)
        evt.Skip()

    def getSelectedSongs(self):
        songlist = []
        index = self.GetFirstSelected()
        while index != -1:
            dprint("song %d" % (index, ))
            songlist.append(index)
            index = self.GetNextSelected(index)
        return songlist
    
    def delete(self, message=None):
        dprint(message)

        # Make sure the message relates to our mpd instance
        if message.data == self.mpd:
            songlist = self.getSelectedSongs()
            if songlist:
                sids = [self.playlist_cache[i] for i in songlist]
                for sid in sids:
                    self.mpd.deleteid(sid)
                self.reset()
                self.setSelected([])
        
    def OnStartDrag(self, evt):
        index = evt.GetIndex()
        print "beginning drag of item %d" % index
        
        data = SongDataObject()
        songlist = self.getSelectedSongs()
        data.SetData(pickle.dumps(songlist,-1))

        # And finally, create the drop source and begin the drag
        # and drop opperation
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        dprint("Begining DragDrop\n")
        result = dropSource.DoDragDrop(wx.Drag_AllowMove)
        dprint("DragDrop completed: %d\n" % result)


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

    def AddSongs(self, x, y, songs):
        index = self._getDropIndex(x, y)
        dprint("At (%d,%d), index=%d, adding %s" % (x, y, index, songs))
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
                dprint("Moving id=%d (index=%d) to %d" % (sid, song, index))
                self.mpd.moveid(sid, index)
                if song >= index:
                    index += 1
                highlight.append(sid)
            else:
                ret = self.mpd.addid(song)
                sid = int(ret['id'])
                self.mpd.moveid(sid, index)
                index += 1
                highlight.append(sid)
        self.mpd.getStatus()
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
        dprint("message received: msg=%s" % str(msg.topic))
        mpd, status = msg.data
        self.reset(visible=self.songindex)
        self.songChanged(msg)
    
    def reset(self, mpd=None, visible=None):
        if mpd is not None:
            self.mpd = mpd
        playlist = self.mpd.playlistinfo()
        list_count = self.GetItemCount()
        index = 0
        cache = []
        show = -1
        for track in playlist:
            if index >= list_count:
                self.InsertStringItem(sys.maxint, str(index+1))
            self.SetStringItem(index, 1, getTitle(track))
            self.SetStringItem(index, 2, getAlbum(track))
            self.SetStringItem(index, 3, getTime(track))
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
        self.resizeColumns([1,0,0,1])

    def appendSong(self, message=None):
        dprint(message)

        # Make sure the message relates to our mpd instance
        if message.data[0] == self.mpd:
            self.mpd.add(message.data[1])
            self.reset(visible = message.data[1])

    def highlightSong(self, newindex):
        if newindex == self.songindex:
            return

        try:
            if self.songindex >= 0:
                item = self.GetItem(self.songindex)
                item.SetFont(self.font)
                self.SetItem(item)
            self.songindex = newindex
            if newindex >= 0:
                item = self.GetItem(self.songindex)
                item.SetFont(self.bold_font)
                self.SetItem(item)            
                self.EnsureVisible(newindex)
            self.resizeColumns()
        except:
            # Failure probably means that the playlist has changed out
            # from under us by another mpd client.  Just skip it and
            # let the playlist get updated by the next playlist
            # changed message
            pass
            
    def songChanged(self, msg):
        dprint(str(msg.topic))
        mpd, status = msg.data
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
        self.playlist = PlaylistCtrl(self.major, parent)
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
        
        Publisher().subscribe(self.songChanged, 'mpd.song.changed')
        Publisher().subscribe(self.songTime, 'mpd.song.time')

    def OnSliderMove(self, evt):
        self.user_scrolling = True
        evt.Skip()
        
    def OnSliderRelease(self, evt):
        self.user_scrolling = False
        dprint(evt.GetPosition())
        self.mpd.seekid(self.songid, evt.GetPosition())

    def songChanged(self, msg=None):
        dprint("songChanged: msg=%s" % str(msg.topic))
        self.reset()

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

    def songTime(self, msg=None):
        dprint("msg=%s" % str(msg.topic))
        mpd, status = msg.data
        self.update(status)

    def update(self, status):
        if status['state'] == 'stop':
            self.slider.SetValue(0)
        elif not self.user_scrolling:
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
                  ("MPD",_("MPD"),Separator("playlist")),
                  ("MPD",_("MPD"),MenuItem(DeleteFromPlaylist)),
                  ("MPD",_("MPD"),Separator("database")),
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

