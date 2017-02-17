"""
default_data.py : This data is used to populate the client database

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

default_filters = [
    dict(
        owner="system",
        filters=[
            dict(variable=5, operator=1, value="<any>")
        ],
        name="All"
    ),
    dict(
        owner="system",
        filters=[
            dict(variable=5, operator=1, value="workstation")
        ],
        name="Workstations"
    ),
    dict(
        owner="system",
        filters=[
            dict(variable=5, operator=1, value="server")
        ],
        name="Servers"
    ),
    dict(
        owner="system",
        filters=[
            dict(variable=5, operator=1, value="mobile")
        ],
        name="Mobiles"
    ),
    dict(
        owner="system",
        filters=[
            dict(variable=5, operator=1, value="server"),
            dict(variable=0, operator=3, value=""),
            dict(variable=5, operator=1, value="workstation")
        ],
        name="Computers"
    ),
]

database_template = dict(
    filter=default_filters,
)
