"""
filter.py : Filter class

This file is part of EPControl.

Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt

EPControl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

EPControl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
"""
import enum
import fnmatch
import logging
from typing import List

from flask import abort

from epmanage.lib.auth import current_identity
from epmanage.lib.modelbase import Model


class VarFilter(enum.Enum):
    """Filteritem variable"""
    uuid = 0x01
    hostname = 0x02
    os = 0x03
    osversion = 0x04
    ostype = 0x05
    tag = 0x06
    filtername = 0x07


class OperatorFilter(enum.Enum):
    """Filteritem operator"""
    equal = 0x01
    like = 0x02
    OR = 0x03
    AND = 0x04

    def is_binop(self):
        return (self == OperatorFilter.OR) or (self == OperatorFilter.AND)


class Filter(Model):
    """Filter object"""

    def __init__(self, **kwargs):
        super(Filter, self).__setattr__('_modeldb', current_identity.get_client().db()['filter'])

        data = None
        is_new = False
        if 'name' in kwargs:
            data = self._modeldb.find_one({'name': kwargs.get('name')})
        if not data:
            data = dict()
            is_new = True

        super(Filter, self).__init__(data, is_new)

        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def eve_hook_write_filter(item, original=None):
        data = [item] if not isinstance(item, list) else item  # type: List[dict]
        for flt in data:
            if flt['owner'] == 'system':
                abort(403, "Cannot delete system filters")

    @staticmethod
    def __match_value(value, pattern, operator):
        if operator == OperatorFilter.equal:
            return True if pattern == '<any>' else value == pattern
        elif operator == OperatorFilter.like:
            return fnmatch.fnmatch(value, pattern)

    def __eval_filteritem(self, filteritem, agent):
        var = VarFilter(filteritem['variable'])
        operator = OperatorFilter(filteritem['operator'])

        if var == VarFilter.tag:
            try:
                return any(
                    t for t in agent['tags']
                    if self.__match_value(t.get('name'), filteritem['value'], operator))
            except KeyError:
                return False
        elif var == VarFilter.filtername:
            return self.is_filter_applicable(filteritem['value'], agent)

        return self.__match_value(agent[var.name], filteritem['value'], operator)

    @staticmethod
    def __eval_and(evaltab):
        index = 0
        while True:
            if len(evaltab) < 3:
                break
            try:
                lval, operator, rval = evaltab[index:index + 3]
                if operator == OperatorFilter.AND:
                    del evaltab[index:index + 3]
                    evaltab.insert(index, lval & rval)
                else:
                    index += 2
            except (ValueError, IndexError):
                break
        return evaltab

    @staticmethod
    def __eval_or(evaltab):
        index = 0
        while True:
            if len(evaltab) < 3:
                break
            try:
                lval, operator, rval = evaltab[index:index + 3]
                if operator == OperatorFilter.OR:
                    del evaltab[index:index + 3]
                    evaltab.insert(index, lval | rval)
                else:
                    index += 2
            except (ValueError, IndexError):
                break
        return evaltab

    def is_applicable(self, agent):
        """Check if a filter is applicable for an agent"""
        evaltab = []
        for filteritem in self.filters:
            operator = OperatorFilter(filteritem['operator'])
            if not operator.is_binop():
                evaltab.append(self.__eval_filteritem(filteritem, agent))
            else:
                evaltab.append(operator)

        # Single value tab
        if len(evaltab) == 1:
            return evaltab[0]

        # Process AND
        evaltab = self.__eval_and(evaltab)

        # Single value tab
        if len(evaltab) == 1:
            return evaltab[0]

        # Process OR
        evaltab = self.__eval_or(evaltab)

        # Single value tab
        if len(evaltab) == 1:
            return evaltab[0]

        logging.error("Filter list not valid")
        return False
