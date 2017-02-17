"""
app.py : App class

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
import hashlib
import json
from io import BufferedReader
from typing import Optional

from flask import current_app as app
from gridfs import GridFS

from epmanage.lib.auth import current_identity
from epmanage.lib.modelbase import Model


class App(Model):
    """App object"""

    def __init__(self, **kwargs):
        super(App, self).__setattr__('_modeldb', app.data.pymongo('app').db['app'])
        super(App, self).__setattr__('_configdb', None)

        data = None
        is_new = False
        if 'uappid' in kwargs:
            data = self._modeldb.find_one({'uappid': kwargs.get('uappid')})
        if not data:
            data = dict()
            is_new = True

        super(App, self).__init__(data, is_new)

        for key, value in kwargs.items():
            setattr(self, key, value)

    def prepare_data(self):
        if isinstance(self.logo, BufferedReader):
            grid = GridFS(self._modeldb.database)

            data = self.logo.read()
            data_hash = hashlib.md5(data).hexdigest()
            existing = grid.find_one(dict(md5=data_hash))
            if existing:
                oid = existing._id
            else:
                oid = grid.put(data)
            self.logo = oid

    def parse_config(self, data: dict) -> dict:
        if not data:
            return {}

        config = dict()
        configdict = {x['variable']: x['value'] for x in data}
        for configitem in self._data['configuration']:
            for variable in configitem['variables']:
                val = configdict.get(variable['name'])  # type: str
                if not val:
                    val = variable.get('default', '')
                if variable['type'] == 'bool':
                    config[variable['name']] = val.lower() == 'true'
                elif variable['type'] == 'integer':
                    # config[variable['name']] = human2bytes(val)
                    if val:
                        config[variable['name']] = int(val)
                elif variable['type'] == 'string':
                    config[variable['name']] = val
                elif variable['type'] == 'list_of_strings':
                    config[variable['name']] = []
                    try:
                        tmp = json.loads(val)
                        if isinstance(tmp, list):
                            for item in tmp:
                                config[variable['name']] += item.split('|')
                    except json.decoder.JSONDecodeError:
                        pass
        return config

    def get_config(self, config_name: str) -> Optional[dict]:
        if not self._configdb:
            super(App, self).__setattr__('_configdb', current_identity.get_client().db()['config'])
        config = self._configdb.find_one({'name': config_name})
        if not config:
            return None

        config = self.parse_config(config['configuration'])
        base_config = self._configdb.find_one({'name': '.global'})  # type: dict
        if base_config:
            base_config = self.parse_config(base_config['configuration'])
            for key, val in config.items():
                if val:
                    base_config[key] = val
            return base_config
        else:
            return config
