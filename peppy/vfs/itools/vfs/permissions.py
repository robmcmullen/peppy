# -*- coding: UTF-8 -*-
# Copyright (C) 2008 Rob McMullen <robm@users.sourceforge.net>
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

import stat


class Permissions(object):
    who_map = {
        'u': {
            'r': stat.S_IRUSR,
            'w': stat.S_IWUSR,
            'x': stat.S_IXUSR,
            },
        'g': {
            'r': stat.S_IRGRP,
            'w': stat.S_IWGRP,
            'x': stat.S_IXGRP,
            },
        'o': {
            'r': stat.S_IROTH,
            'w': stat.S_IWOTH,
            'x': stat.S_IXOTH,
            },
        }
    
    def __init__(self, mode):
        self.mode = mode


    def get_mode_integer_value(self):
        return self.mode


    def _get_mode_bit(self, who, perm):
        w = who[0]
        if perm.startswith("ex"):
            p = 'x'
        else:
            p = perm[0]
        if w in self.who_map:
            if p in self.who_map[w]:
                bit = self.who_map[w][p]
                return bit
            else:
                raise TypeError("Unknown permission %s" % perm)
        else:
            raise TypeError("Unknown symbolic mode %s" % who)


    def is_mode_set(self, who, perm):
        bit = self._get_mode_bit(who, perm)
        return bool(self.mode & bit)


    def set_mode(self, who, perm, state):
        bit = self._get_mode_bit(who, perm)
        current = self.mode & ~bit
        if state:
            current |= bit
        self.mode = current
