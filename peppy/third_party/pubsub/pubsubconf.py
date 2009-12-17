"""
Allows user to configure pubsub API. Most important:

- setMsgProtocol(): select messaging protocol (by name)

- transitionV1ToV3(): temporarily change some
  policies to support a systematic migration (transition) of an
  application from arg1 messaging protocol to kwargs protocol.

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.
     
"""

def useWxStyleMessaging():
    '''Alias for "setMsgProtocol('arg1')". '''
    setMsgProtocol('arg1')


def setMsgProtocol(protocolName):
    '''Change the messaging protocol used by pubsub version 3. When not
    called, the protocol is 'kwargs'. Allowed values for protocolName are
    'kwargs' and 'arg1'. The arg1 protocol is the one originally supported 
    by pubsub prior to v3 API, ie by the original wxPython pubsub. '''
    if protocolName not in ('arg1', 'kwargs'):
        raise NotImplementedError('The protocol "%s" is not supported' % protocolName)

    import core
    core.setMsgProtocol(protocolName)


def transitionV1ToV3(commonName, stage=1):
    '''Use this to help with migrating an application that uses the arg1
    messaging protocol to use the kwargs protocol. pubsub
    version 1 to use version 3 instead, to go from protocol 'arg1' to
    'kwargs'. Ie you want to change an application that has been using
    setMsgProtocol('arg1') into one that uses the more robust 'kwargs'
    protocol.

    This function supports a two-stage process:
    1. make all listeners use the same argument name (commonName);
    2. make all senders use the kwargs protocol.

    After the second stage is tested and debugged, this function call
    can be removed, and all reference to the .data attribute of the message
    object received can be removed in all listeners, allowing the
    application to run in the default messaging protocol (kwargs) used by
    pubsub version 3. 
    '''
    import core
    
    if stage <= 1:
        core.setMsgProtocol('arg1')

    core.setMsgDataArgName(stage, commonName)

    