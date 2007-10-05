import os, sys, re, copy
from cStringIO import StringIO

from peppy.lib.userparams import *

from nose.tools import *

class Vehicle(ClassPrefs):
    default_classprefs = (
        IntParam('wheels', 0),
        IntParam('doors', 0),
        StrParam('wings', 'no wings on this puppy'),
        StrParam('license_plate', ''),
        ReadOnlyParam('primes', [2,3,5,7]),
        )

class Truck(Vehicle):
    default_classprefs = (
        IntParam('wheels', 4),
        IntParam('doors', 4),
        ReadOnlyParam('primes', [11,13,17,19]),
        )

class TrailerMixin(ClassPrefs):
    default_classprefs = (
        StrParam('hitch', 'ball'),
        BoolParam('brakes', True),
        )

class PickupTruck(Truck):
    default_classprefs = (
        IntParam('wheels', 4),
        IntParam('doors', 2),
        ReadOnlyParam('primes', [23,29]),
        )

class ShortBedPickupTruck(Truck):
    pass

class EighteenWheeler(TrailerMixin, Truck):
    default_classprefs = (
        IntParam('wheels', 18),
        StrParam('hitch', '5th wheel'),
        )

def_save = copy.deepcopy(GlobalPrefs.default)
print def_save

user_save = copy.deepcopy(GlobalPrefs.user)
print user_save

class testClassHierarchy(object):
    def setup(self):
        GlobalPrefs.default = copy.deepcopy(def_save)
        GlobalPrefs.user = copy.deepcopy(user_save)

    def testHierarchy(self):
        vehicle=ShortBedPickupTruck()
        eq_([ShortBedPickupTruck, Truck, Vehicle],
            getHierarchy(vehicle, debug=True))
        eq_(['ShortBedPickupTruck', 'Truck', 'Vehicle'],
            getNameHierarchy(vehicle, debug=True))
        assert vehicle.classprefs.wheels
        assert not hasattr(vehicle.classprefs, 'mudflaps')
        vehicle.classprefs.mudflaps=True
        assert vehicle.classprefs.mudflaps
        assert vehicle.classprefs.wheels
        vehicle.classprefs.wheels=6
        eq_(6, vehicle.classprefs.wheels)
        eq_({'wheels': 4,
             'primes': [11, 13, 17, 19],
             'doors': 4}, vehicle.classprefs._getDefaults())
        eq_({'wheels': 6,
             'mudflaps': True}, vehicle.classprefs._getUser())
        eq_({'mudflaps': True,
             'wheels': 6,
             'primes': [11, 13, 17, 19],
             'doors': 4}, vehicle.classprefs._getAll())
        eq_('no wings on this puppy', vehicle.classprefs.wings)
        eq_([11, 13, 17, 19], vehicle.classprefs.primes)
        eq_([11, 13, 17, 19, 11, 13, 17, 19, 2, 3, 5, 7],
            vehicle.classprefs._getList('primes'))
        eq_([6, 4, 0], vehicle.classprefs._getList('wheels'))

    def testGlobalPrefs(self):
        GlobalPrefs.setDefaults({
            'Vehicle':{'wheels': 10,
                       'wings': 'Nope',
                       },
            'Truck':{'wheels': 18,
                     },
            })

        vehicle = Vehicle()
        assert vehicle.classprefs.wheels
        eq_(10, vehicle.classprefs.wheels)
        eq_('Nope', vehicle.classprefs.wings)

        truck = Truck()
        eq_(18, truck.classprefs.wheels)

    def testExistence(self):
        vehicle = Vehicle()
        assert hasattr(vehicle.classprefs, 'wheels')
##        print hasattr(vehicle.classprefs, 'ray_gun')
##        print vehicle.classprefs.ray_gun
        assert not hasattr(vehicle.classprefs, 'ray_gun')
        assert hasattr(vehicle.classprefs, 'license_plate')

    def testMixin(self):
        vehicle = EighteenWheeler()
        print getClassHierarchy(vehicle.__class__, 1)
        eq_(['EighteenWheeler', 'TrailerMixin', 'Truck', 'Vehicle'],
            getNameHierarchy(vehicle, debug=True))
        assert hasattr(vehicle.classprefs, 'wheels')
        assert hasattr(vehicle.classprefs, 'hitch')
        assert hasattr(vehicle.classprefs, 'brakes')

    def testReadConfig(self):
        text = """\
[Vehicle]
wheels = 99

[Truck]
wheels = 1800
"""
        fh = StringIO(text)
        fh.seek(0)
        GlobalPrefs.readConfig(fh)
        
        vehicle = Vehicle()
        assert vehicle.classprefs.wheels
        eq_('99', vehicle.classprefs.wheels)
        eq_('no wings on this puppy', vehicle.classprefs.wings)

        truck = Truck()
        eq_('1800', truck.classprefs.wheels)
        
