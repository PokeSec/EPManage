"""
client.py : Client class

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
from flask import current_app as app

from epmanage.default_data import database_template
from epmanage.lib.modelbase import Model


class Client(Model):
    """Client object"""

    def __init__(self, **kwargs):
        super(Client, self).__setattr__('_modeldb', app.data.pymongo('client').db['client'])

        data = None
        is_new = False
        if 'token' in kwargs:
            data = self._modeldb.find_one({'token': kwargs.get('token')})
        if 'name' in kwargs:
            data = self._modeldb.find_one({'name': kwargs.get('name')})
        if 'registration_token' in kwargs:
            data = self._modeldb.find_one({'registration_token': kwargs.get('registration_token')})
        if not data:
            data = dict()
            is_new = True

        super(Client, self).__init__(data, is_new)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if self.token:
            super(Client, self).__setattr__('_db', app.data.pymongo(prefix='MONGOCLIENT_{}'.format(self.token)).db)
        else:
            super(Client, self).__setattr__('_db', None)

    def db(self):
        return self._db

    def insert_default_data(self):
        prefix = 'MONGOCLIENT_{}'.format(self.token)
        for collection, data in database_template.items():
            coll = app.data.pymongo(prefix=prefix).db[collection]
            for item in data:
                coll.insert(item)
