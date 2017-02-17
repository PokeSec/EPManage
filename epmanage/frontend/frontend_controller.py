"""
frontend.py : Frontend logic

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
import copy
import importlib
import json
import logging
import os
from collections import OrderedDict

from flask import current_app as app
from flask import url_for

from epmanage import settings
from epmanage.lib.agent import Agent
from epmanage.lib.user import User
from epmanage.utils import Singleton


class FrontendController(metaclass=Singleton):
    """Frontend logic"""

    def __init__(self):
        self.__pkg_data = dict()
        self.__apps_db = app.data.pymongo('app').db['app']

    def load_pkg_data(self):
        self.__pkg_data = json.load(open(os.path.join(settings.config.PKG_PATH, 'pkg.json')))

    def get_stats(self, identity):
        if not identity:
            return None
        client = identity.get_client()
        if not client or not client.db():
            return None

        data = dict(
            stats=[
                dict(
                    key='lic_endpoints',
                    title='Licensed Endpoints',
                    category='device-management',
                    count=Agent.get_active_agents(),
                    max=client.max_agents
                ),
                dict(
                    key='lic_users',
                    title='Licensed Users',
                    category='user-management',
                    count=User.get_active_users(),
                    max=client.max_users
                ),
                dict(
                    key='Endpoints',
                    title='Active Endpoints (weekly)',
                    category='device-management',
                    count=Agent.get_weekly_active_agents(),
                    max=Agent.get_active_agents()
                )
            ],
            status={'level': 'warning', 'message': 'This is a beta, don\'t expect too much :p '},
            app_stats=[]
        )

        for epapp in self.__apps_db.find():
            try:
                module = importlib.import_module('epmanage.apps.{}'.format(epapp['name']))
                func = getattr(module, 'get_dashboard_data', None)
                if callable(func):
                    data['app_stats'].append(func(epapp, client))
            except (ImportError, AttributeError):
                pass

        return data

    def get_package_name(self, pkg_hash):
        for key, val in self.__pkg_data.items():
            for pkg in val['packages']:
                file_name = [x['value'] for x in pkg['hash'] if x['type'] == 'sha256'][0]
                if pkg_hash == file_name:
                    return pkg['name']
        return None

    def get_packages(self, identity):
        if not identity:
            return None
        client = identity.get_client()

        oses = OrderedDict([
            ('win', 'win'),
            ('android', 'android'),
            ('macosx', 'macosx'),
            ('redhat', 'centos'),
            ('ubuntu', 'ubuntu'),
            ('sles', 'sles'),
            ('centos', 'centos'),
            ('debian', 'debian'),
        ])

        try:
            data = []
            for key, oskeyval in oses.items():
                val = copy.deepcopy(self.__pkg_data.get(oskeyval))
                if not val:
                    continue
                val['os'] = key
                for pkg in val['packages']:
                    file_name = [x['value'] for x in pkg['hash'] if x['type'] == 'sha256'][0]
                    pkg['url'] = url_for('frontend_component.download_package', name=file_name)

                val['extra_data'] = client.token
                data.append(val)
        except:
            return []

        return data

    @staticmethod
    def get_app_data(identity, app_name: str, data_type: str):
        if not identity:
            return None
        client = identity.get_client()
        if not client or not client.db():
            return None
        try:
            module = importlib.import_module('epmanage.apps.{}'.format(app_name))
            func = getattr(module, 'get_data_{}'.format(data_type), None)
            if callable(func):
                return func(client)
        except (ImportError, AttributeError):
            logging.warning("Attempt to get unknown app data", exc_info=True)
            return None
