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


Hierarchies of Major Modes
--------------------------




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
