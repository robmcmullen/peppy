*************************
Up and Running with Peppy
*************************

Once peppy is installed_, starting the application depends how you installed
the code.

.. _installed: /download.html

Downloaded from source:
    If you downloaded peppy but did not install the source, you run the
    application with the command line ``python peppy.py``

Installed from source:
    If you ran ``python setup.py install`` (which is not recommended at this
    point because this is still alpha code), a python script named ``peppy``
    will be installed in the system binary directory, and you can run peppy
    with that command line.

Installed a binary distribution:
    This is only applicable to Windows and Mac OS X. The install process will
    leave an icon somewhere, and you can just click on that.

The recommended way to run peppy is directly from a source distribution.

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
outlined below.  You can see the full list by running peppy with the ``--
help`` argument.

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
their guidelines useful, and so applied them to my work.

There's a File menu that contains the common file load, file save, and related
options.  The Edit menu holds commands related to editing and selecting text
or date.  The Tools menu holds standalone commands that either start a process
or don't change the contents of the document.  The Documents menu


The File Menu
=============

The File menu contains the common file load, file save, and related options.

Opening Files
-------------


Using the Window Menu
---------------------


Using the Documents Menu
------------------------


Saving Files
------------

