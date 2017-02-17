"""
settings.py : Project configuration

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
import os
import re

from .eve_schema import *

MONGO_CONFIG_VAR = re.compile('MONGOCLIENT_([A-Za-z0-9]+)_([A-Z]+)')


class Config(object):
    """Config class"""
    # ------------------------------------------------------------------------------
    # Basic config
    DEBUG = False
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    BASE_PATH = 'FIXME-BASE-PATH'

    # ------------------------------------------------------------------------------
    # Http config
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64Mo
    SESSION_COOKIE_DOMAIN = 'FIXME-DOMAIN'
    SECRET_KEY = 'FIXME-SECRET_KEY'  # noqa pylint: disable=C0301
    JSONIFY_PRETTYPRINT_REGULAR = False
    # URL prefix for EVE
    URL_PREFIX = ''
    # Allow all domains and methods with CORS
    X_DOMAINS = '*'
    # Allow only required headers
    X_HEADERS = ['Content-Type', 'If-Match', 'Authorization']
    # Cache
    CACHE_CONTROL = 'max-age=20,must-revalidate'

    # ------------------------------------------------------------------------------
    # Mail config
    EMAIL_HOST = 'smtp-relay.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_DOMAIN = 'FIXME-DOMAIN-NAME'
    EMAIL_ADDRESS = 'FIXME-SENDER-ADDRESS'
    REGISTRATION_URL = 'FIXME-WEB-REGISTRATION_URL'
    RECOVERY_URL = 'FIXME-WEB-RECOVERY-URL'

    # ------------------------------------------------------------------------------
    # Crypto config
    AUTH_PRIVKEY = os.path.join(BASE_PATH, 'pki/auth_priv.pem')
    AUTH_PUBKEY = os.path.join(BASE_PATH, 'pki/auth_pub.pem')

    # ------------------------------------------------------------------------------
    # Auth config
    TOKEN_RENEW_GRACE = 60  # 1 minute after expiration

    # ------------------------------------------------------------------------------
    # Storage config
    BIN_PATH = os.path.join(BASE_PATH, 'codelibbin')
    APPS_PATH = os.path.join(BASE_PATH, 'apps')
    PKG_PATH = os.path.join(BASE_PATH, 'pkg')
    BLOB_PATH = os.path.join(BASE_PATH, 'data/blob')
    AGENTBLOB_PATH = os.path.join(BASE_PATH, 'data/agent')
    TASKS_PATH = os.path.join(BASE_PATH, 'tasks')
    ASSETS_PATH = os.path.join(APP_ROOT, 'assets')
    LOG_FILE = os.path.join(APP_ROOT, 'logs/app.log')

    # ------------------------------------------------------------------------------
    # Cache config
    CACHE_DIR = os.path.join(BASE_PATH, 'cache')
    CACHE_SETTINGS = {
        'default_expiration': 86400,
        'eviction_policy': 'least-recently-stored'
    }

    # ------------------------------------------------------------------------------
    # Database config
    MONGO_HOST = '127.0.0.1'
    MONGO_PORT = 27017
    MONGO_DBNAME = 'epmanage'
    ELASTIC_HOSTS = [{'host': '127.0.0.1', 'port': 9200}]

    # ------------------------------------------------------------------------------
    # Eve specific config
    # No XML for now
    XML = False
    # Enable schema endpoint
    SCHEMA_ENDPOINT = 'schema'
    # Enable RW
    RESOURCE_METHODS = ['GET', 'POST']  # Do not enable global delete
    ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
    # For media items
    EXTENDED_MEDIA_INFO = ['content_type', 'length']
    # Max items
    PAGINATION_LIMIT = 1000000
    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    # ------------------------------------------------------------------------------
    # OPLOG
    OPLOG = True
    OPLOG_ENDPOINT = 'audit'
    OPLOG_AUDIT = True
    oplog_item = {
        'allowed_read_roles': ['urn:cmi_admin'],
        'allowed_item_read_roles': ['urn:cmi_admin'],
        'cache_control': 'no-cache'
    }

    # ------------------------------------------------------------------------------
    # Authorization
    ALLOWED_READ_ROLES = ['urn:cmi_ro', 'urn:cmi_rw', 'urn:cmi_admin']
    ALLOWED_ITEM_READ_ROLES = ['urn:cmi_ro', 'urn:cmi_rw', 'urn:cmi_admin']
    ALLOWED_ITEM_WRITE_ROLES = ['urn:cmi_rw', 'urn:cmi_admin']
    ALLOWED_WRITE_ROLES = ['urn:cmi_rw', 'urn:cmi_admin']
    INVITE_MAX_AGENTS = 20
    INVITE_MAX_USERS = 20

    # ------------------------------------------------------------------------------
    # Swagger config
    SWAGGER_INFO = {
        'title': 'EPManage API',
        'version': '0.1',
        'description': 'Management API',
    }
    SWAGGER_HOST = 'FIXME-HOSTNAME-FOR-SWAGGER'

    # ------------------------------------------------------------------------------
    # Sentry config
    SENTRY_CONFIG = {
        'dsn': 'FIXME-SENTRY-DSN',
    }
    PROPAGATE_EXCEPTIONS = True  # Needed so that Sentry can catch uncaught Flask exceptions

    # ------------------------------------------------------------------------------
    # Application configuration
    # Eve endpoints, empty if not needed
    DOMAIN = {
        'agent': agent_item,
        'filter': filter_item,
        'action': action_item,
        'app': app_item,
        'config': config_item,
        'user': user_item,
        # 'oplog': oplog_item,
        'client': client_item,
    }

    # Components (module: prefix)
    EPMODULES = dict(
        code='/code',
        auth='/auth',
        router='/route',
        task='/task',
        data='/data',
        frontend='/frontend',
        admin='/admin',
    )

    def __load_from_obj(self, obj):
        for key in dir(obj):
            if key.isupper() and not getattr(self, key, None):
                setattr(self, key, getattr(obj, key))

    def __load_from_dict(self, data):
        for key, value in data.items():
            if key.isupper() and not getattr(self, key, None):
                setattr(self, key, value)

    def __init__(self):
        # Load Flask default settings
        from flask import Flask
        self.__load_from_dict(Flask.default_config)

        # Load eve default settings
        import eve.default_settings
        self.__load_from_obj(eve.default_settings)

        self.__clientdb = None

    def get(self, item, default=None):
        special = self.get_special_var(item)
        if special:
            return special
        return getattr(self, item, default)

    def __getitem__(self, item):
        special = self.get_special_var(item)
        if special:
            return special
        return getattr(self, item)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __delitem__(self, key):
        return delattr(self, key)

    def __contains__(self, item):
        special = self.get_special_var(item)
        if special:
            return True
        return item in self.keys()

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        yield from self.keys()

    def keys(self):
        return [x for x in dir(self) if x.isupper()]

    def setdefault(self, key, default=None):
        if key not in self:
            setattr(self, key, default)

    def get_special_var(self, item: str):
        match = MONGO_CONFIG_VAR.match(item)
        if match:
            if not self.__clientdb:
                from flask import current_app as app
                self.__clientdb = app.data.pymongo('client').db['client']
                if not self.__clientdb:
                    return None
            client = self.__clientdb.find_one({'token': match.group(1)})
            if client:
                return client['database_settings'].get(match.group(2), self.get('MONGO_{}'.format(match.group(2))))
        return None


class DebugConfig(Config):
    """Config class - Debug"""
    DEBUG = True
    JSONIFY_PRETTYPRINT_REGULAR = True

    def __init__(self):
        super(DebugConfig, self).__init__()


config = None
