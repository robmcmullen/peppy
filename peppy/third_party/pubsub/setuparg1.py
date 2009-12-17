'''
Import this file before the first 'from pubsub import pub' statement
to make pubsub use the *arg1* messaging protocol. Note that an application
can only use one protocol. 

:copyright: Copyright 2006-2009 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

import pubsubconf
pubsubconf.setMsgProtocol('arg1')

import setupv1
setupv1.unsetup()
