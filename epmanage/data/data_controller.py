"""
data.py : Data logic

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

from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch_dsl import Search
from eve.utils import config
from flask import safe_join

from epmanage.lib.auth import current_identity
from epmanage.utils import Singleton


class DataController(metaclass=Singleton):
    """Data logic"""

    def __init__(self):
        self.es = Elasticsearch(hosts=config.ELASTIC_HOSTS)

        pass

    def store_blob(self, agent, blobid, data):
        """Store a blob"""
        try:
            fdir = Path(config.AGENTBLOB_PATH) / agent.uuid
            fdir.mkdir(mode=0o750, exist_ok=True)
            fpath = Path(safe_join(str(fdir), blobid))
            fpath.write_bytes(data)
            return True
        except:
            return False

    def get_blob(self, agent, blobid):
        """Get a blob"""
        fpath = Path(safe_join(config.BLOB_PATH, blobid))
        try:
            return fpath.open(mode='rb')
        except FileNotFoundError:
            return None

    def store_elk(self, agent, data):
        index = "report-{}".format(agent.get_client().token).lower()
        agent_data = dict()
        for item in ['hostname', 'uuid', 'os', 'osversion', 'arch', 'ostype', 'tags']:
            agent_data['agent_{}'.format(item)] = agent[item]

        try:
            self.es.indices.create(index=index, ignore=400)
            for line in data:
                line.update(agent_data)
                self.es.index(
                    index=index,
                    doc_type=line.pop('_key', 'unknown'),
                    body=line)
            return True
        except ElasticsearchException:
            logging.exception("Elasticsearch exception")
            return False

    def store_state(self, agent, data):
        agent = agent.get_agent()
        if not agent:
            return False
        ret = agent.set_state(data)
        if ret:
            agent.save()
        return ret

    def get_search(self, search: dict = None):
        """Get Search object from ElasticSearch"""
        if not current_identity:
            return None
        else:
            try:
                index = "report-{}".format(current_identity.get_client().token).lower()
                s = Search(using=self.es, index=index)
                if search:
                    s.update_from_dict(search)
                return s
            except ElasticsearchException:
                logging.exception("Elasticsearch exception")
                return None
