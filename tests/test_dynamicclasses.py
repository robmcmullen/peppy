"""
Testing dynamic class creation used in the chatbots plugin to create
an Action for each chatbot present in the nltk_lite toolkit.
"""

import os, sys, re, copy
from cStringIO import StringIO

from nose.tools import *

class Base(object):
    def __init__(self):
        self.blah = 1
        self.override = 0

def init(self):
    super(self.__class__, self).__init__()
    self.override = 2
    self.bar = 'baz'

def func(self):
    return 'howdy'

class testDynamicClassCreation(object):
    def setup(self):
        self.Foo = type('Foo', Base.__mro__, {'__init__': init,
                                              'func': func,
                                              'classattr': 'stuff',
                                              })

    def testType(self):
        eq_('Foo', self.Foo.__name__)
        eq_('stuff', self.Foo.classattr)
        
    def testInstantiation(self):
        c = self.Foo()
        eq_('Foo', c.__class__.__name__)

        # The tuples don't compare equal even though a debug print
        # shows that they are the same.  Check the names instead.
        #eq_((self.Foo, Base, object), c.__class__.__mro__)
        eq_(['Foo', 'Base', 'object'], [k.__name__ for k in c.__class__.__mro__])
        eq_(1, c.blah)
        eq_(2, c.override)
        eq_('baz', c.bar)
        eq_('howdy', c.func())

