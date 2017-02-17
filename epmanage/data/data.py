"""
data.py : Data channels APIs

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
import logging
import os
from pathlib import Path

import arrow
from flask import Blueprint, request, abort, send_file
from flask import Response

from epmanage import settings
from epmanage.data.data_controller import DataController
from epmanage.lib.auth import auth_required, current_identity
from epmanage.lib.client import Client

data_component = Blueprint('data_component', __name__)


@data_component.route('/blob', methods=['GET'])
def data_index():
    """Dummy method for router"""
    abort(404)


@data_component.route('/blob/<blobid>', methods=['GET', 'POST'])
@auth_required('urn:data')
def data_do(blobid):
    """Get or store blobs"""
    agent = current_identity
    data_controller = DataController()

    if request.method == 'GET':
        blob = data_controller.get_blob(agent, blobid)
        if not blob:
            abort(404)
        return send_file(blob)
    else:
        result = data_controller.store_blob(agent, blobid, request.stream.read())
        if not result:
            abort(400)
        else:
            return Response(status=201)


@data_component.route('/report', methods=['POST'])
@auth_required('urn:data')
def data_report():
    """Report entry point"""
    agent = current_identity
    data_controller = DataController()
    if data_controller.store_elk(agent, request.json):
        return Response(status=201)
    else:
        abort(400)


@data_component.route('/device-state', methods=['POST'])
@auth_required('urn:data')
def data_state():
    """Report entry point"""
    agent = current_identity
    data_controller = DataController()
    if data_controller.store_state(agent, request.json):
        return Response(status=201)
    else:
        abort(400)


@data_component.route('/debug', methods=['POST'])
@auth_required('urn:data')
def data_debug():
    agent = current_identity
    data_controller = DataController()

    blobid = "error_report_{}".format(arrow.utcnow().timestamp)
    result = data_controller.store_blob(agent, blobid, request.stream.read())
    if not result:
        abort(400)
    else:
        return Response(status=201)


@data_component.route('/assets/<token>', methods=['GET'])
def data_assets(token):
    client = Client(token=token)
    if client.is_new():
        logging.warning("Attempt to download assets with invalid Client token")
        abort(403)
    else:
        osname = request.args.get('os', None)
        version = request.args.get('version', None)
        arch = request.args.get('arch', None)
        cur_hash = request.headers.get('If-None-Match', None)

        if not osname or not version or not arch:
            abort(404)

        pkg_path = Path(settings.config.PKG_PATH)
        data = json.load(open(os.path.join(settings.config.PKG_PATH, 'pkg.json')))
        assets = data.get(osname, dict()).get("assets", [])
        pkgs = [x for x in assets if x.get('version') == version and x.get('arch') == arch]
        if not pkgs:
            abort(404)

        name = [x for x in pkgs[0]['hash'] if x['type'] == 'sha256'][0]['value']

        if cur_hash and cur_hash == name:
            return Response(status=304)

        path = pkg_path / name
        try:
            path.relative_to(pkg_path)
        except ValueError:
            abort(404)

        rsp = send_file(str(path.absolute()))
        return rsp
