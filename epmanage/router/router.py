"""
router.py : Route management

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
from flask import Blueprint, request, abort, url_for, jsonify

from epmanage.lib.auth import auth_required, current_identity

router_component = Blueprint('router_component', __name__)


@router_component.route('/list', methods=['GET'])
@auth_required('urn:router', optional=True)
def route_get():
    """Get some code"""
    if not current_identity and request.args.get('auth'):
        abort(401)  # Force auth if auth param is on

    # No identity, just return authentication servers
    if not current_identity:
        return jsonify(
            auth=[url_for('auth_component.auth_do', _external=True)],
            enroll=[url_for('auth_component.enroll_do', _external=True)],
        )
    else:
        return jsonify(
            auth=[url_for('auth_component.auth_do', _external=True)],
            code_manifest=[url_for('code_component.code_get_manifest', _external=True)],
            code_pkg=[url_for('code_component.code_get', _external=True)],
            task=[url_for('task_component.task_get', _external=True)],
            data_blob=[url_for('data_component.data_index', _external=True)],
            data_report=[url_for('data_component.data_report', _external=True)],
            data_state=[url_for('data_component.data_state', _external=True)],
            traceback=[url_for('data_component.data_debug', _external=True)],
            shell=[url_for('index', _external=True)],
        )
