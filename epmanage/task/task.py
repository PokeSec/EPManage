"""
task.py : Scheduler

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
from flask import Blueprint, request, jsonify

from epmanage.lib.auth import auth_required, current_identity
from epmanage.task.task_controller import TaskController

task_component = Blueprint('task_component', __name__)


@task_component.route('/', methods=['POST'])
@auth_required('urn:task')
def task_get():
    """Get tasks to do"""
    current_report = request.json

    task_controller = TaskController()
    agent = current_identity
    tasks = task_controller.get_tasks(agent, current_report)
    return jsonify(tasks)
