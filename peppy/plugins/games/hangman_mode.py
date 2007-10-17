# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Major mode for playing hangman using the words in the buffer.

Adapted from hangman.py from the wxPython distribution by Harm van der
Heijden.  From the code:

A simple wxPython game, inspired by the old bsd game by Ken Arnold.

From the original man page:

 In hangman, the computer picks a word from the on-line
 word list and you must try to guess it.  The computer
 keeps track of which letters have been guessed and how
 many wrong guesses you have made on the screen in a
 graphic fashion.

That says it all, doesn't it?

Have fun with it,

Harm van der Heijden (H.v.d.Heijden@phys.tue.nl)
"""

import os, random
from cStringIO import StringIO

import wx
import wx.stc

from peppy.menu import *
from peppy.major import *
from peppy.stcinterface import *
from peppy.lib.iconstorage import *

_sample_file="""\
albatros  banana  electrometer  eggshell
"""

icondict = {
'hangman.png':
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\
\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\
\x00\x00oIDAT8\x8d\xedS\xb1\r\x800\x0c\xb3Y\x98\x98y\x85oz\r\xcf\xf2\x84Y\
\x02J\xa1Q(\x13\x03\x96\xa26m\xea$\x95CI\xf0 Y\x1f4 \x89\xc7~\xc8\x823\x84\
\x04\x96e5w\x94D\x9f\xd9\x07V\x06@f\xc5\xd6\xe9z\xef}&\x7f0K\xda^\xb5\x00`\
\xc9\x1e\x03\x88+h\xf6\xdbY\xc1#\xfc\x04_ 8u\x10Ma\xa6\x87\x9b\x90z\xb1\x03\
\x03\xaaO\xfa\xd1L{_\x00\x00\x00\x00IEND\xaeB`\x82'
}
addIconsFromDict(icondict)


class PlayHangman(SelectAction):
    """
    Start a game of hangman.
    """
    alias = _("hangman")
    name = _("Hangman")
    tooltip = _("Start a hangman game")
    default_menu = "Tools/Games"

    def action(self, index=-1, multiplier=1):
        # FIXME: if the current buffer is based on the PeppySTC, it should open
        # the game using the current stc rather than the small word list
        self.frame.open("about:words.hangman")


class RestartGame(SelectAction):
    alias = _("restart-game")
    name = _("Restart Game")
    tooltip = _("Restart Game")
    default_menu = ("Hangman", 100)
    key_bindings = {'default': 'C-R'}

    @classmethod
    def worksWithMajorMode(cls, mode):
        return isinstance(mode, HangmanMode)
    
    def action(self, index=-1, multiplier=1):
        self.mode.stc.restart()


class HangmanSTCWrapper(STCProxy):
    def __init__(self, stc, win, min_length=5):
        self.stc = stc
        self.win = win
        self.min_length = min_length

        # only look at the first 100K characters in the buffer
        self.max_text_length = 100000
        
    def CanEdit(self):
        return False

    def CanCopy(self):
        return False

    def CanCut(self):
        return False

    def CanPaste(self):
        return False

    def CanUndo(self):
        return False

    def CanRedo(self):
        return False

    def getWord(self):
        reg = re.compile('\s+([a-zA-Z]+)\s+')
        n = 50 # safety valve; maximum number of tries to find a suitable word
        num = self.stc.GetLength()
        if num > self.max_text_length:
            num = self.max_text_length
        text = self.stc.GetTextRange(0, num)
        while n:
            index = int(random.random()*num)
            m = reg.search(text[index:])
            if m and len(m.groups()[0]) >= self.min_length: break
            n = n - 1
        if n: return m.groups()[0].lower()
        return "error"

    def restart(self):
        word = self.getWord()
        self.win.StartGame(word)


class HangmanWnd(wx.Window):
    def __init__(self, parent, id, pos=wx.DefaultPosition, size=wx.DefaultSize):
        wx.Window.__init__(self, parent, id, pos, size)
        self.SetBackgroundColour(wx.NamedColour('white'))
        if wx.Platform == '__WXGTK__':
            self.font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL)
        else:
            self.font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL)
        self.SetFocus()
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.max_misses = 7

    def OnSize(self, event):
        self.Refresh()
        
    def StartGame(self, word):
        self.has_won = False
        self.word = word
        self.guess = []
        self.tries = 0
        self.misses = 0
        self.Draw()

    def InProgress(self):
        if not self.has_won and self.misses < self.max_misses:
            return True
        return False

    def EndGame(self):
        self.misses = self.max_misses;
        self.guess = map(chr, range(ord('a'),ord('z')+1))
        self.Draw()

    def HandleKey(self, key):
        self.message = ""
        if self.guess.count(key):
            self.message = 'Already guessed %s' % (key,)
            return 0
        self.guess.append(key)
        self.guess.sort()
        self.tries = self.tries+1
        if not key in self.word:
            self.misses = self.misses+1
        if self.misses == self.max_misses:
            self.EndGame()
            return 1
        has_won = 1
        for letter in self.word:
            if not self.guess.count(letter):
                has_won = 0
                break
        if has_won:
            self.has_won = True
            self.Draw()
            return 2
        self.Draw()
        return 0

    def Draw(self, dc = None):
        if not dc:
            dc = wx.ClientDC(self)
        dc.SetFont(self.font)
        dc.Clear()
        (x,y) = self.GetSizeTuple()
        x1 = x-200; y1 = 20
        for letter in self.word:
            if self.guess.count(letter):
                dc.DrawText(letter, x1, y1)
            else:
                dc.DrawText('.', x1, y1)
            x1 = x1 + 10
        x1 = x-200
        dc.DrawText("tries %d misses %d" % (self.tries,self.misses),x1,50)
        guesses = ""
        for letter in self.guess:
            guesses = guesses + letter
        dc.DrawText("guessed:", x1, 70)
        dc.DrawText(guesses[:13], x1+80, 70)
        dc.DrawText(guesses[13:], x1+80, 90)
        dc.SetUserScale(x/1000.0, y/1000.0)
        self.DrawVictim(dc)

    def DrawVictim(self, dc):
        dc.SetPen(wx.Pen(wx.NamedColour('black'), 20))
        dc.DrawLines([(10, 980), (10,900), (700,900), (700,940), (720,940),
                      (720,980), (900,980)])
        dc.DrawLines([(100,900), (100, 100), (300,100)])
        dc.DrawLine(100,200,200,100)
        if ( self.misses == 0 ): return
        dc.SetPen(wx.Pen(wx.NamedColour('blue'), 10))
        dc.DrawLine(300,100,300,200)
        if ( self.misses == 1 ): return
        dc.DrawEllipse(250,200,100,100)
        if ( self.misses == 2 ): return
        dc.DrawLine(300,300,300,600)
        if ( self.misses == 3) : return
        dc.DrawLine(300,300,250,550)
        if ( self.misses == 4) : return
        dc.DrawLine(300,300,350,550)
        if ( self.misses == 5) : return
        dc.DrawLine(300,600,350,850)
        if ( self.misses == 6) : return
        dc.DrawLine(300,600,250,850)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.Draw(dc)


class HangmanMode(MajorMode):
    """
    Major mode for playing hangman.  It uses the normal stc buffer as
    a backend for the dictionary of words.
    """
    debuglevel=0

    keyword="Hangman"
    icon='hangman.png'
    regex="\.(hangman)"

    default_classprefs = (
        IntParam('min_word_length', 5),
        )
    won = 0
    played = 0
    average = 0.0
    history = []

    def createEditWindow(self, parent):
        """Create the hangman window that is the user interface to this mode.

        @param parent: parent window in which to create this window 
        """
        assert self.dprint()

        win = HangmanWnd(parent, -1)        
        return win

    def createWindowPostHook(self):
        """Initialize the hangman window."""
        self.stc = HangmanSTCWrapper(self.buffer.stc, self.editwin,
                                     self.classprefs.min_word_length)
        self.stc.restart()

    def createEventBindingsPostHook(self):
        self.editwin.Bind(wx.EVT_CHAR, self.OnChar)

    def UpdateAverages(self, has_won):
        if has_won:
            self.won = self.won + 1
        self.played = self.played+1
        self.history.append(self.editwin.misses) # ugly
        total = 0.0
        for m in self.history:
            total = total + m
        self.average = float(total/len(self.history))

    def OnChar(self, evt):
        if not self.editwin.InProgress():
            return
        key = evt.GetKeyCode();
        #print key
        if key >= ord('A') and key <= ord('Z'):
            key = key + ord('a') - ord('A')
        key = chr(key)
        if key < 'a' or key > 'z':
            event.Skip()
            return
        res = self.editwin.HandleKey(key)
        if res == 0:
            self.frame.SetStatusText(self.editwin.message)
        elif res == 1:
            self.UpdateAverages(0)
            self.frame.SetStatusText("Too bad, you're dead!",0)
        elif res == 2:
            self.UpdateAverages(1)
            self.frame.SetStatusText("Congratulations!",0)
        if self.played:
            percent = (100.*self.won)/self.played
        else:
            percent = 0.0
        self.frame.SetStatusText("p %d, w %d (%g %%), av %g" % (self.played,self.won, percent, self.average),1)


class HangmanPlugin(IPeppyPlugin, debugmixin):
    """
    Image viewer plugin that registers the major mode and supplies the
    user interface actions so we can use the mode.
    """
    def aboutFiles(self):
        return {"words.hangman": _sample_file}
    
    def getMajorModes(self):
        yield HangmanMode
    
    def getActions(self):
        return [PlayHangman, RestartGame]
