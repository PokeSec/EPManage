"""
mongo.py : Custom data layer for eve

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
import eve.io.mongo

from epmanage.settings import Config


class Mongo(eve.io.mongo.Mongo):
    """Custom data layer"""

    def __init__(self, app):
        super().__init__(app)

    def current_mongo_prefix(self, resource=None):
        domain = Config.DOMAIN.get(resource)
        if not resource or (domain and domain.get('global_db', False)):
            prefix = 'MONGO'
        else:
            prefix = super().current_mongo_prefix(resource)
        return prefix
