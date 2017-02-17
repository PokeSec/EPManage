"""
admin.py : Admin only APIs

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
import json
from pathlib import Path

from eve.io.mongo import Validator
from flask import Blueprint, Response, jsonify, abort, request
from flask import current_app as app

from epmanage import settings
from epmanage.lib.app import App
from epmanage.lib.auth import auth_required, AuthController, AuthException
from epmanage.utils import cors

admin_component = Blueprint('admin_component', __name__)


@admin_component.route('/invite', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_superadmin')
@cors()
def admin_invite():
    registration_token = None
    data = request.get_json(silent=True)
    if data:
        fields = ['email', 'max_users', 'max_agents']
        if any(data.get(field) is None for field in fields):
            abort(400)
        try:
            registration_token = AuthController.invite({field: data.get(field) for field in fields})
        except AuthException as exc:
            abort(403, exc.message)
        return registration_token if registration_token else abort(403)
    else:
        abort(406)


@admin_component.route('/apps', methods=['GET', 'OPTIONS'])
@auth_required('urn:cmi_superadmin')
@cors()
def admin_apps():
    apps_path = Path(settings.config.APPS_PATH)

    return jsonify(apps=[x.name for x in apps_path.glob('*') if x.is_dir()])


@admin_component.route('/apps/<app_name>', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_superadmin')
@cors()
def admin_apps_do(app_name):
    apps_path = Path(settings.config.APPS_PATH)

    action = request.json.get('action')
    if not action in ['enable', 'disable']:
        abort(400)

    app_path = apps_path / app_name

    # Check if app is under apps_path
    try:
        app_path.relative_to(apps_path)
    except ValueError:
        abort(404)

    if not app_path.exists():
        abort(404)

    app_db = app.data.pymongo('app').db['app']
    if action == 'disable':
        app_db.remove(dict(name=app_name))
        return Response(status=204)
    elif action == 'enable':
        schema = settings.config.DOMAIN['app']['schema']
        validator = Validator(schema=schema, resource='app')

        with (app_path / 'manifest.json').open('r') as ifile:
            data = ifile.read()
            manifest = json.loads(data)
            app_config = manifest['app_config']

            logo = app_config.pop('logo')

            existing = app_db.find_one(dict(uappid=app_config['uappid']))
            if existing:
                app_db.remove(dict(uappid=app_config['uappid']))

            if not validator.validate(app_config):
                print("Validation error: ", validator.errors)
                abort(422, "Invalid app data")

            app_item = App(**app_config)

            app_config['logo'] = logo

            if app_config.get('logo'):
                try:
                    logofile = (app_path / app_config.get('logo')).open('rb')
                    app_item.logo = logofile
                except:
                    pass
            app_item.prepare_data()

            app_item.save()
        return Response(status=201)
    else:
        abort(404, 'Invalid action')
