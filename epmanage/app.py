"""
app.py : Entry point for backend app

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
import importlib
import logging
import os
from logging.handlers import RotatingFileHandler

from eve import Eve
from flask import Response
from raven.contrib.flask import Sentry
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.utils import import_string

import epmanage.settings as settings
from epmanage.lib.auth import JWTAuth, AuthController
from epmanage.lib.filter import Filter
from epmanage.lib.user import User
from epmanage.reverseproxied import ReverseProxied
from epmanage.utils import Mongo, CustomValidator


class EPManageEve(Eve):
    """Custom EVE class to allow config import from object"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wsgi_app = ReverseProxied(self.wsgi_app)
        self.wsgi_app = ProxyFix(self.wsgi_app)

        if 'EPMODULES' in self.config.keys():
            for epmodule, prefix in self.config['EPMODULES'].items():
                try:
                    module = importlib.import_module('epmanage.{}'.format(epmodule))
                    component = getattr(module, '{}_component'.format(epmodule), None)
                    if component:
                        self.register_blueprint(component, url_prefix=prefix)
                except (ImportError, AttributeError):
                    pass

        if 'SWAGGER_INFO' in self.config.keys():
            from eve_swagger import swagger
            self.register_blueprint(swagger)

        if 'user' in self.config['DOMAIN'].keys():
            # Fixups for EVE API endpoints
            self.on_insert_user += User.eve_hook_write_user
            self.on_replace_user += User.eve_hook_write_user
            self.on_update_user += User.eve_hook_write_user

            self.on_pre_GET_user += User.eve_hook_filter_user
            self.on_pre_HEAD_user += User.eve_hook_filter_user
            self.on_pre_PATCH_user += User.eve_hook_filter_user
            self.on_pre_PUT_user += User.eve_hook_filter_user
            self.on_pre_DELETE_user += User.eve_hook_filter_user

            self.on_delete_item_user += User.eve_hook_anti_self_delete_user

        if 'filter' in self.config['DOMAIN'].keys():
            # Fixups for EVE API endpoints
            self.on_insert_filter += Filter.eve_hook_write_filter
            self.on_replace_filter += Filter.eve_hook_write_filter
            self.on_update_filter += Filter.eve_hook_write_filter
            self.on_delete_item_filter += Filter.eve_hook_write_filter

    def load_config(self):
        """Override default load_config"""
        conf_module = os.environ.get('EPMANAGE_CONFIG_MODULE')
        if not conf_module:
            conf_module = 'epmanage.settings.Config'
        obj = import_string(conf_module)()

        self.config = obj
        settings.config = obj


class EPManageSentry(Sentry):
    def get_user_info(self, request):
        try:
            user = AuthController.get_current_identity().get_user()
            if user:
                return {'email': user.email}
            client = AuthController.get_current_identity().get_client()
            if client:
                return {'uuid': client.uuid}
        except Exception:
            return


app = EPManageEve(auth=JWTAuth, data=Mongo, validator=CustomValidator)

if not settings.config.DEBUG:
    sentry = EPManageSentry(app, register_signal=False, logging=True, level=logging.WARNING)
else:
    sentry = None

logging.basicConfig(
    format="[%(asctime)s] {%(name)s} %(levelname)s - %(message)s",
    handlers=[RotatingFileHandler(settings.config.LOGFILE, maxBytes=1000000, backupCount=1)],
    level=logging.DEBUG)

logging.getLogger('werkzeug').handlers = [logging.StreamHandler()]


@app.after_request
def after(response):
    """Remove cache control when request failed"""
    if response.status_code not in range(200, 300):
        response.cache_control.max_age = 0
    return response


@app.route('/')
def index():
    return Response(status=200)
