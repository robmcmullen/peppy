@echo off
rem = """-*-Python-*- script
rem Windows batch script based on pylint's batch scripts
rem Don't know how this works, but it does.
rem
rem -------------------- DOS section --------------------
rem You could set PYTHONPATH or TK environment variables here
python -x "%~f0" %*
goto exit

"""
# -------------------- Python section --------------------
import os,sys

# Set default translation as a no-op for the moment (the actual translation is
# performed on-demand during the GUI creation, not at application start time).
import __builtin__
__builtin__._ = unicode

import peppy.main

peppy.main.main()

DosExitLabel = """
:exit
rem """


