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

import peppy.vfs as vfs

from peppy.debug import *
from peppy.menu import *
from peppy.major import *

# can't use cStringIO because we need to add attributes to it
from StringIO import StringIO

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __version__, __codename__, __description__, __author__, __author_email__, __url__
substitutes = {
    'prog': 'peppy',
    'yearrange': '2006-2007',
    'version': __version__,
    'codename': __codename__,
    'description': __description__,
    'author': __author__,
    'author_email': __author_email__,
    'url': __url__,
    'license': "Licensed under the GPL",
    'warning': """<P>I'm dogfooding!  This is now my primary editor,
but caveat emptor: it is still alpha code.  It has all of the basic features
that I need for my day-to-day editing, and for the most part it has replaced
XEmacs as my daily editor.  I've planned much more development, though,
and I also intend to work on a lot of documentation to make it easier for
contributors to extend the editor.

<P>Save your work often and file a bug report at
http://trac.flipturn.org/newticket if you notice something that shouldn't
be happening.
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

def findAbout(path):
    if path in aboutfiles:
        return aboutfiles[path]
    plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
    for plugin in plugins:
        #dprint("checking plugin %s" % plugin)
        files = plugin.aboutFiles()
        if path in files:
            return files[path]
    return None

class AboutFS(vfs.BaseFS):
    @staticmethod
    def exists(reference):
        path = str(reference.path)
        text = findAbout(path)
        return text is not None

    @staticmethod
    def is_file(reference):
        return AboutFS.exists(reference)

    @staticmethod
    def is_folder(reference):
        return False

    @staticmethod
    def can_read(reference):
        return AboutFS.exists(reference)

    @staticmethod
    def can_write(reference):
        return False

    @staticmethod
    def get_size(reference):
        path = str(reference.path)
        text = findAbout(path)
        if text:
            return len(text)
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @staticmethod
    def open(reference, mode=None):
        path = str(reference.path)
        #dprint(url)
        
        text = findAbout(path)
        if text is None:
            raise IOError("[Errno 2] No such file or directory: '%s'" % reference)
        if text.find("%(") >= 0:
            text = text % substitutes
        fh=StringIO()
        fh.write(text)
        fh.seek(0)

        return fh

vfs.register_file_system('about', AboutFS)


SetAbout('untitled','')
SetAbout('blank','')
SetAbout('scratch','-*- Fundamental -*-')

SetAbout('peppy',"""\
<!-- -*- HTMLView -*- -->
<h2>%(prog)s %(version)s \"%(codename)s\"</h2>

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


credits={}
def AddCredit(author, contribution):
    credits[author] = contribution
    substitutes['thanks']="\n".join(["<li>%s - %s</li>" % (a,c) for a,c in credits.iteritems()])
        
AddCredit("Mark James", "the free silk icon set available at http://www.famfamfam.com/lab/icons/silk/")
AddCredit("Chris Barker", "for testing on the Mac and many bug reports and feature suggestions")
AddCredit("Julian Back", "for the framework for the C edit mode")
AddCredit("Thibauld Nion", "for the Yapsy plugin framework.  Note: Yapsy is BSD licensed and can be downloaded under that license from at http://yapsy.sourceforge.net/")
AddCredit("Peter Damoc", "for the feature suggestions")
AddCredit("Stani Michiels", "for the scintilla fold explorer he shared with the pyxides mailing list")
AddCredit("David Eppstein", "for his public domain python implementation of the TeX word wrapping algorithm")

copyrights = {}
def AddCopyright(project, website, author, date, reason=""):
    copyrights[project] = ({'website': website,
                       'project': project,
                       'author': author,
                       'date': date,
                       'reason': reason,
                       })
    substitutes['gpl_code']="\n".join(["<li>%(reason)s <a href=\"%(website)s\">%(project)s</a> Copyright (c) %(date)s %(author)s</i>" % c for c in copyrights.values()])
