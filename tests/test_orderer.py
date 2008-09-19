import os,sys,re

from peppy.lib.orderer import *
from peppy.menu import *

from nose.tools import *

class TestOrderer:
    def testMenu(self):
        menus=[Menu('File').first(),
               Menu('Edit').first().before('Major Mode'),
               Menu('Help').last(),
               Menu('View').before('Major Mode'),
               Menu('Zippy').after('Minor Mode'),
               Menu('Stuff').after('Zippy'),
               Menu('Buffers').before('Major Mode').after('View'),
               Menu('Python').after('Major Mode').before('Minor Mode'),
               Menu('Functions').after('Minor Mode'),
               Menu('Major Mode').before('Minor Mode'),
               Menu('Minor Mode').after('Major Mode'),
               ]
        orderer=Orderer(menus)
        order=orderer.sort()
        eq_(11,len(order))
        eq_('File',order[0].name)
        eq_('Edit',order[1].name)
        eq_('Help',order[-1].name)
        eq_(['File', 'Edit', 'View', 'Buffers', 'Major Mode', 'Python', 'Minor Mode', 'Zippy', 'Stuff', 'Functions', 'Help'],[a.name for a in order])
