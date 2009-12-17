'''
Publisher-subscribe package.

This package provides the pub and utils modules and the deprecated
setupV1() function:

- pub: access point for core pubsub functionality such as subscribing
  listeners, sending messages, setting notification handlers, etc.
- utils: various utility functions and classes that may be of use.
- setupV1(): force pubsub to use v1 API.

For instance::

    from pubsub import pub
    pub.sendMessage('topic', data1=123)

    from pubsub import utils
    utils....

NOTE: pub, utils and setupV1 are the only pubsub objects that can
be used in v3 of the API. In v1, the Publisher singleton is
also available.

NOTE: the old style ``Publisher().sendMessage...`` is only supported in
v1 of the API.

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

Last known commit:
- $Date: 2009-12-14 23:10:59 -0800 (Mon, 14 Dec 2009) $
- $Revision: 238 $

'''


__all__ = [
    'pub', 'Publisher',
    'pubsubconf', 'setupkwargs', 'setuparg1', 'setupV1',
    'utils'
    ]


def setupV1():
    '''Manually setup pubsub to use the legacy v1 API of pubsub. This
    should be useful only to wxPython users. Example::

        from wx.lib import pubsub
        pubsub.setupV1()
        from wx.lib.pubsub import Publisher
        Publisher().sendMessage(...) # example

    .. warning: This function is deprecated:
       upgrade your application to make use of the 'arg1' messaging
       protocol of the v3 API, which is almost identical to v1 but with
       better notification and exception handling capabilities. See the
       pubsub.setuparg1 module.'''

    import setupv1 as setupexec
    setupexec.setup( globals() )


def tryAutoSetupV1():
    '''If a module called 'autosetuppubsubv1' is found on the module
    search path, it means pubsub must default to using v1 API
    "out of the box". '''
    try:
        # if autosetupv1 is importable, then it means we should
        # automatically setup for version 1 API
        import autosetuppubsubv1
        setupV1()

    except ImportError:
        pass


tryAutoSetupV1()
