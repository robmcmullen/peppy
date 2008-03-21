# To create a development version, run python setup.py develop
from setuptools import setup, find_packages

import distutils
from distutils.core import setup, Extension

setup(
    name = "peppy_mpd",
    version = "0.1",
    description = """Music Player Daemon controller""",
    author = "Rob McMullen",
    author_email = "robm@users.sourceforge.net",
    url = "http://peppy.flipturn.org",
    download_url = "http://peppy.flipturn.org/archive",
    
    py_modules = ['mpd_major_mode', 'mpdclient2'],
    
    entry_points="""
    [peppy.plugins]
    MPD = mpd_major_mode:MPDPlugin
    """
    )
