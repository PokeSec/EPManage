"""
auth.py : Authentication APIs

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
from flask import Blueprint, request, abort

from epmanage.lib.auth import AuthController, AuthException

auth_component = Blueprint('auth_component', __name__)


@auth_component.route('/', methods=['POST'])
def auth_do():
    """Perform authentication"""
    try:
        return AuthController.get_token_agent(request.json)
    except AuthException:
        abort(503)
    except:
        abort(503)


@auth_component.route('/enroll', methods=['POST'])
def enroll_do():
    """Perform enrollment"""
    try:
        return AuthController.enroll_agent(request.json)
    except AuthException:
        abort(503)
    except:
        abort(503)
