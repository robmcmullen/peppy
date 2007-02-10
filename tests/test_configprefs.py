import os,sys,re

from peppy.configprefs import *
from peppy.configprefs import getHierarchy, getNameHierarchy

from nose.tools import *

class Vehicle(ClassSettingsMixin):
    defaultsettings={'wheels':0,
                     'doors':0,
                     'wings':'no wings on this puppy',
                     'primes':[2,3,5,7],
                     }

class Truck(Vehicle):
    defaultsettings={'wheels':True,
                     'doors':True,
                     'primes':[11,13,17,19],
                     }

class PickupTruck(Truck):
    defaultsettings={'wheels':4,
                     'doors':2,
                     'primes':[23,29],
                     }

class ShortBedPickupTruck(Truck):
    pass

class testClassHierarchy(object):
    def testHierarchy(self):
        GlobalSettings.setDefaults({
            'MenuFrame':{'width':600,
                         'height':500,
                         },
            'Peppy':{'plugins':'hexedit-plugin,python-plugin,fundamental',
                     },
            'MajorMode':{'linenumbers':'True',
                         'wordwrap':'False',
                         },
            'PythonMode':{'wordwrap':'True',
                          },
            })
        vehicle=ShortBedPickupTruck()
        eq_([ShortBedPickupTruck, Truck, Vehicle],
            getHierarchy(vehicle, debug=True))
        eq_(['ShortBedPickupTruck', 'Truck', 'Vehicle'],
            getNameHierarchy(vehicle, debug=True))
        assert vehicle.settings.wheels
        eq_(None, vehicle.settings.mudflaps)
        vehicle.settings.mudflaps=True
        assert vehicle.settings.mudflaps
        assert vehicle.settings.wheels
        vehicle.settings.wheels=6
        eq_(6, vehicle.settings.wheels)
        eq_({'wheels': True,
             'primes': [11, 13, 17, 19],
             'doors': True}, vehicle.settings._getDefaults())
        eq_({'wheels': 6,
             'mudflaps': True}, vehicle.settings._getUser())
        eq_({'mudflaps': True,
             'wheels': 6,
             'primes': [11, 13, 17, 19],
             'doors': True}, vehicle.settings._getAll())
        eq_('no wings on this puppy', vehicle.settings.wings)
        eq_([11, 13, 17, 19], vehicle.settings.primes)
        eq_([11, 13, 17, 19, 11, 13, 17, 19, 2, 3, 5, 7],
            vehicle.settings._getList('primes'))
        eq_([6, True, 0], vehicle.settings._getList('wheels'))
    
class SettingsMixin(object):
    def __init__(self):
        pass

class Plant(SettingsMixin):
    settings=['roots','branches','leaves','fruit']
    roots=True

    def __init__(self):
        self.branches=False
        self.leaves=False
        self.fruit=False
        
class Tree(Plant):
    def __init__(self):
        Plant.__init__(self)
        self.branches=True
        self.leaves=True

class OrangeTree(Tree):
    settings=['company']
    fruit="tangerines"
    
    def __init__(self):
        self.fruit="oranges"
        self.company="Tropicana"


class TestSettingMixin:
    def testPlant(self):
        plant=Tree()
        assert plant.branches
        assert plant.leaves
        assert not plant.fruit
        
    def testOrangeTree(self):
        tree=OrangeTree()
        eq_('oranges',tree.fruit)
        eq_('tangerines',tree.__class__.fruit)
        eq_(['company'],tree.settings)
        eq_('Tropicana',tree.company)
