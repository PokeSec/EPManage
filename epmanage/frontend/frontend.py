"""
frontend.py : Simple frontend interface

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
from pathlib import Path

from elasticsearch import ElasticsearchException
from flask import Blueprint, jsonify, request, abort, Response, send_file

from epmanage import settings
from epmanage.data.data_controller import DataController
from epmanage.frontend.frontend_controller import FrontendController
from epmanage.lib.auth import AuthController, auth_required, current_identity, AuthException
from epmanage.lib.user import User
from epmanage.utils import cors

frontend_component = Blueprint('frontend_component', __name__)


@frontend_component.route('/basestats', methods=['GET', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def get_stats():
    """Get tasks to do"""
    return jsonify(data=FrontendController().get_stats(current_identity))


@frontend_component.route('/packages', methods=['GET', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def get_packages():
    """Get tasks to do"""
    FrontendController().load_pkg_data()
    return jsonify(data=FrontendController().get_packages(current_identity))


@frontend_component.route('/download/<name>', methods=['GET', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors(expose=['Content-Disposition'])
def download_package(name):
    pkg_path = Path(settings.config.PKG_PATH)
    path = pkg_path / name
    try:
        path.relative_to(pkg_path)
    except ValueError:
        abort(404)

    pkg_name = FrontendController().get_package_name(name)
    if not pkg_name:
        raise RuntimeError('ERROR, could not get package name')

    rsp = send_file(str(path.absolute()),
                    as_attachment=True,
                    attachment_filename=pkg_name)
    return rsp


@frontend_component.route('/login', methods=['POST', 'OPTIONS'])
@cors()
def login():
    """Frontend login"""
    token = None
    data = request.get_json(silent=True)
    if data:
        email = data.get('email')
        password = data.get('password')
        try:
            token = AuthController.get_token_user(email, password) if email and password else None
        except AuthException as exc:
            abort(403, exc.message)
        return token if token else abort(403)

    # Try to renew the existing token if no data is provided
    token = AuthController.renew_token()
    return token if token else abort(403)


@frontend_component.route('/login-mfa', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_mfa')
@cors()
def login_mfa():
    """Frontend login"""
    user = current_identity.get_user()  # type: User
    token = None
    data = request.get_json(silent=True)
    if data and data.get('code') and user and user.check_2fa_totp(data.get('code')):
        try:
            token, error = user.get_token()
            if error:
                raise AuthException(error)
        except AuthException as exc:
            abort(403, exc.message)
        return token if token else abort(403)
    else:
        abort(403)


@frontend_component.route('/manage-mfa', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def manage_mfa():
    user = current_identity.get_user()  # type: User
    data = request.get_json(silent=True)
    if not user or not data:
        abort(403)
    if data.get('init') is True:
        rsp = user.init_2fa_totp()
        if not rsp:
            abort(403)
        return rsp
    elif data.get('disable') is True:
        return Response(status=204) if user.disable_2fa_totp() else abort(500)
    elif data.get('code'):
        if user.check_2fa_totp(data.get('code')):
            user.enable_2fa_totp()
            return Response(status=204)
        else:
            abort(403)


@frontend_component.route('/register', methods=['POST', 'OPTIONS'])
@cors()
def register():
    data = request.get_json(silent=True)
    if data:
        fields = ['token', 'firstname', 'lastname', 'company', 'email', 'password']
        if any(data.get(field) is None for field in fields):
            abort(400)
        status = AuthController.register({field: data.get(field) for field in fields})
        return Response(status=201) if status else abort(403)
    else:
        abort(406)


@frontend_component.route('/recover', methods=['POST', 'OPTIONS'])
@cors()
def recover():
    """Frontend password recovery"""
    data = request.get_json(silent=True)
    if data:
        email = data.get('email')
        token = data.get('token')
        password = data.get('password')
        if email:
            user = User.from_email(email)
            if user and not user.is_new():
                if user.mfa_enabled:
                    abort(422, 'Cannot change password for MFA-enabled accounts')
                if not user.send_password_reset_code():
                    abort(422, 'Failed to send reset code')
        elif token and password:
            user = User.from_reset_token(token)
            if user and not user.is_new():
                if not user.change_password(password, reset_token=token):
                    abort(422, 'Failed to change password')
                user.save()
            else:
                abort(422, 'Bad token')
        else:
            abort(422, 'Bad parameters')
        return Response(status=200)
    else:
        abort(406)


@frontend_component.route('/feedback', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def feedback():
    data = request.get_json(silent=True)
    if data:
        text = data.get('text')
        category = data.get('category')
        if not text or category not in ['bug', 'feature']:
            abort(422, 'Invalid form')
        # FIXME : Do something with the feedback data
        return Response(status=204)
    else:
        abort(406)


@frontend_component.route('/report-data', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def report_data():
    """Get Reports data from ES, using an optional ES Search dict"""
    data = request.get_json(silent=True)
    if data:
        search = data.get('search')
        start = data.get('start', 0)
        count = data.get('count', 10)
        try:
            s = DataController().get_search(search)
            result = []
            for hit in s[start:start + count]:
                elem = hit._d_  # type: dict
                elem.update({'doc_type': hit.meta.doc_type})
                result.append(elem)
            return jsonify(data={
                'total_count': s.count(),
                'data': result
            })
        except ElasticsearchException:
            logging.warning("Invalid ES query", exc_info=True)
            abort(406, "Invalid ES query")
    else:
        abort(406, "No query provided")


@frontend_component.route('/report-aggs', methods=['POST', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def report_aggs():
    """Get Aggregations from ES, using an ES Search dict"""
    data = request.get_json(silent=True)
    if data:
        search = data.get('search')
        try:
            s = DataController().get_search(search)
            result = s.execute()
            return jsonify(data={
                'total_count': s.count(),
                'aggs': result.aggregations.to_dict()
            })
        except ElasticsearchException:
            logging.warning("Invalid ES query", exc_info=True)
            abort(406, "Invalid ES query")
    else:
        abort(406, "No query provided")


@frontend_component.route('/app-data/<app_name>/<data_type>', methods=['GET', 'OPTIONS'])
@auth_required('urn:cmi_ro')
@cors()
def app_data(app_name, data_type):
    """Get app specific data"""
    data = FrontendController().get_app_data(current_identity, app_name, data_type)
    if data is not None:
        return jsonify(data=data)
    else:
        abort(406, "No such data")
