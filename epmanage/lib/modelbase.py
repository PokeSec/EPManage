"""
modelbase.py : Simple base for mongo models

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
import arrow


class Model(object):
    def __init__(self, data, is_new):
        self._set_modified(False)
        self._set_new(is_new)
        super(Model, self).__setattr__('_data', data)
        super(Model, self).__setattr__('_errors', [])

    def _set_modified(self, status: bool):
        super(Model, self).__setattr__('_modified', status)

    def _set_new(self, status: bool):
        super(Model, self).__setattr__('_new', status)

    def __getattr__(self, item):
        return self._data.get(item)

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            if self._data.get(key) != value:
                self._data[key] = value
                self._set_modified(True)
        else:
            super(Model, self).__setattr__(key, value)

    def __delattr__(self, item):
        if item in self._data:
            del self._data[item]
            self._set_modified(True)

    def add_error(self, error):
        self._errors.append(error)

    def get_errors(self):
        return self._errors

    def is_new(self):
        return self._new

    def is_modified(self):
        return self._modified

    def save(self):
        """Save the model to the bdd"""
        self.prepare_data()
        if self.is_modified():
            if self.is_new():
                self._data['_created'] = arrow.utcnow().datetime
            self._data['_updated'] = arrow.utcnow().datetime
        if self.is_new():
            self._modeldb.insert_one(self._data)
            self._set_new(False)
        elif self._modified:
            self._modeldb.replace_one({'_id': self._data['_id']}, self._data)
            self._set_modified(False)

    def prepare_data(self):
        pass

    def get_data(self):
        self.prepare_data()
        return self._data
