# To create a development version, run python setup.py develop
from setuptools import setup, find_packages

import distutils
from distutils.core import setup, Extension

setup(
    name = "peppy_games",
    version = "0.1",
    description = """Simple games and diversions""",
    author = "Rob McMullen",
    author_email = "robm@users.sourceforge.net",
    url = "http://peppy.flipturn.org",
    download_url = "http://peppy.flipturn.org/archive",
    
    py_modules = ['hangman_mode', 'fractal_mode'],
    
    entry_points="""
    [peppy.plugins]
    Hangman = hangman_mode:HangmanPlugin
    Mandelbrot = fractal_mode:MandelbrotPlugin
    """
    )
