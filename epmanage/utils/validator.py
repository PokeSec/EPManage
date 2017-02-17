"""
validator.py : Data validator for eve

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
import passwordmeter
from eve.io.mongo import Validator
from eve.utils import config
from flask import current_app as app


class CustomValidator(Validator):
    def _validate_passwordstrength(self, strength, field, value):
        value, error = passwordmeter.test(value)
        if value < strength:
            error_str = "Password is too weak, try to:\n"
            error_str += "\n".join([val for val in error.values()])
            self._error(field, error_str)

    def _validate_unique_to_field(self, extra_field, field, value):
        extra_value = self.document.get(extra_field) if self.document is not None else None
        query = {extra_field: extra_value} if extra_value else {}
        self._is_value_unique(True, field, value, query)

    def _is_value_unique(self, unique, field, value, query):
        """ Validates that a field value is unique.
        Patch original method to avoid app.data.driver.db
        """
        if unique:
            query[field] = value

            resource_config = config.DOMAIN[self.resource]

            if resource_config['soft_delete']:
                query[config.DELETED] = {'$ne': True}

            if self._id:
                id_field = resource_config['id_field']
                query[id_field] = {'$ne': self._id}

            datasource, _, _, _ = app.data.datasource(self.resource)

            if app.data.pymongo(resource=datasource).db[datasource].find_one(query):
                self._error(field, "value '%s' is not unique" % value)
