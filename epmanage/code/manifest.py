"""
manifest.py : Web manifest management

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
import logging
import struct
from pathlib import Path

import arrow
from flask import abort
from flask import current_app as app

import epmanage.settings as settings


class ManifestController(object):
    """Manage code manifest"""

    def __init__(self, arch=None):
        self.arch = arch
        self.__data = b''
        self.__timestamp = 0
        self.__appsdb = app.data.pymongo('app').db['app']

    def get_timestamp(self):
        """Get the manifest timestamp"""
        if self.__timestamp == 0:
            self.get_data()
        return self.__timestamp

    def __get_manifest_data(self):
        # Load the codelib manifest
        data = b''
        bin_path = Path(settings.config.BIN_PATH, self.arch, 'manifest.bin')
        try:
            data = bin_path.read_bytes()
        except FileNotFoundError:
            logging.error("Cannot find %s", str(bin_path))
            abort(404)

        manifest_count = 1

        # Load apps manifest
        for app_item in self.__appsdb.find():
            app_path = Path(settings.config.APPS_PATH, app_item['name'])
            try:
                app_data = (app_path / 'manifest.bin').read_bytes()
                data += app_data
                manifest_count += 1
            except:
                logging.error("Invalid SPK %s", str(app_path))
                continue

        final_data = b'SONEMANI'
        final_data += struct.pack('<H', manifest_count)
        final_data += data
        return arrow.utcnow().timestamp, final_data

    def get_data(self):
        """Returns the compound manifest"""
        timestamp, data = self.__get_manifest_data()
        self.__timestamp = timestamp
        self.__data = data

        return self.__data

    def get_pkg(self, pkg):
        """Get the pkg code"""
        binpath = Path(settings.config.BIN_PATH, self.arch)
        apps_path = Path(settings.config.APPS_PATH)

        for path in [binpath] + [x for x in apps_path.glob('*')]:
            pkg_path = path / pkg
            try:
                if pkg_path.relative_to(path) and pkg_path.exists():
                    return pkg_path.read_bytes()
            except:
                continue
        return None
