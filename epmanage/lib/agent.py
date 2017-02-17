"""
agent.py : Agent class

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
import uuid
from datetime import timedelta

import arrow
from flask import current_app as app

import epmanage.lib.auth
from epmanage.lib.client import Client
from epmanage.lib.modelbase import Model

logger = logging.getLogger(__name__)


class Agent(Model):
    """Agent object (Endpoint)"""

    @classmethod
    def from_enrollment_data(cls, data: dict):
        instance_token = data.pop('instance', None)
        if not instance_token:
            raise KeyError("Instance (client instance_token) is missing")
        data['__NOTOKEN'] = True
        agent = cls(instance_token, **data)
        if agent.is_new():
            agent.save()
            return agent
        else:
            logger.warning("Reenrollment of (%s), adding duplicate tag", agent.hostname)
            agent.add_tag('duplicate', 'system')
            agent.save()

            new_agent = cls(instance_token)
            for key, value in data.items():
                setattr(new_agent, key, value)
            new_agent.add_tag('duplicate', 'system')
            new_agent.save()
            return new_agent

    @classmethod
    def from_auth_data(cls, data: dict):
        instance_token = data.pop('instance', None)
        if not instance_token:
            raise KeyError("Instance (client token) is missing")
        if 'token' not in data:
            raise KeyError("Token is missing from auth data")
        data['uuid'] = data.pop('token', '')
        agent = cls(instance_token, **data)
        if agent.is_new():
            logger.warning("Attempt to authenticate with non-existent token")
            return None
        return agent

    @classmethod
    def from_token(cls, token: dict):
        return cls(token['aid'], uuid=token['sub'])

    def __init__(self, client_token, **kwargs):
        super(Agent, self).__setattr__('_token', client_token)
        super(Agent, self).__setattr__('_prefix', 'MONGOCLIENT_{}'.format(client_token))
        super(Agent, self).__setattr__('_modeldb', app.data.pymongo(prefix=self._prefix).db['agent'])
        super(Agent, self).__setattr__('_notoken', kwargs.pop('__NOTOKEN', False))

        data = None
        is_new = False
        if 'uuid' in kwargs:
            data = self._modeldb.find_one({'uuid': kwargs.get('uuid')})
        elif 'hostname' in kwargs:
            data = self._modeldb.find_one({'hostname': kwargs.get('hostname')})

        if not data:
            data = dict()
            is_new = True

        super(Agent, self).__init__(data, is_new)

        for key, value in kwargs.items():
            setattr(self, key, value)

    def prepare_data(self):
        if self.is_new():
            self.add_tag('new', 'system')
            self._data['uuid'] = str(uuid.uuid4())

        if not self._data.get('hostname'):
            self._data['hostname'] = 'unk_{}'.format(self._data['uuid'])

        # Enforce active agents
        client = self.get_client()
        if client:
            active = Agent.get_active_agents(client)
            max_agents = client.max_agents
            if max_agents and active >= max_agents:
                logger.info("Agent cap exceded: forcing disabled tag for (%s)", self.email)
                self.add_tag('disabled', 'system')

    def add_tag(self, tagname, tagtype=None):
        """Add a tag to an agent"""
        tags = self._data.setdefault('tags', [])
        tag = dict(name=tagname)
        if tagtype:
            tag['type'] = tagtype
        if tag in tags:
            return False
        else:
            tags.append(tag)
            self._set_modified(True)
            return True

    def remove_tag(self, tagname):
        """Remove a tag from the agent
        Returns True if the removal has succeeded"""
        tags = self._data.get('tags')
        if not tags:
            return False
        for tag in tags.items():
            if tag.get('name') == tagname:
                tags.pop(tag)
                self._set_modified(True)
                return True
        return False

    def set_state(self, data: dict):
        """Set the device state"""
        states = self._data.setdefault('device_state', dict())
        states.update(data)
        self._set_modified(True)
        return True

    def get_token(self, duration=None):
        """Get the authentication token for the agent"""
        if self._notoken:
            return None, 'Unable to get token'
        if not duration:
            duration = timedelta(hours=12)
        if any(tag['name'] == 'disabled' for tag in self._data.get('tags', [])):
            return None, 'The agent is disabled'
        token = epmanage.lib.auth.AuthController.generate_token(
            self.uuid,
            ['agent', 'urn:router', 'urn:code', 'urn:task', 'urn:data'],
            duration,
            extras=dict(aid=self._token))
        logger.info("Issued token for {%s} (%s)", self.uuid, self.hostname)
        return token, None

    def get_client(self):
        """Get the client object"""
        client = Client(token=self._token)
        if client.token != self._token:
            return None
        return client

    @staticmethod
    def get_active_agents(client: Client = None):
        if not client:
            identity = epmanage.lib.auth.current_identity
            client = identity.get_client()
        agentdb = client.db()['agent']
        return agentdb.count({'tags.name': {'$nin': ['disabled']}})

    @staticmethod
    def get_weekly_active_agents(client: Client = None):
        if not client:
            identity = epmanage.lib.auth.current_identity
            client = identity.get_client()
        agentdb = client.db()['agent']
        now = arrow.utcnow()
        return agentdb.count({'tags.name': {'$nin': ['disabled']},
                              'last_seen': {'$gte': now.replace(days=-7).datetime}
                              })
