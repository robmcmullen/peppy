'''
This module is for internal use by pubsub. Do not import directly.
It is required for backward compatibility with legacy wxPython code.

This module is automatically imported and used by pubsub when pubsub
is first imported, IF pubsub is able to find a module called
'autosetuppubsubv1' on the search path. This indicates to pubsub
that it should default to v1 API, such that a simple
"from pubsub import Publisher" will directly provide the legacy
Publisher singleton familiar to v1 users.

If the default is not v1 API, then you may switch to v1 API by doing

  import pubsub
  pubsub.setupV1()

This must be done before the first import of Publisher or pub from pubsub.

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

_saveModGlobals = None


def setup(pubsubInitGlobals):
    '''pubsubInitGlobals is pubsub.__init__'s global dict. This gets
    populated with 'pub' and 'Publisher' from core.pubsub1 so that
    importing either will not use the default core.pubsub3 module. '''
    from core import pubsub1
    from core.pubsub1 import Publisher

    pubsubInitGlobals['Publisher'] = Publisher
    pubsubInitGlobals['pub'] = pubsub1

    # for unsetup:
    global _saveModGlobals
    _saveModGlobals = pubsubInitGlobals


def removePubsub1Module(pubsub1Module):
    import sys
    for modName, modObj in sys.modules:
        if modObj is pubsub1Module:
            del sys.modules[modName]
            break


def unsetup():
    '''This should be called by setup* modules in case setupv1 was used.'''
    
    global _saveModGlobals
    if _saveModGlobals is not None:
        pubsub1 = pubsubInitGlobals['pub']
        removePubsub1Module(pubsub1)

        del pubsubInitGlobals['pub']
        del pubsubInitGlobals['Publisher']

        _saveModGlobals = None
