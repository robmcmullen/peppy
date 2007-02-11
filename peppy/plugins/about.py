# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Definition and storage of the 'about:' protocol.

This provides the about: protocol handling (a read-only protocol) for
built-in storage of data.  It also provides some global user interface
elements for the help menu and other testing menu items.
"""

import os,os.path,sys,re,time,commands,glob,random

import wx

from peppy import *
from peppy.menu import *
from peppy.major_modes.fundamental import FundamentalMode
from peppy.major import *
from peppy.iofilter import *

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __version__,__description__,__author__,__author_email__,__url__

gpl_text="""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

aboutfiles={}
aboutfiles['demo.txt'] = """\
This editor is provided by a class named wx.StyledTextCtrl.  As
the name suggests, you can define styles that can be applied to
sections of text.  This will typically be used for things like
syntax highlighting code editors, but I'm sure that there are other
applications as well.  A style is a combination of font, point size,
foreground and background colours.  The editor can handle
proportional fonts just as easily as monospaced fonts, and various
styles can use different sized fonts.

There are a few canned language lexers and colourizers included,
(see the next demo) or you can handle the colourization yourself.
If you do you can simply register an event handler and the editor
will let you know when the visible portion of the text needs
styling.

wx.StyledTextEditor also supports setting markers in the margin...




...and indicators within the text.  You can use these for whatever
you want in your application.  Cut, Copy, Paste, Drag and Drop of
text works, as well as virtually unlimited Undo and Redo
capabilities, (right click to try it out.)
"""

def SetAbout(path,text):
    aboutfiles[path]=text

SetAbout('untitled','')
SetAbout('alpha','')
SetAbout('bravo','')
SetAbout('blank','')

warning="""This is still alpha software, so please treat accordingly. :)

May be unstable and crash without warning, so don't use this to edit
important stuff.  Or, at least make lots of backups.  It probably will save
what you're working on, but you never know.  I'm not using this as my primary
editor yet, so it hasn't had much of a workout.  By the end of the 0.6.x
series of releases, I intend to be using this as my primary editor, so I'll
have much more confidence in it by then.
"""
SetAbout('title.txt',"%s %s\n%s\n\nCopyright (c) 2006-2007 %s (%s)\n\n%s" % ("peppy",__version__,__description__,__author__,__author_email__,warning))
SetAbout('sample.py','''#!/usr/bin/env python
""" doc string """
import os
from cStringIO import StringIO

globalvar="string"
listvar=[2,3,5,7,11]
dictvar={'a':1,'b':2,'z'=3333}

class Foo(Bar):
    """
    Multi-line
    doc string
    """
    classvar="stuff"
    def __init__(self):
        self.baz="zippy"
        if self.baz=str(globalvar):
            open(self.baz)
        else:
            raise TypeError("stuff")
        return
''')
SetAbout('0x00-0xff',"".join([chr(i) for i in range(256)]))
SetAbout('red.png',
"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\
\x00\x00\x00\x90\x91h6\x00\x00\x00\x03sBIT\x08\x08\x08\xdb\xe1O\xe0\x00\x00\
\x00\x93IDAT(\x91\xb5\x921\x0e\xc3 \x0cE\x7f:0r\x90\x0c,Y\x18\x98\xb8B\x8e\
\xc5\n'\xe4\x160\xfc\x0e\x14K\xb4T(\x91\xf2\xe5\xf1=[\xb2\xbd\x91\xc4\x95\
\xbc.\xd1?B\xadH\t\xdeC)(\x05\xef\x91\x12j\x1d\x18Jr\xe6q\x10\xf8.c\x98\xb3P\
](\x85\xc6LhqJ\x19\x85\x10\xfe\xd2\xadB\x18\x05k\x17\x82\xb5\xa3\xa0\xf5B\
\xd0\xba\x81\xb7\xd7\xba\xef\x0b\xb0\x03]8\xcf\x85 \xc0\xdd\xb5\xb6\xc3M\x9d\
\xf9\xe1dN\x8ct\xee\x83:\xc7\x18\xa5w\xcb\xf6\xf8\xb7\xbe\x01K&\xfa\xcbB\xfe\
\xcc\x08\x00\x00\x00\x00IEND\xaeB`\x82")


class AboutProtocol(ProtocolPluginBase,debugmixin):
    implements(ProtocolPlugin)

    def supportedProtocols(self):
        return ['about']
    
    def getReader(self,urlinfo):
        if urlinfo.path in aboutfiles:
            fh=StringIO()
            fh.write(aboutfiles[urlinfo.path])
            fh.seek(0)
            return fh
        raise IOError



class HelpAbout(SelectAction):
    name = "&About..."
    tooltip = "About this program"

    about = "Test program"
    title = "Test program title"
    
    def action(self, pos=None):
        from wx.lib.wordwrap import wordwrap
        
        info = wx.AboutDialogInfo()
        info.Name = "peppy"
        info.Version = __version__
        info.Copyright = "Copyright (c) 2006 %s (%s)" % (__author__,__author_email__)
        info.Description = wordwrap(
            "This program is a wxPython/Scintilla-based editor written "
            "in and extensible through Python.  Its aim to provide "
            "the user with an XEmacs-like multi-window, multi-tabbed "
            "interface while providing the developer easy ways to "
            "extend the capabilities of the editor using Python "
            "instead of Emacs lisp.\n",
            350, wx.ClientDC(self.frame))
        info.WebSite = (__url__, "peppy home page")
        info.Developers = [ "Rob McMullen",
                            "",
                            "Contributions by:",
                            "Robin Dunn (for wxPython)",
                            "Josiah Carlson (for ideas & code from PyPE)",
                            "Stani Michiels (for ideas & code from SPE)",
                            "Mark James (for the silk icon library)",
                            "The Natural Language Toolkit project (nltk.sourceforge.net) for the chatbot implementations"]

        info.License = wordwrap(gpl_text, 500, wx.ClientDC(self.frame))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)



class AlphaMode(MajorMode):
    keyword='Alpha'
    icon = 'icons/world.png'
    regex = "alpha"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (45, 45))
        return win


class BravoMode(MajorMode):
    keyword='Bravo'
    icon='icons/bug_add.png'
    regex="bravo"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (100,100))
        return win


class BlankMode(MajorMode):
    keyword='Blank'
    icon='icons/application.png'
    regex="about:blank"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        text=self.buffer.stc.GetText()
        wx.StaticText(win, -1, text, (10,10))
        return win

class TitleMode(BlankMode):
    keyword='Title'
    regex="about:title.txt"
    temporary=True


class OpenAlpha(SelectAction):
    name = "&Open Alpha..."
    tooltip = "Open an Alpha object"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:alpha")

class OpenBravo(SelectAction):
    name = "&Open Bravo..."
    tooltip = "Open a Bravo object"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:bravo")



class AboutPlugin(MajorModeMatcherBase):
    implements(IMajorModeMatcher)
    implements(IMenuItemProvider)

    def scanFilename(self,filename):
        if filename=='about:alpha':
            return MajorModeMatch(AlphaMode,exact=True)
        elif filename=='about:bravo':
            return MajorModeMatch(BravoMode,exact=True)
        elif filename=='about:title.txt':
            return MajorModeMatch(TitleMode,exact=True)
        elif filename=='about:blank':
            return MajorModeMatch(BlankMode,exact=True)
        elif filename=='about:untitled':
            return MajorModeMatch(FundamentalMode,exact=True)
        else:
            return None

    default_menu=((None,None,Menu("Help").last()),
                  (None,"Help",MenuItem(HelpAbout).first()),
                  (None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(OpenAlpha).first()),
                  (None,"Test",MenuItem(OpenBravo).first()),
                  ("Alpha",None,Menu("Alpha").after("Major Mode")),
                  ("Alpha","Alpha",MenuItem(OpenAlpha).first()),
                  ("Alpha","Alpha",MenuItem(OpenBravo).first()),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

