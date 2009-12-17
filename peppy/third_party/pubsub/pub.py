"""
All pubsub v3 core functionality is provided by this module::

  from pubsub import pub
  pub.sendMessage(...)
  
:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.
"""

__all__ = []


def importSymbols(module):
    '''Get all the attributes from module and make them
    accessible from our own module.'''
    attribs = {}
    # we have to use dir() rather than vars() beccause obj may not be a module
    for attrib in dir(module):
        if not attrib.startswith('_'):
            attribs[attrib] = getattr(module, attrib)

    #print 'imported ', attribs.keys()
    globals().update(attribs)


from core import pubsub3
importSymbols(pubsub3)

from utils import globalsettings as utilsSettings
utilsSettings.setPackageImported()


# print '__all__', __all__
