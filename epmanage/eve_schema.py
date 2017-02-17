"""
settings.py : API schema

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
schema_tag = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 42,
        'required': True
    },
    'type': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 42,
    }
}

schema_agent = {
    'uuid': {
        'type': 'string',
        'minlength': 36,
        'maxlength': 36,
        'unique': True,
        'required': True,
        'readonly': True,
    },
    'hostname': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 200,
        'required': True,
        'unique': True,
        'readonly': True,
    },
    'os': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 45,
        'readonly': True,
    },
    'ostype': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 45,
        'readonly': True,
    },
    'osversion': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 45,
        'readonly': True,
    },
    'arch': {
        'type': 'string',
        'minlength': 2,
        'maxlength': 10,
        'readonly': True,
    },
    'version': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 45,
        'readonly': True,
    },
    'tags': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': schema_tag,
        }
    },
    'last_seen': {
        'type': 'datetime',
        'required': False,
        'readonly': True
    },
    'device_state': {
        'type': 'dict',
        'readonly': True,
        'nullable': True,
    }
}

schema_filteritem = {
    'variable': {
        'type': 'integer',
        'min': 0x1,
        'max': 0x7,
        'required': False
    },
    'operator': {
        'type': 'integer',
        'min': 0x1,
        'max': 0x4,
        'required': True
    },
    'value': {
        'type': 'string',
        'maxlength': 255
    },
}

schema_filter = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True,
        'unique': True,
    },
    'owner': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True
    },
    'filters': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': schema_filteritem,
        }
    }
}

schema_configuration = {
    'variable': {
        'type': 'string',
        'maxlength': 255,
        'required': True
    },
    'value': {
        'type': 'string',
        'maxlength': 255
    },
}

schema_config = {
    'app_id': {
        'type': 'string',
        'minlength': 36,
        'maxlength': 36,
        'required': True,
    },
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'unique_to_field': 'app_id',
        'required': True
    },
    'configuration': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': schema_configuration,
        }
    }
}

schema_schedule = {
    'type': {
        'type': 'string',
        'maxlength': 25,
        'required': True
    },
    'value1': {
        'type': 'string',
        'maxlength': 255
    },
    'value2': {
        'type': 'string',
        'maxlength': 255
    }
}

schema_action = {
    'app_id': {
        'type': 'string',
        'minlength': 36,
        'maxlength': 36,
        'required': True,
    },
    'config': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True,
    },
    'filter': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True
    },
    'schedule': {
        'type': 'dict',
        'schema': schema_schedule
    }
}

schema_developer = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True
    },
    'email': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
    },
    'website': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
    }
}

schema_app_compatibility = {
    'ostype': {
        'type': 'list',
        'required': True,
        'allowed': [
            'server',
            'workstation',
            'mobile'
        ]
    },
    'os': {
        'type': 'list',
        'required': True,
        'allowed': [
            'windows',
            'linux',
            'macosx',
            'android',
            'ios'
        ]
    },
}

schema_app_configuration_var = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True
    },
    'type': {
        'type': 'string',
        'required': True,
        'allowed': [
            'boolean',
            'integer',
            'string',
            'list_of_strings',
            'schedule'
        ]
    },
    'default_value': {
        'required': True
    },
    'description': {
        'type': 'string',
        'maxlength': 255,
        'required': True
    },
    'description_long': {
        'type': 'string',
        'maxlength': 10000,
        'required': False
    },
    'example': {
        'required': False
    },
}

schema_app_configuration = {
    'title': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True
    },
    'description': {
        'type': 'string',
        'maxlength': 10000
    },
    'variables': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': schema_app_configuration_var,
        }
    },
}

schema_app = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'unique': True,
        'required': True
    },
    'title': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'unique': True,
    },
    'uappid': {
        'type': 'string',
        'minlength': 36,
        'maxlength': 36,
        'unique': True,
        'required': True,
    },
    'logo': {
        'type': 'media'
    },
    'description': {
        'type': 'string',
        'maxlength': 10000
    },
    'version': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 45,
    },
    'developer': {
        'type': 'dict',
        'schema': schema_developer
    },
    'category': {
        'type': 'list',
        'schema': {
            'type': 'string',
            'minlength': 1,
            'maxlength': 255,
        }
    },
    'compatibility': {
        'type': 'dict',
        'schema': schema_app_compatibility,
    },
    'configuration': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': schema_app_configuration,
        }
    },
}

schema_user = {
    'email': {
        'type': 'string',
        'minlength': 5,
        'maxlength': 255,
        'unique': True,
        'required': True
    },
    'password': {
        'type': 'string',
        'minlength': 8,
        'maxlength': 1024,
        'required': False,
        'passwordstrength': 0.2,  # FIXME: stronger passwords
    },
    'firstname': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True,
    },
    'lastname': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 255,
        'required': True,
    },
    'roles': {
        'type': 'list',
        'schema': {
            'type': 'string',
            'minlength': 1,
            'maxlength': 255,
        }
    },
    'last_seen': {
        'type': 'datetime',
        'required': False,
        'readonly': True
    },
    'mfa_enabled': {
        'type': 'boolean',
        'required': False,
        'readonly': True
    },
}

# Agents (Endpoints)
agent_item = {
    'item_title': 'agent',
    'schema': schema_agent,
    'id_field': 'uuid',
    'item_lookup_field': 'uuid',
    'item_url': 'regex("[a-f0-9-]{36}")',
    'etag_ignore_fields': ['device_state'],
}
# Filters (Scopes)
filter_item = {
    'item_title': 'filter',
    'schema': schema_filter
}

# Actions (Tasks)
action_item = {
    'item_title': 'action',
    'schema': schema_action,
    'url': 'app/<regex("[a-f0-9-]{36}"):app_id>/action',
    'resource_title': 'action',
}
# Configurations (App settings)
config_item = {
    'item_title': 'config',
    'schema': schema_config,
    'url': 'app/<regex("[a-f0-9-]{36}"):app_id>/config',
    'resource_title': 'config',
}
# Applications
app_item = {
    'item_title': 'app',
    'schema': schema_app,
    'id_field': 'uappid',
    'item_lookup_field': 'uappid',
    'item_url': 'regex("[a-f0-9-]{36}")',
    'allowed_write_roles': [],
    'allowed_item_write_roles': [],
    'global_db': True
}
# Users
user_item = {
    'item_title': 'user',
    'schema': schema_user,
    'allowed_write_roles': ['urn:cmi_admin'],
    'allowed_item_write_roles': ['urn:cmi_ro', 'urn:cmi_rw', 'urn:cmi_admin'],
    'cache_control': 'no-cache',
    'global_db': True
}
# Clients
client_item = {
    'internal_resource': True,
    'global_db': True
}
