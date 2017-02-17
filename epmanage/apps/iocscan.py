"""
iocscan.py : Reporting component for IOCScanner

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
import pymongo

from epmanage.lib.client import Client
from epmanage.utils import Cache


class IocscanReporting(object):
    @staticmethod
    def get_detections(token: str):
        value = Cache().get('iocscan_detections_{}'.format(token))
        if value:
            return value
        # FIXME: do elasticsearch query
        value = 42
        Cache().set('iocscan_detections_{}'.format(token), value, tag='report_data')
        return value

    @staticmethod
    def get_most_infected(client: Client):
        most_infected = Cache().get('iocscan_most_infected_{}'.format(client.token))
        if most_infected:
            return most_infected

        most_infected = []
        agentdb = client.db()['agent']
        most_infected_agents = agentdb.find().sort('device_state.iocscan.detect_count', pymongo.DESCENDING).limit(10)
        for agent in most_infected_agents:
            try:
                detect_count = agent['device_state']['iocscan']['detect_count']
                if detect_count:
                    most_infected.append({
                        'hostname': agent['hostname'],
                        'uuid': agent['uuid'],
                        'count': detect_count
                    })
            except KeyError:
                pass

        Cache().set('iocscan_most_infected_{}'.format(client.token), most_infected, tag='report_data', expire=3600)
        return most_infected


def get_dashboard_data(app: dict, client: Client) -> dict:
    return dict(
        key=app['name'],
        title=app['title'],
        menu=[
            dict(
                text='Analytics',
                link='/',
            ),
            dict(
                text='Detections',
                link='/detections',
                type='error',
                count=IocscanReporting.get_detections(client.token)
            ),
            dict(
                text='Explore data',
                link='/all',
            )
        ]
    )


def get_data_most_infected(client: Client):
    return IocscanReporting.get_most_infected(client)
