"""peppy - (ap)Proximated (X)Emacs Powered by Python.

A full-featured editor for text files and more, Peppy provides an XEmacs-like
multi-window, multi-tabbed interface using the Advanced User Interface
(wx.aui) framework of wxPython.  It is built around the emacs concept of major
modes -- different views are presented to the user depending on the type of
data being edited.  Text files are shown using the wx.stc (Scintilla) editing
component, binary files use a grid layout showing hexadecimal representation
of the binary data, scientific image datasets are displayed using a raster
band image displayer, and more.  Peppy is designed to be very extensible using
setuptools plugins.

The program is inspired by emacs, and I borrowed quite a lot of emacs
terminology, including frames and buffers, the minibuffer concept, and the
keyboard bindings.  I did not borrow emacs lisp, however; that being the
primary reason for me wanting to move away from emacs.  I find it easy to
think in Python, unlike lisp which my brain can't seem to flush fast enough
after learning just enough to hack XEmacs.

Plugins
=======

peppy is extended by plugins.  Plugins are based on the U{yapsy component
architecture<http://yapsy.sourceforge.net>} and are discovered using
setuptools plugins.

Many parts of the peppy system are exposed through the L{IPeppyPlugin}
interface, but most interesting for now are L{IPeppyPlugin.getMajorModes}
used to specify the Major Modes provided by the plugin and
L{IPeppyPlugin.getActions} to specify the actions that provide the user
interface for the major mode.

Major Modes
===========

A major mode is a specialized editing mode that is associated with a type of
file.  It takes its name from the emacs concept of the same name.  A major
mode provides the user interface and specialized editing commands to edit
a type of file.  There are several ways to identify files, one of the most
useful being the MIME type of the file.  (Major modes can also use other
means to identify files that they are capable of operating on, like filename
matching and even scanning bytes in the file.)

See the documentation for the L{MajorMode} class for more information
on the interface for major mode subclasses, and also instances like
L{FundamentalMode} for an example of a mode for general text files,
L{PythonMode} for a specific type of text file, and L{HexEditMode} for a major
mode that doesn't use a text window as its user interface.

Actions
=======

Peppy uses the term Action to represent any response from the user interface,
whether it be from the menu bar, tool bar, or keyboard.  The class
L{SelectAction} is used as the base class for all the possible actions that
the user can perform.  Actions are associated with a major mode (or several
major modes or the entire application) and can be provided by plugins.  They
contain a default menu item text, toolbar icon, and keyboard shortcut.

Virtual File System (VFS)
=========================

One of the advances used by peppy is the U{itools
<http://www.ikaaro.org/itools>} virtual filesystem layer, an abstraction of
the filesystem that allows for transparent file access whether the file is
local to your hard disk, or across the network to a webdav server, an FTP
server, or tunnelled over ssh.  At least theoretically -- the network stuff
isn't available yet, but it will be at some point, and then they'll be able to
be transparently integrated with peppy.

Behind the scenes, all file access in peppy is through URLs, although local
files are handled as a special case not requiring the leading C{file://}
component.

The virtual filesystem is extensible, but it's currently beyond the scope of
this documentation.  If you're interested, you can see the L{TarFS} example to
see how I implemented a pseudo-filesystem that allows reading individual files
from within tar archives without decompressing the whole file first.
"""

# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__bug_report_email__ = "bugs@peppy.flipturn.org"
__url__ = "http://peppy.flipturn.org/"
__download_url__ = "http://peppy.flipturn.org/archive/"
__bug_report_url__ = "http://trac.flipturn.org/newticket"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, wxwindows, scintilla"
__license__ = "GPL"

# The real version number is maintained in a file that's under version control
# so I don't have to keep updating and checking in the file
try:
    import _peppy_version
    __version__ = _peppy_version.version
    __codename__ = _peppy_version.codename
except ImportError:
    __version__ = "svn-devel"
    __codename__ = "svn-codename"
