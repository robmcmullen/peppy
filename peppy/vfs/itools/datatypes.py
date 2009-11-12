# -*- coding: UTF-8 -*-
# Copyright (C) 2004-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


class DataType(object):

    default = None


    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])


    @staticmethod
    def decode(data):
        """Deserializes the given byte string to a value with a type."""
        raise NotImplementedError


    @staticmethod
    def encode(value):
        """Serializes the given value to a byte string."""
        raise NotImplementedError


    @staticmethod
    def is_valid(value):
        """Checks whether the given value is valid.

        For example, for a natural number the value will be an integer,
        and this method will check that it is not a negative number.
        """
        return True

import re, time, datetime, calendar, decimal, mimetypes
from copy import deepcopy

# Import from itools
from peppy.vfs.itools.uri import get_reference
#from itools.i18n import has_language
def has_language(stuff):
    return False
#from base import DataType



def is_datatype(type, base_type):
    """
    Returns True if 'type' is of 'base_type'.
    """
    try:
        if issubclass(type, base_type):
            return True
    except TypeError:
        pass
    if isinstance(type, base_type):
        return True
    return False



class Integer(DataType):

    @staticmethod
    def decode(value):
        if not value:
            return None
        return int(value)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return str(value)



class Decimal(DataType):

    @staticmethod
    def decode(value):
        if not value:
            return None
        return decimal.Decimal(value)

    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return str(value)



class Unicode(DataType):

    default = u''


    @staticmethod
    def decode(value, encoding='UTF-8'):
        return unicode(value, encoding)


    @staticmethod
    def encode(value, encoding='UTF-8'):
        return value.encode(encoding)



class String(DataType):

    @staticmethod
    def decode(value):
        return value


    @staticmethod
    def encode(value):
        return value



class Boolean(DataType):

    default = False

    @staticmethod
    def decode(value):
        return bool(int(value))


    @staticmethod
    def encode(value):
        if value is True:
            return '1'
        elif value is False:
            return '0'
        else:
            raise ValueError, 'value is not a boolean'



class URI(DataType):

    @staticmethod
    def decode(value):
        return get_reference(value)


    @staticmethod
    def encode(value):
        return str(value)



class Email(String):

    @staticmethod
    def is_valid(value):
        expr = "^[0-9a-z]+[_\.0-9a-z-'+]*@([0-9a-z][0-9a-z-]+\.)+[a-z]{2,4}$"
        return re.match(expr, value.lower()) is not None



class FileName(DataType):
    """
    A filename is tuple consisting of a name, a type and a language.

    XXX We should extend this to add the character encoding
    """

    @staticmethod
    def decode(data):
        data = data.split('.')

        # XXX The encoding (UTF-8, etc.)

        n = len(data)
        if n == 1:
            return data[0], None, None
        elif n == 2:
            if '.%s' % data[-1].lower() in mimetypes.types_map:
                name, type = data
                return name, type, None
            elif has_language(data[-1]):
                name, language = data
                return name, None, language
            else:
                return '.'.join(data), None, None
        else:
            # Default values
            type = encoding = language = None

            # The language
            if '.%s' % data[-1].lower() in mimetypes.encodings_map:
                encoding = data[-1]
                data = data[:-1]
            elif has_language(data[-1]):
                language = data[-1]
                data = data[:-1]

            # The type
            if '.%s' % data[-1].lower() in mimetypes.types_map:
                type = data[-1]
                data = data[:-1]

            if encoding is not None:
                type = '%s.%s' % (type, encoding)

            # The name
            name = '.'.join(data)

        return name, type, language


    @staticmethod
    def encode(value):
        name, type, language = value
        if type is not None:
            name = name + '.' + type
        if language is not None:
            name = name + '.' + language
        return name



class HTTPDate(DataType):
    # XXX As specified by RFC 1945 (HTTP 1.0), should check HTTP 1.1
    # XXX The '%a', '%A' and '%b' format variables depend on the locale
    # (that's what the Python docs say), so what happens if the locale
    # in the server is not in English?

    @staticmethod
    def decode(data):
        formats = [
            # RFC-1123 (updates RFC-822, which uses two-digits years)
            '%a, %d %b %Y %H:%M:%S GMT',
            # RFC-850
            '%A, %d-%b-%y %H:%M:%S GMT',
            # ANSI C's asctime() format
            '%a %b  %d %H:%M:%S %Y',
            # Non-Standard formats, sent by some clients
            # Variation of RFC-1123, uses full day name (sent by Netscape 4)
            '%A, %d %b %Y %H:%M:%S GMT',
            # Variation of RFC-850, uses full month name and full year
            # (unkown sender)
            '%A, %d-%B-%Y %H:%M:%S GMT',
            ]
        for format in formats:
            try:
                tm = time.strptime(data, format)
            except ValueError:
                pass
            else:
                break
        else:
            raise ValueError, 'date "%s" is not an HTTP-Date' % data

        return datetime.datetime.utcfromtimestamp(calendar.timegm(tm))
    
    @staticmethod
    def encode(mtime):
        tm = time.gmtime(mtime)
        return time.strftime('%a, %d %b %Y %H:%M:%S GMT', tm)



class QName(DataType):

    @staticmethod
    def decode(data):
        if ':' in data:
            return tuple(data.split(':', 1))

        return None, data


    @staticmethod
    def encode(value):
        if value[0] is None:
            return value[1]
        return '%s:%s' % value



class Tokens(DataType):

    @staticmethod
    def decode(data):
        return tuple(data.split())


    @staticmethod
    def encode(value):
        return ' '.join(value)



class Enumerate(String):

    is_enumerate = True
    options = []


    @classmethod
    def get_options(cls):
        """Returns a list of dictionaries in the format
            [{'name': <str>, 'value': <unicode>}, ...]
        The default implementation returns a copy of the "options" class
        attribute. Both the list and the dictionaries may be modified
        afterwards.
        """
        return deepcopy(cls.options)


    @classmethod
    def is_valid(cls, name):
        """Returns True if the given name is part of this Enumerate's options.
        """
        for option in cls.get_options():
            if name == option['name']:
                return True
        return False


    @classmethod
    def get_namespace(cls, name):
        """Extends the options with information about which one is matching the
        given name.
        """
        options = cls.get_options()
        if isinstance(name, list):
            for option in options:
                option['selected'] = option['name'] in name
        else:
            for option in options:
                option['selected'] = option['name'] == name
        return options


    @classmethod
    def get_value(cls, name, default=None):
        """Returns the value matching the given name, or the default value.
        """
        for option in cls.get_options():
            if option['name'] == name:
                return option['value']

        return default


############################################################################
# Medium decoder/encoders (not for values)

class XML(object):

    @staticmethod
    def encode(value):
        return value.replace('&', '&amp;').replace('<', '&lt;')


    @staticmethod
    def decode(value):
        return value.replace('&amp;', '&').replace('&lt;', '<')



class XMLAttribute(object):

    @staticmethod
    def encode(value):
        value = value.replace('&', '&amp;').replace('<', '&lt;')
        return value.replace('"', '&quot;')

    @staticmethod
    def decode(value):
        value = value.replace('&amp;', '&').replace('&lt;', '<')
        return value.replace('&quot;', '"')
