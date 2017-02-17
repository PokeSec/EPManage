"""
code.py : Code management APIs

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
from flask import Blueprint, request, abort, Response

from epmanage.code.manifest import ManifestController
from epmanage.lib.auth import auth_required, current_identity

code_component = Blueprint('code_component', __name__)


def get_arch_folder():
    """Get the folder for BIN_PATH"""
    agent = current_identity

    if agent['os'] == 'win32':
        return '{}_{}'.format('win', agent['arch'])
    elif agent['os'] == 'unix':
        return '{}_{}'.format(agent['osversion'], agent['arch'])
    elif agent['os'] == 'android':
        return 'android_arm'
    else:
        return 'unk'


@code_component.route('/pkg', methods=['GET'])
@auth_required('urn:code')
def code_get():
    """Get some code"""
    pkg = request.args.get('id')
    if not pkg:
        abort(404)
    mmanager = ManifestController(get_arch_folder())

    data = mmanager.get_pkg(pkg)
    if not data:
        abort(404)
    resp = Response(response=data,
                    status=200,
                    mimetype="application/epccode")
    resp.cache_control.max_age = 3600 * 24 * 30
    return resp


@code_component.route('/manifest', methods=['GET'])
@auth_required('urn:code')
def code_get_manifest():
    mmanager = ManifestController(get_arch_folder())

    try:
        cur = int(request.args.get('cur'))
        if cur > 0 and cur == mmanager.get_timestamp():
            return Response(status=304)
    except ValueError:
        abort(404)

    resp = Response(response=mmanager.get_data(),
                    status=200,
                    mimetype="application/epmanifest")
    resp.cache_control.max_age = 300
    return resp
