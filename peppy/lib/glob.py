# Copyright (C) 2006 Jan Hudec

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Tools for converting globs to regular expressions.

This module provides functions for converting shell-like globs to regular
expressions. See translate function for implemented glob semantics.
"""


import os
import re


class Replacer(object):
    """Do a multiple-pattern substitution.

    The patterns and substitutions are combined into one, so the result of
    one replacement is never substituted again. Add the patterns and
    replacements via the add method and then call the object. The patterns
    must not contain capturing groups.
    """

    _expand = re.compile(ur'\\&')

    def __init__(self, source=None):
        self._pat = None
        if source is not None:
            self._pats = list(source._pats)
            self._funs = list(source._funs)
        else:
            self._pats = []
            self._funs = []

    def add(self, pat, fun):
        r"""Add a pattern and replacement.

        The pattern must not contain capturing groups.
        The replacement might be either a string template in which \& will be
        replaced with the match, or a function that will get the matching text as
        argument. It does not get match object, because capturing is forbidden
        anyway.
        """
        self._pat = None
        self._pats.append(pat)
        self._funs.append(fun)

    def add_replacer(self, replacer):
        r"""Add all patterns from another replacer.

        All patterns and replacements from replacer are appended to the ones
        already defined.
        """
        self._pat = None
        self._pats.extend(replacer._pats)
        self._funs.extend(replacer._funs)

    def __call__(self, text):
        if self._pat is None:
            self._pat = re.compile(
                    u'|'.join([u'(%s)' % p for p in self._pats]),
                    re.UNICODE)
        return self._pat.sub(self._do_sub, text)

    def _do_sub(self, m):
        #print("match = %s, lastindex = %d" % (m.group(0), m.lastindex))
        fun = self._funs[m.lastindex - 1]
        if hasattr(fun, '__call__'):
            return fun(m.group(0))
        else:
            return self._expand.sub(m.group(0), fun)


def _badvalue(m):
    raise ValueError, m

_unescape_string = Replacer()
_unescape_string.add(ur'\\U[0-9A-Fa-f]{8}', lambda m: unichr(int(m[2:], 16)))
_unescape_string.add(ur'\\u[0-9A-Fa-f]{4}', lambda m: unichr(int(m[2:], 16)))
_unescape_string.add(ur'\\x[0-9A-Fa-f]{2}', lambda m: unichr(int(m[2:], 16)))
_unescape_string.add(ur'\\[^\w]', lambda m: m[1:])
_unescape_string.add(ur'\\a', u'\a')
_unescape_string.add(ur'\\f', u'\f')
_unescape_string.add(ur'\\n', u'\n')
_unescape_string.add(ur'\\r', u'\r')
_unescape_string.add(ur'\\t', u'\t')
_unescape_string.add(ur'\\v', u'\v')


_unescape_glob = Replacer(_unescape_string)
_unescape_glob.__doc__ = '''Get a signle match for a glob.

If the regular expression does not contain any special characters, returns
the string that matches it. This differs from the input if it contains
character escapes. If the regular expression contains special characters,
throws a ValueError
'''
_unescape_glob.add(ur'[][*?\\]', _badvalue)
_unescape_glob.add(ur'^RE:', _badvalue)


_strip_escapes = Replacer(_unescape_string)
_strip_escapes.__doc__ = '''Delete all globbing characters from a glob.

Length of such string is used for comparing glob match specificity.
'''
_strip_escapes.add(ur'\[\^?\]?(?:[^][]|\[:[^]]+:\])+\]', u'')
_strip_escapes.add(ur'[*?]', u'')
_strip_escapes.add(ur'\\.', u'')


_sub_named = Replacer()
_sub_named.add(ur'\[:digit:\]', ur'\d')
_sub_named.add(ur'\[:space:\]', ur'\s')
_sub_named.add(ur'\[:alnum:\]', ur'\w')
_sub_named.add(ur'\[:ascii:\]', ur'\0-\x7f')
_sub_named.add(ur'\[:blank:\]', ur' \t')
_sub_named.add(ur'\[:cntrl:\]', ur'\0-\x1f\x7f-\x9f')
# but python regular expression engine does not provide their equivalents.


def _sub_group(m):
    if m[1] == u'!':
        m[1] = u'^'
    return u'[' + _sub_named(m[1:-1]) + u']'


_sub_shell = Replacer()
#_sub_shell.add(ur'(?:(?<=/)|^)(?:\.?/)+', u'') # canonicalize
#_sub_shell.add(ur'\\.', ur'\&') # keep anything backslashed
_sub_shell.add(ur'[][|^$+]', ur'\\&') # escape specials
#_sub_shell.add(ur'(?:(?<=/)|^)\*\*\*(?:/|$)', ur'(?:[^/]+(?:/|$))*') # ***
#_sub_shell.add(ur'(?:(?<=/)|^)\*\*(?:/|$)', ur'(?:[^./][^/]*(?:/|$))*') # **
#_sub_shell.add(ur'(?:(?<=/)|^)\*\.', ur'(?:[^./][^/]*)\.') # *. after /|^
#_sub_shell.add(ur'(?:(?<=/)|^)\*', ur'(?:[^./][^/]*)?') # * after /|^
_sub_shell.add(ur'\*', ur'\(.*\)') # * elsewhere
#_sub_shell.add(ur'(?:(?<=/)|^)\?', ur'[^./]') # ? after /|^
_sub_shell.add(ur'\?', ur'\(.\)') # ? elsewhere
#_sub_shell.add(ur'\[\^?\]?(?:[^][]|\[:[^]]+:\])+\]', _sub_group) # char group


def SHELL(pat, sep):
    """Convert globs to regexp using 'shell-style' interpretation.

    Shell-style globs implement *, ?, [] character groups (both ! and
    ^ negate), named character classes [:digit:], [:space:], [:alnum:],
    [:ascii:], [:blank:], [:cntrl:] (use /inside/ []), zsh-style **, ***
    which includes hidden directories and escapes regular expression special
    characters.

    If a pattern starts with RE:, the rest is considered to be regular
    expression.

    During conversion the regexp is canonicalized and must be matched against
    canonical path. The path must NOT start with '/' and must not contain '.'
    components nor multiple '/'es.

    This is intended for use the style argument to translate and related
    functions.
    """
    if not pat.startswith('RE:'):
        pat = sep(pat)
    return _sub_shell(pat)


def POSIX(pat):
    """Canonicalize glob using / as directory separator.

    This is intended for passing in the sep argument to translate and
    related functions.
    """
    return pat


# Default style so it's consisten between all funcs that take that argument.
_default_style = SHELL


def translate(pat, style=_default_style, sep=POSIX):
    r"""Convert a glob to regular expression.

    The style argument is the actual translator to be used. Translators
    defined are SHELL and FNMATCH. See their respective documentation for
    exact interpretation of globbing chars. Default translator is SHELL.
    
    Pattern is returned as string.
    """
    regex = style(pat, sep)
    #if '\(.*\)' in regex:
    #    # If there's a pattern, limit the search to the end of a word
    #    regex += "[ $]"
    if pat.startswith('*'):
        regex = "[^ ]" + regex
    return regex

def compile(pat, style=_default_style, sep=POSIX):
    """Convert a unix glob to regular expression and compile it.

    This converts a glob to regex via translate and compiles the regex. See
    translate for glob semantics.
    """
    return re.compile(translate(pat, style, sep), re.UNICODE)


class TestShellGlobs(object):
    def failUnless(self, expr, msg):
        import nose.tools
        nose.tools.assert_true(expr, msg)

    def failIf(self, expr, msg):
        import nose.tools
        nose.tools.assert_false(expr, msg)

    def assertMatch(self, glob, positive, negative):
        rx = compile(anchor_glob(glob), style=SHELL)
        for name in positive:
            self.failUnless(rx.match(name), repr(
                        u'name "%s" does not match glob "%s" (rx="%s")' %
                        (name, glob, rx.pattern)))
        for name in negative:
            self.failIf(rx.match(name), repr(
                        u'name "%s" does match glob "%s" (rx="%s")' %
                        (name, glob, rx.pattern)))


    def test_char_groups(self):
        # The definition of digit this uses includes arabic digits from
        # non-latin scripts (arabic, indic, etc.) and subscript/superscript
        # digits, but neither roman numerals nor vulgar fractions.
        self.assertMatch(u'[[:digit:]]', [u'0', u'5', u'\u0663', u'\u06f9',
                u'\u0f21', u'\xb9'], [u'T', u'q', u' ', u'\u8336'])

        self.assertMatch(u'[[:space:]]', [u' ', u'\t', u'\n', u'\xa0',
                u'\u2000', u'\u2002'], [u'a', u'-', u'\u8336'])
        self.assertMatch(u'[^[:space:]]', [u'a', u'-', u'\u8336'], [u' ',
                u'\t', u'\n', u'\xa0', u'\u2000', u'\u2002'])

        self.assertMatch(u'[[:alnum:]]', [u'a', u'Z', u'\u017e', u'\u8336'],
                [u':', u'-', u'\u25cf'])
        self.assertMatch(u'[^[:alnum:]]', [u':', u'-', u'\u25cf'], [])

        self.assertMatch(u'[[:ascii:]]', [u'a', u'Q', u'^'], [u'\xcc',
                u'\u8336'])
        self.assertMatch(u'[^[:ascii:]]', [u'\xcc', u'\u8336'], [u'a', u'Q',
                u'^'])

        self.assertMatch(u'[[:blank:]]', [u'\t'], [u'x', u'y', u'z'])
        self.assertMatch(u'[^[:blank:]]', [u'x', u'y', u'z'], [u'\t'])

        self.assertMatch(u'[[:cntrl:]]', [u'\b', u'\t', '\x7f'], [u'a', u'Q',
                u'\u8336'])

        self.assertMatch(u'[a-z]', [u'a', u'q', u'f'], [u'A', u'Q', u'F'])
        self.assertMatch(u'[^a-z]', [u'A', u'Q', u'F'], [u'a', u'q', u'f'])

        self.assertMatch(ur'[\x20-\x30\u8336]', [u'\040', u'\044', u'\u8336'],
                [])
        self.assertMatch(ur'[^\x20-\x30\u8336]', [], [u'\040', u'\044',
                u'\u8336'])

    def test_question_mark(self):
        self.assertMatch(u'?foo', [u'xfoo', u'bar/xfoo', u'bar/\u8336foo'],
                [u'.foo', u'bar/.foo', u'bar/foo', u'foo'])

        self.assertMatch(u'foo?bar', [u'fooxbar', u'foo.bar', u'foo\u8336bar',
                u'qyzzy/foo.bar'], [u'foo/bar'])

        self.assertMatch(u'foo/?bar', [u'foo/xbar'], [u'foo/.bar', u'foo/bar',
                u'bar/foo/xbar'])

    def test_asterisk(self):
        self.assertMatch(u'*.x', [u'foo/bar/baz.x', u'\u8336/Q.x'],
                [u'.foo.x', u'bar/.foo.x', u'.x'])

        self.assertMatch(u'x*x', [u'xx', u'x.x', u'x\u8336..x',
                u'\u8336/x.x'], [u'x/x', u'bar/x/bar/x', u'bax/abaxab'])

        self.assertMatch(u'*/*x', [u'\u8336/x', u'foo/bax', u'x/a.x'],
                [u'.foo/x', u'\u8336/.x', u'foo/.q.x', u'foo/bar/bax'])

    def test_end_anchor(self):
        self.assertMatch(u'*.333', [u'foo.333'], [])
        self.assertMatch(u'*.3', [], [u'foo.333'])

if __name__ == "__main__":
    print translate("blah*blah")
    print translate("blah*eua??blah")
    print translate("bl+a$^[]h*blah")
    print translate("bl(ah*eua??blah")
    print translate("bl\\(")
    print translate("*blah*")
    