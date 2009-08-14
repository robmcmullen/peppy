*********************
Text Editing Basics *
*********************

.. _fundamental:

Fundamental Mode
================

Fundamental mode is the basis for all source code editing modes in peppy.
All of the text editing functions that are common to more than one mode are
generally placed in Fundamental mode.  If you're familiar with object oriented
programming concepts, Fundamental mode is the *superclass* of the other text
editing modes.

.. _hierarchies:

Hierarchies of Major Modes
--------------------------

There are different hierarchies of major modes in peppy, but the primary
hierarchical tree starts from Fundamental mode.  Major modes that are used
to edit text files descend from Fundamental mode, and therefore are part of
this hierarchy.

Hierarchies are important because many of the commands available in Peppy are
based on the major mode of the current file.  Actions are only presented to
you in the menubar and toolbar if they're appropriate to the major mode.  For
instance, when editing text files, it doesn't make sense to include actions
used to edit images.

The major mode hierarchy starting with Fundamental mode includes Python
mode, C++ mode, Bash mode, and all the other modes used to edit source code.
Fundamental mode is the more general major mode, so all actions available for
Fundamental mode are available to Python mode, for instance.  However, Python
mode actions are not available to Fundamental mode.



Scintilla and the Styled Text Control
-------------------------------------

Peppy uses the wxPython component called the StyledTextCtrl for its user
interface, which is based on the source code editing component called
Scintilla__.  Scintilla and the StyledTextCtrl supply the highlighting, syntax
coloring, code folding, line numbers, word wrapping, and many more built-in
features.  Additionally, due to the cross-platform nature of both wxPython and
Scintilla, peppy operates in very similarly across the three major classes of
operating systems supported by wxPython: unix-like systems, Windows, and Mac
OS X.

__ www.scintilla.org


View Settings
=============


Cut, Copy, and Paste
====================


Middle Mouse Paste
------------------


Undo and Redo
=============


Find and Replace
================


Wildcard / Shell Style
----------------------

Regular Expressions
-------------------


Running Scripts
===============

Filters
-------
