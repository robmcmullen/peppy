#!/usr/local/bin/wish -f
# Hello World in tcl/tk
# Some more comments about this file

wm title . "Hello world!"

frame .h -borderwidth 2
frame .q -borderwidth 2
button .h.hello -text "Hello world" \
        -command "puts stdout \"Hello world!\"" -cursor gumby
button .q.quit -text "Quit" -command exit -cursor pirate

pack .h -side left
pack .q -side right
pack .h.hello
pack .q.quit
