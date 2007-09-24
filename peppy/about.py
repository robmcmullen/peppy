# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Definition and storage of the 'about:' protocol.

This provides the about: protocol handling (a read-only protocol) for
built-in storage of data.  It also provides some global user interface
elements for the help menu and other testing menu items.
"""

import os,os.path,sys,re,time,commands,glob,random
import urllib2

import wx

from peppy.debug import *
from peppy.menu import *
from peppy.major import *
from peppy.iofilter import *

# can't use cStringIO because we need to add attributes to it
from StringIO import StringIO

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __version__,__description__,__author__,__author_email__,__url__
substitutes = {
    'prog': 'peppy',
    'yearrange': '2006-2007',
    'version': __version__,
    'description': __description__,
    'author': __author__,
    'author_email': __author_email__,
    'url': __url__,
    'license': "Licensed under the GPL",
    'warning': """This is still alpha software, so please treat accordingly. :)

May be unstable and crash without warning, so don't use this to edit important stuff.  Or, at least make lots of backups.  It probably will save what you're working on, but you never know.  I'm not using this as my primary editor yet, so it hasn't had much of a workout.  By the end of the 0.6.x series of releases, I intend to be using this as my primary editor, so I'll have much more confidence in it by then.
    """,
    'thanks': "",
    'gpl_code': "",
    }
substitutes['copyright'] = 'Copyright (c) %(yearrange)s %(author)s (%(author_email)s)' % substitutes

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
def SetAbout(path,text):
    #eprint("Setting %s: %d bytes" % (path, len(text)))
    aboutfiles[path]=text
    
class AboutHandler(urllib2.BaseHandler):
    # Use local file or FTP depending on form of URL
    def about_open(self, req):
        url = req.get_selector()
        #dprint(url)

        if url not in aboutfiles:
            raise urllib2.URLError("url %s not found" % url)
        text = aboutfiles[url]
        if text.find("%(") >= 0:
            text = text % substitutes
        fh=StringIO()
        fh.write(text)
        fh.seek(0)
        fh.geturl = lambda :"about:%s" % url
        fh.info = lambda :{'Content-type': 'text/plain',
                            'Content-length': len(text),
                            'Last-modified': 'Sat, 17 Feb 2007 20:29:30 GMT',
                            }

        return fh


SetAbout('untitled','')
SetAbout('blank','')

SetAbout('peppy',"""\
<!-- -*- HTMLView -*- -->
<h2>%(prog)s %(version)s</h2>

<h3>%(description)s</h3>

<p>Copyright (c) %(yearrange)s %(author)s (%(author_email)s)</p>

<p>%(license)s</p>

<p>%(warning)s</p>

<p>GPL code borrowed from the following projects:</p>
<ul>
%(gpl_code)s
</ul>
<p>Thanks to lots of folks:</p>
<ul>
%(thanks)s
</ul>
<p>See the file THANKS for more credits.</p>
""")
SetAbout('demo.txt',"""\
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
""")
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


credits=[]

def AddCredit(author, contribution):
    credits.append((author, contribution))
    substitutes['thanks']="\n".join(["<li>%s - %s</li>" % (a,c) for a,c in credits])
        
AddCredit("Mark James", "the free silk icon set (http://www.famfamfam.com/lab/icons/silk/)")
AddCredit("Chris Barker", "for testing on the Mac and many bug reports and feature suggestions")
AddCredit("Julian Back", "for the framework for the C edit mode")

copyrights = []
def AddCopyright(project, website, author, date, reason=None):
    copyrights.append({'website': website,
                       'project': project,
                       'author': author,
                       'date': date,
                       'reason': reason,
                       })
    substitutes['gpl_code']="\n".join(["<li><a href=\"%(website)s\">%(project)s</a> Copyright (c) %(date)s %(author)s</i>" % c for c in copyrights])
        


class HelpAbout(SelectAction):
    name = _("&About...")
    tooltip = _("About this program")
    stock_id = wx.ID_ABOUT

    about = "Test program"
    title = "Test program title"
    
    def action(self, pos=None):
        from wx.lib.wordwrap import wordwrap
        
        info = wx.AboutDialogInfo()
        info.Name = substitutes['prog']
        info.Version = substitutes['version']
        info.Copyright = substitutes['copyright']
        info.Description = wordwrap(substitutes['description'],
            350, wx.ClientDC(self.frame))
        info.WebSite = (__url__, "%(prog)s home page" % substitutes)
        devs = [ substitutes['author'],
                 "",
                 _("Contributions by:"),
                 ]
        dprint([a for a,c in credits])
        devs.extend([a for a,c in credits])
        devs.extend(("", _("See the file THANKS for more credits")))
        info.Developers = devs
        dprint(info.Developers)

        info.License = wordwrap(gpl_text, 500, wx.ClientDC(self.frame))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)


SetAbout('User Manual',"""\
<!-- -*- HTMLView -*- -->
<h2>User Manual for %(prog)s %(version)s</h2>
<p>Copyright (c) %(yearrange)s %(author)s (%(author_email)s)</p>

<p>Well, not so much a user's manual as a placeholder for one.
""")
class HelpManual(SelectAction):
    name = _("&Help...")
    tooltip = _("User manual")
    stock_id = wx.ID_HELP
    key_bindings = {'default': "F1",}
    
    def action(self, pos=None):
        self.frame.open("about:User Manual")
        

class BlankMode(MajorMode):
    keyword='Blank'
    icon='icons/application.png'
    regex="about:blank"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        text=self.buffer.stc.GetText()
        lines=wx.StaticText(win, -1, text, (10,10))
        lines.Wrap(500)
        self.stc = self.buffer.stc
        return win


class AboutPlugin(IPeppyPlugin):
    def getURLHandlers(self):
        return [AboutHandler]

    def scanFilename(self,filename):
        if filename=='about:blank':
            return MajorModeMatch(BlankMode,exact=True)
        else:
            return None

    default_menu=((None,None,Menu(_("&Help")).last()),
                  (None,_("&Help"),MenuItem(HelpAbout).first()),
                  (None,_("&Help"),Separator(_("manual")).first()),
                  (None,_("&Help"),MenuItem(HelpManual).first()),
                  (None,_("&Help"),Separator(_("debug")).first()),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

