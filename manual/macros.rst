********
Macros *
********

.. _macros:

Macros are a set of actions that are recorded for later playback.  They are
used as a convenient shortcut to perform repetitive tasks.


Hierarchical Macros
===================

Macros are associated with major modes, and because Peppy uses a hierarchical
system of major modes (see :ref:`hierarchies`), macros are displayed only if they
are appropriate for the current major mode.

Note that macros for more general major modes will be available.  For
example, when editing python source files using Python mode, Fundamental mode
macros will also be available.  However when editing plain text files using
Fundamental mode, you will not be able to use Python mode macros.  This keeps
the user interface much less cluttered.



Recording Macros
================

Start recording a macro using the Tools -> Macros -> Start Recording menu item,
or the equivalent keystroke.  For windows keybindings, the default keystroke is
Ctrl+Shift+9.  For emacs, the standard emacs binding of 'C-x (' is available.

Once recording, every action that makes a direct change to the contents of the
document will be recorded.  For example, characters will be recorded as you
type, and keystrokes that have special meaning (like using TAB to reindent the
line or RETURN to end the current line and autoindent the next line) will be
recorded such that on playback they will apply their function.

Actions will be recorded until you stop recording
using the Tools -> Macros -> Stop Recording menu item (or its equivalent
keystroke: Ctrl+Shift+0 or 'C-x )' with emacs keybindings).

Changing tabs will abort macro recording.

By default, macros are saved using a name derived from the characters that
you typed.  Macros can be renamed to give them more meaning to you; see the
section :ref:`macrominormode` below.

You can also bind a macro to a keystroke.  After finishing the macro recording,
use the Tools -> Macros -> Add Keybinding for Last Macro menu item.  You'll
be prompted to enter a sequence of keystrokes followed by the RETURN character
that ends the sequence.  The keystrokes will then be bound to that macro
so whenever you are in the current major mode, that sequence of keys will
automatically trigger the macro.

Macros in Peppy are automatically saved so they'll be available the next time
you use the program.


Playback of Macros
==================

In addition to macros being triggered by the keystroke set using the Add
Keybinding for Last Macro menu item, macros can be played back by last macro
defined, by name, or by selecting the macro from a list.

Tools -> Macros -> Play Last Macro will replay the last macro recorded, assuming
the macro is valid for the current major mode.  If not, nothing happens.

Tools -> Macros -> Execute Macro brings up a minibuffer that allows you to use
tab completion to type in the name of the macro you'd like to replay.

Macros can also be executed by selecting them from a list: see the section
below for more information.

.. _macrominormode:

Macro Minor Mode
================

In the major mode sidebar on the right hand side of the text, you'll see a
springtab named "Macros".  This is the Macro Minor Mode -- it contains the
user interface for managing the macros that work with the current major mode.

Clicking on the Macros button will pop out the window that contains the
hierarchy of major modes applicable to the current major mode and the macros
defined for each of those major modes:

[pic here of macro minor mode]

Right clicking on a macro will bring up a context menu showing various options,
like Edit, Rename, Delete, and an option to provide a new keybinding.


Editing Macros
--------------

Macros are stored as snippets of Python code, and they can be edited to provide
even more functionality than is available by simply recording keystrokes.
This is a bit of an advanced topic, so some care is needed to make sure that
the macro will function properly if you add custom python code to the macro.

Regardless of the major mode for which the macro was recorded, macros are
Python code -- therefore the normal Python mode is used to make changes.  For
example, even if the macro is for C++ mode, you edit the macro itself using
Python mode.

You must save your changes by selecting File -> Save in order for the updated
macro to take effect.
