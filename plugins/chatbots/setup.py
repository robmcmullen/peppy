# To create a development version, run python setup.py develop
from setuptools import setup, find_packages

import distutils
from distutils.core import setup, Extension

setup(
    name = "peppy_chatbots",
    version = "0.2",
    description = """Eliza and other chatbots from nltk""",
    author = "Rob McMullen",
    author_email = "robm@users.sourceforge.net",
    url = "http://peppy.flipturn.org",
    download_url = "http://peppy.flipturn.org/archive",
    
    packages=['nltk', 'nltk.chat'],
    
    py_modules = ['chatbots'],
    
    entry_points="""
    [peppy.plugins]
    Chatbots = chatbots:ChatPlugin
    """
    )
