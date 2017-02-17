"""
auth.py : Authentication Logic

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
import random
import string
from datetime import timedelta
from email.utils import make_msgid
from functools import wraps
from pathlib import Path

import arrow
import jwt
from emails.template import JinjaTemplate as T
from eve.auth import TokenAuth
from flask import request, Response, abort, current_app as app
from flask.ext.emails import Message
from werkzeug.local import LocalProxy

import epmanage.lib.agent
import epmanage.lib.client
import epmanage.lib.user

current_identity = LocalProxy(lambda: AuthController.get_current_identity())  # type: Identity


class AuthException(Exception):
    """Authentication Exception"""

    def __init__(self, message):
        super(AuthException, self).__init__(message)
        self.message = message


class Identity(object):
    """User or agent identity"""

    def __init__(self, token):
        self.__raw_token = token
        self.__token = self.__check_token('', options=dict(verify_aud=False))
        if not self.__token:
            raise AuthException("Invalid token")
        if 'user' in self.__token['aud']:
            self.__object = epmanage.lib.user.User.from_token(self.__token)
            self.__internal_type = 'user'
        elif 'agent' in self.__token['aud']:
            self.__object = epmanage.lib.agent.Agent.from_token(self.__token)
            self.__internal_type = 'agent'
        else:
            raise AuthException("Bad token")

    def get_user(self):
        return self.__object if self.__internal_type == 'user' else None

    def get_agent(self):
        return self.__object if self.__internal_type == 'agent' else None

    def get_client(self):
        return self.__object.get_client()

    def check_audience(self, check, check_all=False):
        # print("CheckAudience", self['email'], self.__token['aud'], check)
        if callable(check):
            return check(self.__token['aud'])
        elif isinstance(check, str):
            return check in self.__token['aud']
        elif isinstance(check, list):
            if check_all:
                return all(item in self.__token['aud'] for item in check)
            else:
                return any(item in self.__token['aud'] for item in check)
        return False

    def __getitem__(self, item):
        return getattr(self.__object, item)

    def __check_token(self, audience, options=None):
        """Verifies a token"""
        if not options:
            options = {}
        decode_options = dict(
            verify_signature=True,
            verify_iat=True,
            verify_nbf=True,
            verify_exp=True,
            verify_iss=True,
            verify_aud=True,
            require_exp=True,
            require_iat=True,
            require_nbf=True)
        decode_options.update(options)
        try:
            data = jwt.decode(self.__raw_token,
                              open(app.config.AUTH_PUBKEY).read(),
                              algorithm='RS512',
                              options=decode_options,
                              issuer='auth_module',
                              audience=audience)
            return data
        except jwt.exceptions.InvalidTokenError:
            return None

    def renew_token(self):
        token = self.__check_token('', options=dict(verify_aud=False, verify_exp=False))
        if token:
            now = arrow.utcnow()
            exp = arrow.get(token['exp'])
            # Allow to replace near to expire tokens
            if exp.replace(minutes=+1) > now:
                return None
            if (now - exp).total_seconds() > app.config.TOKEN_RENEW_GRACE:
                return None
            print("RENEW TOKEN!", token)
            return self.__object.get_token()
        return None


def auth_required(audience, optional=False, check_all=False):
    """Decorator for JWT authentication"""

    def decorator(f):
        """Actual decorator"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            """Decorator internals"""
            if current_identity:
                verified = current_identity.check_audience(audience, check_all=check_all)
            else:
                verified = False
            if not optional and not verified:
                abort(401)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class AuthController(object):
    """Authentication backend"""

    @staticmethod
    def get_token_agent(data):
        """Return a token for the specified data"""
        try:
            agent = epmanage.lib.agent.Agent.from_auth_data(data)
        except KeyError:
            raise AuthException("Invalid agent data")
        token, error = agent.get_token()
        if error:
            raise AuthException(error)
        agent.last_seen = arrow.utcnow().datetime
        agent.save()
        return token

    @staticmethod
    def enroll_agent(data):
        """Return the agent unique token"""
        try:
            agent = epmanage.lib.agent.Agent.from_enrollment_data(data)
        except KeyError:
            raise AuthException("Invalid agent data")
        logging.debug("Agent enrollment: %s -> %s", agent.hostname, agent.uuid)
        return agent.uuid

    @staticmethod
    def get_token_user(email, password):
        """Get the token for user standard authentication"""
        user = epmanage.lib.user.User.from_email(email)
        if not user.client:  # new users have no client set
            return None
        if not user.check_password(password):
            return None
        if not user.mfa_enabled:
            # Return standard token
            token, error = user.get_token()
            if error:
                raise AuthException(error)
            user.last_seen = arrow.utcnow().datetime
            user.save()
            return token
        else:
            # Return restricted token
            token, error = user.get_token(duration=timedelta(minutes=10), privileges=['mfa'])
            if error:
                raise AuthException(error)
            return token

    @staticmethod
    def renew_token():
        """Renew the token is present in headers"""
        if current_identity:
            return current_identity.renew_token()
        return None

    @staticmethod
    def get_current_identity(force=False):
        token = request.headers.get('Authorization')
        # Check if token is present in headers
        if token:
            tmp = token.split(' ')
            # Check token format
            if len(tmp) == 2 and tmp[0] == 'Bearer':
                try:
                    AuthController.__identity = Identity(tmp[1])
                    return AuthController.__identity
                except AuthException:
                    return None
        return None

    @staticmethod
    def generate_token(sub, aud, exp, extras=None):
        """Generate a token for the specified subject, audience and expiration (arrow or timedelta)"""
        now = arrow.utcnow()
        if type(exp) == timedelta:
            exp = now + exp
        tokendict = {
            'nbf': now.timestamp,
            'iat': now.timestamp,
            'exp': exp.timestamp,
            'iss': 'auth_module',
            'aud': aud,
            'sub': sub
        }
        if extras:
            tokendict.update(extras)
        token = jwt.encode(
            tokendict,
            open(app.config.AUTH_PRIVKEY).read(),
            algorithm='RS512'
        )
        return token

    @staticmethod
    def invite(data: dict):
        """
        Create a Client object ready for registration
        :return: the registration_token to be used for registration
        """
        max_agents = data.pop('max_agents')
        if max_agents > app.config.INVITE_MAX_AGENTS:
            raise AuthException("Please set a maximum of {} agents".format(app.config.INVITE_MAX_AGENTS))
        max_users = data.pop('max_users')
        if max_users > app.config.INVITE_MAX_USERS:
            raise AuthException("Please set a maximum of {} users".format(app.config.INVITE_MAX_USERS))
        client = epmanage.lib.client.Client()
        client.invitation_email = data.pop('email')
        client.max_agents = max_agents
        client.max_users = max_users
        client.token = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(32))
        client.registration_token = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits)
                                            for _ in range(20))
        client.database_settings = dict(
            DBNAME='{}_corp'.format(client.token)
        )
        client.save()
        client.insert_default_data()

        sender = AuthController.get_current_identity().get_user()
        user_name = "{} {}".format(sender.firstname, sender.lastname)
        user_email = sender.email

        with (Path(app.config.ASSETS_PATH) / 'html/invite.html').open() as html, \
                (Path(app.config.ASSETS_PATH) / 'txt/invite.txt').open() as txt, \
                (Path(app.config.ASSETS_PATH) / 'img/rocket.png').open('rb') as rocket, \
                (Path(app.config.ASSETS_PATH) / 'img/epmanage.png').open('rb') as logo:
            msg = Message(
                html=T(html.read()),
                text=T(txt.read()),
                subject="Invitation to the EPManage",
                mail_from=(user_name, user_email),
                message_id=make_msgid(domain=app.config.EMAIL_DOMAIN))
            msg.attach(filename="rocket.png", content_disposition="inline", data=rocket)
            msg.attach(filename="epmanage.png", content_disposition="inline", data=logo)

            msg.send(to=client.invitation_email, render={
                'USER_NAME': user_name,
                'USER_EMAIL': user_email,
                'URL_TO_JOIN': "{}/{}".format(app.config.REGISTRATION_URL, client.registration_token)
            })

        return client.registration_token

    @staticmethod
    def register(data: dict):
        """Register a new Client and create its first User"""
        registration_token = data.pop('token')
        client = epmanage.lib.client.Client(**dict(registration_token=registration_token))
        if client.is_new():
            logging.debug("Attempt to register a user with an invalid registration_token")
            return False

        del client.registration_token
        client.name = data.pop('company')

        user = epmanage.lib.user.User(**data)
        if not user.is_new():
            logging.debug("Attempt to register a user with existing data")
            return False

        user.client = client.token
        user.roles = ['ro', 'rw', 'admin']
        user.change_password(data.pop('password'))
        user.save()

        client.save()
        client.insert_default_data()

        return True


class JWTAuth(TokenAuth):
    """Eve auth with JWT"""

    def authenticate(self):
        """Indicate to the client that it 0needs to authenticate via a 401."""
        resp = Response(None, 401, {'WWW-Authenticate': 'Bearer realm="api"'})
        abort(401, description='Please provide proper credentials', response=resp)

    def authorized(self, allowed_roles, resource, method):
        """Check if the client is authorized"""
        if not current_identity:
            return False
        result = current_identity.check_audience(allowed_roles)
        return result

    def get_mongo_prefix(self):
        prefix = super().get_mongo_prefix()
        user = current_identity
        if user:
            prefix = 'MONGOCLIENT_{}'.format(user['client'])
        return prefix

    def set_mongo_prefix(self, value):
        """Disable arbitrary changes to mongo prefix"""
        return
