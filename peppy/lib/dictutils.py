# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dictionary utilities

"""
import time

class TimeExpiringDict(dict):
    """Dictionary where each value expires after a set amount of time
    
    The delay used as the default elapsed expiration time is a parameter of the
    entire dictionary, although the expiration time can optionally be set on a
    per-element basis.
    
    """

    def __init__(self, arg1=None, arg2=None, **kwargs):
        """Constructor for the TimeExpiringDict
        
        Can take an integer or floating point argument to set the expiration
        delay for each new element.  The expiration delay is the number
        of seconds added to the current time for each element added to the
        dictionary.  If no expiration delay is set, the elements in the dict
        never expire, essentially mimicking a regular dict.  Individual
        expiration times may be set after adding a key to the dictionary.
        
        @param arg1: an iterable to be used to pre-populate the dict, or an
        integer or floating point value setting the expiration delay.  The
        delay is specified in seconds.
        
        @param arg2: either an iterable or a number (same as arg1), provided so
        that both an initial iterable and a delay may be set.
        
        @param kwargs: initial keyword/value pairs to pre-populate the
        dictionary
        """
        # Initialize the dict
        dict.__init__(self)
        self._elapsed_time = -1
        self._expires_at = {}

        for arg in [arg1, arg2]:
            if isinstance(arg, int) or isinstance(arg, float):
                self._elapsed_time = arg
            elif isinstance(arg, dict) or not hasattr(arg, 'items'):
                self.update(arg)
            elif arg is not None:
                for k, v in arg.items():
                    self[k] = v
        if len(kwargs):
            self.update(kwargs)
    
    def _show_state(self):
        print("dict: %s\ntimes: %s" % (self, self._expires_at))
    
    def __iter__(self):
        current_time = time.time()
        for key, expires_at in self._expires_at.iteritems():
            if current_time < expires_at:
                yield key

    def __setitem__(self, key, value):
        if self._elapsed_time > 0:
            self._expires_at[key] = time.time() + self._elapsed_time
        else:
            # Set the time to beyond the end of the universe.  Probably won't
            # fail.
            self._expires_at[key] = 1.0e20
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        del self._expires_at[key]
        dict.__delitem__(self, key)

    def __contains__(self, key):
        if key in self._expires_at:
            current_time = time.time()
            expires_at = self._expires_at[key]
            if current_time < expires_at:
                return True
            del self[key]

    def iteritems(self):
        current_time = time.time()
        for key, expires_at in self._expires_at.iteritems():
            if current_time < expires_at:
                yield key, self[key]

    def items(self):
        return list(self.iteritems())

    iterkeys = __iter__

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        current_time = time.time()
        for key, expires_at in self._expires_at.iteritems():
            if current_time < expires_at:
                yield self[key]

    def values(self):
        return list(self.itervalues())

    def pop(self, key, *default):
        if key in self._expires_at:
            current_time = time.time()
            expires_at = self._expires_at[key]
            if current_time < expires_at:
                value = self[key]
                del self[key]
                return value
        if len(default) > 0:
            return default[0]
        raise KeyError

    def popitem(self):
        current_time = time.time()
        while True:
            # Raises KeyError when out of valid items.  Note that this also
            # cleans up any expired items as a nice side effect
            key, expires_at = self._expires_at.popitem()
            if current_time < expires_at:
                # Can't use self.pop because it will fail since the
                # _expires_at element has already been removed from the
                # popitem call above
                value = dict.pop(self, key)
                return key, value

    def setdefault(self, key, default=None):
        if key in self._expires_at.iterkeys():
            current_time = time.time()
            expires_at = self._expires_at[key]
            if current_time < expires_at:
                return self[key]
        self[key] = default
        return default

    def update(self, other=None, **kwargs):
        # Make progressively weaker assumptions about "other"
        if other is None:
            pass
        elif hasattr(other, 'iteritems'):  # iteritems saves memory and lookups
            for k, v in other.iteritems():
                self[k] = v
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self[k] = other[k]
        else:
            for k, v in other:
                self[k] = v
        if len(kwargs):
            for k, v in kwargs.iteritems():
                self[k] = v
    
    def expire_at(self, key, when):
        # make sure the element exists before allowing the change in expiration
        # time.  Need to avoid the case where the key has expired but hasn't
        # been cleaned out of the dict yet.  Calling __contains__ will remove
        # the item, so this check will force the presence of the key.
        if key in self:
            self._expires_at[key] = when
        else:
            raise KeyError



if __name__ == "__main__":
    # Dict testcase code borrowed from the Python source code
    import unittest
    import sys, UserDict, cStringIO

    class DictTest(unittest.TestCase):
        def test_bool(self):
            self.assert_(not TimeExpiringDict())
            self.assert_({1: 2})
            self.assert_(bool(TimeExpiringDict()) is False)
            self.assert_(bool({1: 2}) is True)

        def test_keys(self):
            d = TimeExpiringDict()
            self.assertEqual(d.keys(), [])
            d = {'a': 1, 'b': 2}
            k = d.keys()
            self.assert_(d.has_key('a'))
            self.assert_(d.has_key('b'))

            self.assertRaises(TypeError, d.keys, None)

        def test_values(self):
            d = TimeExpiringDict()
            self.assertEqual(d.values(), [])
            d = {1:2}
            self.assertEqual(d.values(), [2])

            self.assertRaises(TypeError, d.values, None)

        def test_items(self):
            d = TimeExpiringDict()
            self.assertEqual(d.items(), [])

            d = {1:2}
            self.assertEqual(d.items(), [(1, 2)])

            self.assertRaises(TypeError, d.items, None)

        def test_has_key(self):
            d = TimeExpiringDict()
            self.assert_(not d.has_key('a'))
            d = TimeExpiringDict({'a': 1, 'b': 2})
            k = d.keys()
            k.sort()
            self.assertEqual(k, ['a', 'b'])

            self.assertRaises(TypeError, d.has_key)

        def test_contains(self):
            d = TimeExpiringDict()
            self.assert_(not ('a' in d))
            self.assert_('a' not in d)
            d = TimeExpiringDict({'a': 1, 'b': 2})
            self.assert_('a' in d)
            self.assert_('b' in d)
            self.assert_('c' not in d)

            self.assertRaises(TypeError, d.__contains__)

        def test_len(self):
            d = TimeExpiringDict()
            self.assertEqual(len(d), 0)
            d = {'a': 1, 'b': 2}
            self.assertEqual(len(d), 2)

        def test_getitem(self):
            d = {'a': 1, 'b': 2}
            self.assertEqual(d['a'], 1)
            self.assertEqual(d['b'], 2)
            d['c'] = 3
            d['a'] = 4
            self.assertEqual(d['c'], 3)
            self.assertEqual(d['a'], 4)
            del d['b']
            self.assertEqual(d, {'a': 4, 'c': 3})

            self.assertRaises(TypeError, d.__getitem__)

            class BadEq(object):
                def __eq__(self, other):
                    raise Exc()

            d = TimeExpiringDict()
            d[BadEq()] = 42
            self.assertRaises(KeyError, d.__getitem__, 23)

            class Exc(Exception): pass

            class BadHash(object):
                fail = False
                def __hash__(self):
                    if self.fail:
                        raise Exc()
                    else:
                        return 42

            x = BadHash()
            d[x] = 42
            x.fail = True
            self.assertRaises(Exc, d.__getitem__, x)

        def test_clear(self):
            d = {1:1, 2:2, 3:3}
            d.clear()
            self.assertEqual(d, TimeExpiringDict())

            self.assertRaises(TypeError, d.clear, None)

        def test_update(self):
            d = TimeExpiringDict()
            d.update({1:100})
            d.update({2:20})
            d.update({1:1, 2:2, 3:3})
            self.assertEqual(d, {1:1, 2:2, 3:3})

            d.update()
            self.assertEqual(d, {1:1, 2:2, 3:3})

            class SimpleUserDict:
                def __init__(self):
                    self.d = {1:1, 2:2, 3:3}
                def keys(self):
                    return self.d.keys()
                def __getitem__(self, i):
                    return self.d[i]
            d.clear()
            d.update(SimpleUserDict())
            self.assertEqual(d, {1:1, 2:2, 3:3})

            class Exc(Exception): pass

            d.clear()
            class FailingUserDict:
                def keys(self):
                    raise Exc
            self.assertRaises(Exc, d.update, FailingUserDict())

            class FailingUserDict:
                def keys(self):
                    class BogonIter:
                        def __init__(self):
                            self.i = 1
                        def __iter__(self):
                            return self
                        def next(self):
                            if self.i:
                                self.i = 0
                                return 'a'
                            raise Exc
                    return BogonIter()
                def __getitem__(self, key):
                    return key
            self.assertRaises(Exc, d.update, FailingUserDict())

            class FailingUserDict:
                def keys(self):
                    class BogonIter:
                        def __init__(self):
                            self.i = ord('a')
                        def __iter__(self):
                            return self
                        def next(self):
                            if self.i <= ord('z'):
                                rtn = chr(self.i)
                                self.i += 1
                                return rtn
                            raise StopIteration
                    return BogonIter()
                def __getitem__(self, key):
                    raise Exc
            self.assertRaises(Exc, d.update, FailingUserDict())

            class badseq(object):
                def __iter__(self):
                    return self
                def next(self):
                    raise Exc()

            self.assertRaises(Exc, TimeExpiringDict().update, badseq())

            self.assertRaises(ValueError, TimeExpiringDict().update, [(1, 2, 3)])

        def test_fromkeys(self):
            self.assertEqual(dict.fromkeys('abc'), {'a':None, 'b':None, 'c':None})
            d = TimeExpiringDict()
            self.assert_(not(d.fromkeys('abc') is d))
            self.assertEqual(d.fromkeys('abc'), {'a':None, 'b':None, 'c':None})
            self.assertEqual(d.fromkeys((4,5),0), {4:0, 5:0})
            self.assertEqual(d.fromkeys([]), TimeExpiringDict())
            def g():
                yield 1
            self.assertEqual(d.fromkeys(g()), {1:None})
            self.assertRaises(TypeError, TimeExpiringDict().fromkeys, 3)
            class dictlike(dict): pass
            self.assertEqual(dictlike.fromkeys('a'), {'a':None})
            self.assertEqual(dictlike().fromkeys('a'), {'a':None})
            self.assert_(type(dictlike.fromkeys('a')) is dictlike)
            self.assert_(type(dictlike().fromkeys('a')) is dictlike)
            class mydict(dict):
                def __new__(cls):
                    return UserDict.UserDict()
            ud = mydict.fromkeys('ab')
            self.assertEqual(ud, {'a':None, 'b':None})
            self.assert_(isinstance(ud, UserDict.UserDict))
            self.assertRaises(TypeError, dict.fromkeys)

            class Exc(Exception): pass

            class baddict1(dict):
                def __init__(self):
                    raise Exc()

            self.assertRaises(Exc, baddict1.fromkeys, [1])

            class BadSeq(object):
                def __iter__(self):
                    return self
                def next(self):
                    raise Exc()

            self.assertRaises(Exc, dict.fromkeys, BadSeq())

            class baddict2(dict):
                def __setitem__(self, key, value):
                    raise Exc()

            self.assertRaises(Exc, baddict2.fromkeys, [1])

        def test_copy(self):
            d = TimeExpiringDict({1:1, 2:2, 3:3})
            self.assertEqual(d.copy(), TimeExpiringDict({1:1, 2:2, 3:3}))
            self.assertEqual(TimeExpiringDict().copy(), TimeExpiringDict())
            self.assertRaises(TypeError, d.copy, None)

        def test_get(self):
            d = TimeExpiringDict()
            self.assert_(d.get('c') is None)
            self.assertEqual(d.get('c', 3), 3)
            d = {'a' : 1, 'b' : 2}
            self.assert_(d.get('c') is None)
            self.assertEqual(d.get('c', 3), 3)
            self.assertEqual(d.get('a'), 1)
            self.assertEqual(d.get('a', 3), 1)
            self.assertRaises(TypeError, d.get)
            self.assertRaises(TypeError, d.get, None, None, None)

        def test_setdefault(self):
            # dict.setdefault()
            d = TimeExpiringDict()
            self.assert_(d.setdefault('key0') is None)
            d.setdefault('key0', [])
            self.assert_(d.setdefault('key0') is None)
            d.setdefault('key', []).append(3)
            self.assertEqual(d['key'][0], 3)
            d.setdefault('key', []).append(4)
            self.assertEqual(len(d['key']), 2)
            self.assertRaises(TypeError, d.setdefault)

            class Exc(Exception): pass

            class BadHash(object):
                fail = False
                def __hash__(self):
                    if self.fail:
                        raise Exc()
                    else:
                        return 42

            x = BadHash()
            d[x] = 42
            x.fail = True
            self.assertRaises(Exc, d.setdefault, x, [])

        def test_popitem(self):
            # dict.popitem()
            for copymode in -1, +1:
                # -1: b has same structure as a
                # +1: b is a.copy()
                for log2size in range(12):
                    size = 2**log2size
                    a = TimeExpiringDict()
                    b = TimeExpiringDict()
                    for i in range(size):
                        a[repr(i)] = i
                        if copymode < 0:
                            b[repr(i)] = i
                    if copymode > 0:
                        b = a.copy()
                    for i in range(size):
                        ka, va = ta = a.popitem()
                        self.assertEqual(va, int(ka))
                        kb, vb = tb = b.popitem()
                        self.assertEqual(vb, int(kb))
                        self.assert_(not(copymode < 0 and ta != tb))
                    self.assert_(not a)
                    self.assert_(not b)

            d = TimeExpiringDict()
            self.assertRaises(KeyError, d.popitem)

        def test_pop(self):
            # Tests for pop with specified key
            d = TimeExpiringDict()
            k, v = 'abc', 'def'
            d[k] = v
            self.assertRaises(KeyError, d.pop, 'ghi')

            self.assertEqual(d.pop(k), v)
            self.assertEqual(len(d), 0)

            self.assertRaises(KeyError, d.pop, k)

            # verify longs/ints get same value when key > 32 bits (for 64-bit archs)
            # see SF bug #689659
            x = 4503599627370496L
            y = 4503599627370496
            h = TimeExpiringDict({x: 'anything', y: 'something else'})
            self.assertEqual(h[x], h[y])

            self.assertEqual(d.pop(k, v), v)
            d[k] = v
            self.assertEqual(d.pop(k, 1), v)

            self.assertRaises(TypeError, d.pop)

            class Exc(Exception): pass

            class BadHash(object):
                fail = False
                def __hash__(self):
                    if self.fail:
                        raise Exc()
                    else:
                        return 42

            x = BadHash()
            d[x] = 42
            x.fail = True
            self.assertRaises(Exc, d.pop, x)

        def test_mutatingiteration(self):
            d = TimeExpiringDict()
            d[1] = 1
            try:
                for i in d:
                    d[i+1] = 1
            except RuntimeError:
                pass
            else:
                self.fail("changing dict size during iteration doesn't raise Error")

        def test_repr(self):
            d = TimeExpiringDict()
            self.assertEqual(repr(d), '{}')
            d[1] = 2
            self.assertEqual(repr(d), '{1: 2}')
            d = TimeExpiringDict()
            d[1] = d
            self.assertEqual(repr(d), '{1: {...}}')

            class Exc(Exception): pass

            class BadRepr(object):
                def __repr__(self):
                    raise Exc()

            d = TimeExpiringDict({1: BadRepr()})
            self.assertRaises(Exc, repr, d)

        def test_le(self):
            self.assert_(not (TimeExpiringDict() < TimeExpiringDict()))
            self.assert_(not ({1: 2} < {1L: 2L}))

            class Exc(Exception): pass

            class BadCmp(object):
                def __eq__(self, other):
                    raise Exc()

            d1 = TimeExpiringDict({BadCmp(): 1})
            d2 = TimeExpiringDict({1: 1})
            try:
                d1 < d2
            except Exc:
                pass
            else:
                self.fail("< didn't raise Exc")

        def test_missing(self):
            # Make sure dict doesn't have a __missing__ method
            self.assertEqual(hasattr(dict, "__missing__"), False)
            self.assertEqual(hasattr(TimeExpiringDict(), "__missing__"), False)
            # Test several cases:
            # (D) subclass defines __missing__ method returning a value
            # (E) subclass defines __missing__ method raising RuntimeError
            # (F) subclass sets __missing__ instance variable (no effect)
            # (G) subclass doesn't define __missing__ at a all
            class D(TimeExpiringDict):
                def __missing__(self, key):
                    return 42
            d = D({1: 2, 3: 4})
            self.assertEqual(d[1], 2)
            self.assertEqual(d[3], 4)
            self.assert_(2 not in d)
            self.assert_(2 not in d.keys())
            self.assertEqual(d[2], 42)
            class E(TimeExpiringDict):
                def __missing__(self, key):
                    raise RuntimeError(key)
            e = E()
            try:
                e[42]
            except RuntimeError, err:
                self.assertEqual(err.args, (42,))
            else:
                self.fail("e[42] didn't raise RuntimeError")
            class F(TimeExpiringDict):
                def __init__(self):
                    # An instance variable __missing__ should have no effect
                    self.__missing__ = lambda key: None
            f = F()
            try:
                f[42]
            except KeyError, err:
                self.assertEqual(err.args, (42,))
            else:
                self.fail("f[42] didn't raise KeyError")
            class G(dict):
                pass
            g = G()
            try:
                g[42]
            except KeyError, err:
                self.assertEqual(err.args, (42,))
            else:
                self.fail("g[42] didn't raise KeyError")

        def test_tuple_keyerror(self):
            # SF #1576657
            d = TimeExpiringDict()
            try:
                d[(1,)]
            except KeyError, e:
                self.assertEqual(e.args, ((1,),))
            else:
                self.fail("missing KeyError")
    
    class TimedDictTest(unittest.TestCase):
        def test_expire(self):
            d = TimeExpiringDict(.3, {'a': 1, 'b': 2, 'c': 3})
            self.assert_('a' in d)
            self.assert_('b' in d)
            self.assert_('c' in d)
            self.assert_('d' not in d)
            time.sleep(.2)
            self.assertEqual(d['a'], 1)
            d['a'] = 3
            d.expire_at('c', time.time())
            self.assert_('b' in d)
            self.assert_('c' not in d)
            time.sleep(.2)
            self.assertEqual(d['a'], 3)
            self.assert_('b' not in d)
            time.sleep(.2)
            self.assert_('a' not in d)


    unittest.main()
