********
Concepts
********

Peppy provides a fairly standard looking graphical user interface that should
be familiar if you've used a text editor before.  However, there are several
unique features that may not be obvious, and these are described here.

User Interface
==============

.. image:: peppy-python-mode.png
   :align: center

Top Level Windows
-----------------

Peppy can display multiple top level windows, each of which can display an
arbitrary number of tabs.  Each tab contains exactly one major mode, which is
to say that each tab contains one view of a document.


.. _majormodes:

Major Modes
-----------

A major mode is a specific type of user interface window for a particular
type of file.  For example, the Python Major Mode in the image above shows a
typical text editor window with line numbers on the left side, a cursor for
typing, and scroll bars for moving back and forward in the document.

Other major modes like HexEdit:

.. image:: peppy-hexedit-mode.png
   :align: center

provide a different type of user interface.  Some types of major modes are
specific to a type of file and some are more general and can be used to edit
many types of files.

Menu Bar
--------

The menu bar of peppy is dynamic, and is customized depending on the major
mode.  Switching major modes by changing tabs or loading a new file causes
the menu bar to be modified so that it only displays items relevant to the
current major mode.  This prevents cluttering the user interface with a bunch
of grayed out items that don't apply to what you're editing at the moment.

Tool Bar
--------

The tool bar is likewise dynamic, and shows only those tool bar items that are
appropriate to the current major mode.  The tool bar may also be turned off if
you don't like a tool bar or if you want a little extra vertical space for the
major mode.


Files as URLs
=============

All files in peppy are treated as being referenced by a URL, even local files.
This abstraction makes it easy to add support for new URL schemes to load
files, and for the most part, it makes no difference what scheme has been
used to load a file.

Local files can be specified as simple pathnames, like **/Users/rob/file.txt**,
or as full URLs like **file:///Users/rob/file.txt**.  Note that URLs
always use forward slashes even on windows.  A windows path **C:\Program
Files\peppy\peppy.exe** is equivalent to the URL **file://C:/Program
Files/peppy/peppy.exe**


Automatic Recognition of File Type
----------------------------------

Another unique aspect of peppy is the lengths to which it goes to identify
a file.  Because most text editors assume that the file that you're loading
is a text file, they don't spend much time trying to figure out what type of
file it really is.  They just look at the file extension and assume that it
correctly identifies the text within it.

Peppy does take into account the filename and extension when identifying a file,
but it doesn't *just* do that -- it also provides several hooks in the file
loading process to examine the URL or the contents of the file to determine
what type of file it is.  This set of heuristics allows peppy to correctly
determine the major mode to use even if the file is incorrectly labeled, or in
cases where the same file extension is used for different types of data.


Network File Systems
====================

Peppy uses the virtual file system from `itools
<http://www.ikaaro.org/itools/>`_ to provide the framework to support
networked file loading.  It provides the means to load files based on the
*protocol* (also called the *scheme*) of the URL.  For example, the protocol
of the URL **http://peppy.flipturn.org** is *http*, and the protocol of
**file://C:/Program Files/peppy/peppy.exe** is *file*.

HTTP
----

Read-only support is provided for files using the http protocol, so any file
that is visible to a normal web browser can be loaded by peppy.  Obviously,
due to the read-only nature of normal http servers, you will have to save the
file using some other protocol.

WebDAV
------

The 0.13.0 release added experimental support for the `WebDAV protocol
<http://www.webdav.org/specs/rfc2518.html>`_, which is a distributed
filesystem based on web servers.

This is an *experimental* addition to peppy, and a work in progress.  I have
tested it quite a bit, but this is the first networked filesystem that peppy
supports for both reading and writing, and there may still be issues to
resolve.

Also note that the current implementation of WebDAV will lock the GUI until
the operation completes, so if a WebDAV server freezes in the middle of a
transfer, you're stuck.  Multithreaded operation of the networked file systems
is planned, the goal being to provide an opportunity to cancel an operation if
it is taking too long.

WebDAV files and directories are accessed using URLs like
**webdav://www.webdavserver.com/path/to/file**, where peppy will prompt
you for authentication information and remember the authentication for the
duration of your editing session.  Optionally, a less secure method is also
supported where you embed the authentication information directly into the URL
itself, like: **webdav://user:pass@www.webdavserver.com/path/to/file**

SFTP
----

The 0.14.1 release added experimental support for the `SSH File Transfer
Protocol (SFTP) <http://en.wikipedia.org/wiki/SSH_file_transfer_protocol>`_,
which is a method to access a remote filesystem using the SSH protocol to
provide encryption and security.

This is currently an *experimental* addition to peppy, but is expected to be a
stable feature in the next major release of peppy.

SFTP files and directories are accessed using URLs like
**sftp://some.server.com/path/to/file**, where peppy will prompt you
for authentication information and remember the authentication for the
duration of your editing session.  A username may also be specified,
like **sftp://username@some.server.com/path/to/file**, in which case
peppy will prompt you for the password by popping up a dialog box.  Also
supported, but not recommended, is to include the password in the URL like
**sftp://username:passwd@some.server.com/path/to/file**, but this will result
in the storage of the plain text password in history files and other places.
Definitely not recommended.

Other Network File Systems
--------------------------

Support for other network protocols may be added in the future.  Under
consideration are the old insecure FTP protocol, as well as the Files
transferred over Shell (FISH) protocol.


Special File Systems
--------------------

There are also some built-in schemes, like **about:** that used for read only
documentation, **mem:** used for an in-memory temporary file system, **tar:**
used for read only access to files contained within tar files, and more
esoteric schemes like **aptus:** which is used in the fractal renderer.


Documents and Views
===================

A URL uniquely identifies a file on some file system, and peppy uses the URL
as the identifier of a loaded document.  Only one copy of a document exists in
peppy, but it can have many different views in the user interface.  And, even
if no more views exist of the document, it is still kept in memory by peppy
until you explicitly delete it from memory.

Opened files appear in the *Documents* menu, and a particular document can be
opened in any peppy window by selecting it from the menu.  A new tab containing
a view of the document will appear, using its default major mode.  Deleting
the tab only causes the tab to go away; it doesn't delete the document.  Only
when closing the document will the document be removed from memory.

