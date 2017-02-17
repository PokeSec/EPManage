"""
task.py : Task distribution logic

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
from pathlib import Path
from typing import Optional

from epmanage.lib.app import App
from epmanage.lib.auth import Identity
from epmanage.lib.filter import Filter
from epmanage.settings import Config


class TaskController(object):
    """Frontend logic"""

    def __init__(self):
        self.actiondb = None

    def get_tasks(self, agent: Identity, report: dict) -> Optional[dict]:
        """
        Get the tasks for the specified agent
        :param agent: the agent Identity
        :param report: report from the endpoint (running tasks)
        """
        if not agent:
            return None

        if not report:
            report = dict()

        # TODO: Use report
        logging.info("Report from %s : %s", agent.get_agent().uuid, report)

        data = dict(
            active=dict(),
            stop=[],
        )

        if not self.actiondb:
            self.actiondb = agent.get_client().db()['action']

        tasks = dict()

        for action in self.actiondb.find():
            flt = Filter(name=action['filter'])
            app = App(uappid=action['app_id'])
            if flt.is_new() or app.is_new() or not flt.is_applicable(agent):
                continue
            if app.name not in tasks:
                tasks[app.name] = dict(
                    app=app.name,
                    module='{module}.{module}'.format(module=app.name),
                    configs=[]
                )
            config = app.get_config(action.get('config'))
            if config is None:
                continue

            schedule = config.pop('schedule', None)
            if schedule and schedule in ['daily', 'weekly', 'monthly']:
                schedule = dict(
                    type='period',
                    value1=schedule
                )
            if action.get('schedule'):
                schedule = action.get('schedule')

            config['_schedule'] = schedule
            config['task_id'] = str(action['_id'])

            if config is not None:
                tasks[app.name]['configs'].append(config)

        for name, task in tasks.items():
            data['active'][name] = task

        task_override = Path(Config().TASKS_PATH) / agent.get_agent().uuid
        if task_override.exists():
            try:
                data.update(json.load(task_override.open()))
            except:
                pass

        logging.debug("Tasks for %s : %s", agent.get_agent().uuid, data)

        return data
