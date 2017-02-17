"""
user.py : User class

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
from pathlib import Path
from typing import List

import bson
import pyotp
from emails.template import JinjaTemplate as T
from flask import abort, current_app as app
from flask.ext.emails import Message
from passlib.context import CryptContext

import epmanage.lib.auth
from epmanage.lib.client import Client
from epmanage.lib.modelbase import Model

logger = logging.getLogger(__name__)
RESET_TOKEN_LEN = 32


class User(Model):
    """User object (CMI user)"""
    __pwdctx = CryptContext(schemes=["sha256_crypt"])

    @classmethod
    def from_email(cls, email: str):
        return cls(email=email)

    @classmethod
    def from_reset_token(cls, reset_token: str):
        return cls(_reset_token=reset_token)

    @classmethod
    def from_token(cls, token: dict):
        return cls(_id=token['sub'])

    def __init__(self, **kwargs):
        super(User, self).__setattr__('_modeldb', app.data.pymongo('user').db['user'])
        data = None
        is_new = False
        if 'email' in kwargs:
            data = self._modeldb.find_one({'email': kwargs.get('email')})
        elif '_reset_token' in kwargs:
            data = self._modeldb.find_one({'_reset_token': kwargs.get('_reset_token')})
        if '_id' in kwargs:
            try:
                data = self._modeldb.find_one({'_id': bson.objectid.ObjectId(kwargs.get('_id'))})
            except bson.errors.InvalidId:
                logger.error("Object ID in token is invalid")
                data = None
        if not data:
            data = dict()
            is_new = True
        super(User, self).__init__(data, is_new)

        for key, value in kwargs.items():
            if key != 'password':
                setattr(self, key, value)

    def __getattr__(self, item):
        if item in ['password', '_password']:
            logger.warning("Attempt to access password information", stack_info=True)
            raise AttributeError
        return super(User, self).__getattr__(item)

    def __setattr__(self, key, value):
        if key == 'password':
            if self.change_password(value):
                self._set_modified(True)
            else:
                logger.error("Cannot change password for (%s)", self.email)
        else:
            if str(getattr(self, key)) != str(value) and not self.is_new():
                logger.info("Attribute change for (%s) : {%s}[%s] ==> [%s]", self.email, key, getattr(self, key), value)
            return super(User, self).__setattr__(key, value)

    def prepare_data(self):
        # Sort roles
        if 'roles' in self._data:
            self._data['roles'].sort()

            # Enforce active users
            client = self.get_client()
            if client:
                active = User.get_active_users(client)
                max_users = client.max_users
                if max_users and active >= max_users:
                    logger.info("Client cap exceded: forcing empty roles (user disabled) for (%s)", self.email)

                    # Add an error if the user already exists
                    if not self.is_new():
                        self.add_error("Client cap exceded: forcing empty roles (user disabled) for (%s)" % self.email)
                    self._data['roles'] = []

    def check_password(self, password):
        """Check the password"""
        if not self._data.get('_password'):
            return False

        hashed = self._data.get('_password')
        try:
            check = User.__pwdctx.verify(password, hashed)
            if check and User.__pwdctx.needs_update(hashed):
                if self.change_password(password):
                    logger.debug("Password for (%s) has been upgraded", self.email)
                    self.save()
                else:
                    logger.error("Cannot change password for (%s)", self.email)
                    check = False
        except ValueError:
            check = False
        if not check:
            logger.error("Password error for (%s)", self.email)
        return check

    def change_password(self, password, reset_token=False):
        if reset_token:
            if self._data.get('_reset_token') != reset_token:
                return False
            del self._data['_reset_token']
            logger.info("Password reset for (%s)", self.email)
        self._data['_password'] = User.__pwdctx.encrypt(password)
        self._set_modified(True)
        if 'password' in self._data:
            del self._data['password']
        logger.info("Password change for (%s)", self.email)
        return self._data['_password']

    def get_token(self, duration=None, privileges=None):
        """Get the authentication token for the agent"""
        if not duration:
            duration = timedelta(hours=18)
        if len(self.roles) == 0:
            logger.warning("Attempt to login with a disabled account (%s)", self.email)
            return None, "User is disabled"
        if not privileges:
            privileges = ['urn:cmi_{}'.format(x) for x in self.roles]
        else:
            privileges = ['urn:cmi_{}'.format(x) for x in privileges]
        token = epmanage.lib.auth.AuthController.generate_token(
            str(self._data['_id']),
            ['user'] + privileges,
            duration)
        logger.info("Issued token for (%s) with (%s)", self.email, privileges)
        return token, None

    def get_client(self):
        """Get the client object"""
        client = Client(token=self.client)
        if client.token != self.client:
            return None
        return client

    def send_password_reset_code(self):
        """Create a password reset code"""
        reset_token = ''.join(
            random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(RESET_TOKEN_LEN))
        self._data['_reset_token'] = reset_token
        self._set_modified(True)
        self.save()
        logger.info("Password reset requested for (%s) : %s", self.email, reset_token)
        with (Path(app.config.ASSETS_PATH) / 'html/recover.html').open() as html, \
                (Path(app.config.ASSETS_PATH) / 'txt/recover.txt').open() as txt, \
                (Path(app.config.ASSETS_PATH) / 'img/epmanage.png').open('rb') as logo:
            msg = Message(
                html=T(html.read()),
                text=T(txt.read()),
                subject="Account recovery for {}".format(self.email),
                mail_from=("EPManage", app.config.EMAIL_ADDRESS),
                message_id=make_msgid(domain=app.config.EMAIL_DOMAIN))
            msg.attach(filename="epmanage.png", content_disposition="inline", data=logo)

            msg.send(to=self.email, render={
                'USER_EMAIL': self.email,
                'URL_TO_RESET': "{}/{}".format(app.config.RECOVERY_URL, reset_token)
            })
        return True

    def init_2fa_totp(self):
        if self._data.get('mfa_enabled'):
            return None
        self._data['_2fa_totp'] = pyotp.random_base32()
        self._set_modified(True)
        self.save()
        totp = pyotp.TOTP(self._data['_2fa_totp'])
        return totp.provisioning_uri(self.email, 'EPManage')

    def check_2fa_totp(self, token):
        if not self._data.get('_2fa_totp'):
            return False
        totp = pyotp.TOTP(self._data['_2fa_totp'])
        totp.now()
        result = totp.verify(token, valid_window=1)
        if not result and self._data.get('_2fa_recovery_codes'):
            # Try the recovery codes
            if token in self._data['_2fa_recovery_codes']:
                self._data['_2fa_recovery_codes'].remove(token)
                self._set_modified(True)
                self.save()
                logger.info("User (%s) has used a recovery code", self.email)
                result = True
        if not result:
            logger.error("Bad TOTP token for (%s)", self.email)
        return result

    def disable_2fa_totp(self):
        if not self._data.get('_2fa_totp'):
            return False
        del self._data['_2fa_totp']
        del self._data['mfa_enabled']
        self._set_modified(True)
        self.save()
        logging.info("Disabled TOTP 2fa for (%s)", self.email)
        return True

    def enable_2fa_totp(self):
        if not self._data.get('_2fa_totp'):
            return False
        self.mfa_enabled = True
        self.save()
        logging.info("Enable TOTP 2fa for (%s)", self.email)
        return True

    # EVE filter callbacks
    @staticmethod
    def get_active_users(client: Client = None):
        userdb = app.data.pymongo('user').db['user']
        if not client:
            identity = epmanage.lib.auth.current_identity
            client = identity.get_client()
        return userdb.count({'client': client.token, 'roles': {'$gt': []}})

    @staticmethod
    def eve_hook_write_user(item, original=None):
        identity = epmanage.lib.auth.current_identity
        client = identity.get_client()
        data = [item] if not isinstance(item, list) else item  # type: List[dict]
        for user in data:
            if 'roles' in user and not identity.check_audience('urn:cmi_admin'):
                logger.error("Attempt to modify user without admin rights (%s)", identity['email'])
                abort(403)

            if 'client' not in user:
                user['client'] = client.token

            userobj = User(**user)  # type: User

            if 'password' in user:
                if not userobj.change_password(user.pop('password')):
                    userobj.add_error("Cannot change password")

            user.update(userobj.get_data())

            errors = userobj.get_errors()
            if errors:
                abort(403, ';'.join(errors))

    @staticmethod
    def eve_hook_filter_user(request, lookup):
        identity = epmanage.lib.auth.current_identity
        client = identity.get_client()
        lookup['client'] = client.token
        if not identity.check_audience('urn:cmi_admin'):
            lookup['email'] = identity['email']

    @staticmethod
    def eve_hook_anti_self_delete_user(item):
        identity = epmanage.lib.auth.current_identity
        if identity['email'] == item['email']:
            logger.warning("Attempt to self-delete (%s)", identity['email'])
            abort(403, "Cannot self-delete")
        logger.info("Delete (%s) by (%s)", item['email'], identity['email'])
