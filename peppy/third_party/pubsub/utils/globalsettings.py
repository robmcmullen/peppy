'''

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

_packageImported = False


def isPackageImported():
    '''Can be used to determine if pubsub package has been imported
    by your application (or by any modules imported by it). '''
    return _packageImported


def setPackageImported():
    '''Called automatically when pubsub package is important.
    You may use isPackageImported() to test. '''
    global _packageImported
    _packageImported = True

