*************************
Up and Running with Peppy
*************************

Once peppy is installed__, starting the application depends how you installed
the code.

__ /download.html

Installed using easy_install: (RECOMMENDED)
    If you used ``easy_install`` to install the latest version from the Python
    Package Index, a python script named ``peppy`` will be installed in the
    system binary directory, so simply typing ``peppy`` on the command line
    will start the program.

Downloaded from source:
    If you downloaded peppy but did not install the source, you run the
    application with the command line ``python peppy.py`` from within the
    peppy directory.

Installed from the downloaded source:
    If you ran ``python setup.py install`` on the downloaded source, a python
    script named ``peppy`` will be installed in the system binary directory.

Installed a binary distribution:
    This is only applicable to Windows and Mac OS X. The install process will
    leave an icon somewhere, and you can just click on that.

Command Line Use
================

When you start peppy from the command line, you can specify options and URLs
to load.  For example, running from a source distribution, you might use a
command line like this:

``python peppy.py README /tmp/file.txt http://www.flipturn.org/index.html``

which tells peppy to open three URLs: the local file ``README`` in the
current directory, the file ``/tmp/file.txt``, and the ``index.html`` file from
``http://www.flipturn.org``.


Options
-------

There are many command line options available, the most useful of which are
outlined below.  You can see the full list by running peppy with the ``--help``
argument.

-d:
    Send all debug printing to the console

-t:
    Run in test mode -- allow multiple peppy processes (see the next section)
    and send all debug printing to the console

-v:
    Run in verbose mode, which turns on **a lot** of debugging output.  Use in
    combination with ``-d`` or ``-t`` to send the output to the console


Single Peppy Process
====================

Normally, peppy only allows a single process per user so that subsequent file
open requests (by starting peppy from the command line with an argument) will
actually be opened by the already running process.  This can be disabled by
preference or by the ``-t`` option as described above.


Using the Basic Menu Functions
==============================

The GUI should be similar to typical windowed applications
on your platform.  The layout of the menu attempts to
follow the `Apple style guidelines for the menu bar
<http://developer.apple.com/documentation/UserExperience/Conceptual/OSXHIGuidelines/XHIGMenus/chapter_17_section_4.html>`_
even though peppy works with all platforms and not just Mac OS X. I found
their guidelines useful and logical, and so applied them to my work.

There are seven menu titles that will always appear in the menu bar, and
additional titles depending on the major mode.  The seven are: File, Edit,
View, Tools, Documents, Window, and Help.

The File menu contains the common file load, file save, and related options.
The Edit menu holds commands related to editing and selecting text or data,
and also is where you'll find the :ref:`preferences <preferences>`.  View
holds menu items that affect how the major mode displays its contents, but
nothing that actually alters the data -- just how the data is viewed.  The
Tools menu holds standalone commands that either start a process or don't
change the contents of the document.  The Documents menu contains a list of
currently open documents, but note that some documents may not have an active
view.  Window holds a list of top level peppy windows, allowing you to switch
back and forth between them.  And finally, Help contains menu items related
to documentation.


Opening Files
-------------

Peppy provides several commands to open files, from the traditional GUI file
dialog using the File -> Open -> Open File menu command, to the more emacs-
like File -> Open -> Open File using Minibuffer command (bound to C-x C-f in
emacs keybinding mode).


Editing Files
-------------

Once a file has been opened, a new tab will appear in the window that shows
the GUI that is used to edit that type of file.  There are specific types of
editing modes, called :ref:`major modes <majormodes>`, for different types
of files.  For instance, plain text files are editing using the Fundamental
major mode, while python source files are edited using the Python major mode.
Both these major modes are similar is that they use a text editing component
(called the StyledTextCtrl in wxPython, which is based on the Scintilla__
source code editing component).  However, unlike most editors, text files
are not the only thing that can be edited.  There are major modes for editing
:ref:`binary files <hexedit>`, and even :ref:`hyperspectral images <hsi>`.

__ http://www.scintilla.org

Saving Files
------------

After editing the file, it must be saved before the changes can be made
permanent.  Like opening files, there are several ways to save the file.
You can use the File -> Save to save the file if you want to overwrite your
changes, or File -> Save As to pull up a traditional file save dialog to save
it to a new file.  Some major modes provide other ways to save the file in the
File -> Export menu.
