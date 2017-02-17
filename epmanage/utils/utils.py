"""
utils.py : Common utilities for agentlib

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
from functools import wraps

from flask import make_response
from flask import request, Response

import epmanage.settings as settings


class Singleton(type):
    """Singleton metaclass"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def cors(expose=None):
    """Decorator for CORS"""

    def decorator(f):
        """Actual decorator"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            """Decorator internals"""
            rule = request.url_rule
            if request.method == 'OPTIONS' and 'Origin' in request.headers:
                rsp = Response()
                rsp.headers['Access-Control-Allow-Origin'] = ','.join(settings.config.X_DOMAINS)
                rsp.headers['Access-Control-Allow-Headers'] = ','.join(settings.config.X_HEADERS)
                rsp.headers['Access-Control-Allow-Methods'] = ','.join([x for x in rule.methods if x != 'OPTIONS'])
                return rsp
            else:
                rsp = make_response(f(*args, **kwargs))
                if 'Origin' in request.headers:
                    rsp.headers['Access-Control-Allow-Origin'] = ','.join(settings.config.X_DOMAINS)
                    if expose:
                        rsp.headers['Access-Control-Expose-Headers'] = ','.join(expose)
                return rsp

        return decorated_function

    return decorator


SYMBOLS = {
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa', 'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi', 'zebi', 'yobi'),
}


def bytes2human(n, fmt='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on fmt.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return fmt % locals()
    return fmt % dict(symbol=symbols[0], value=n)


def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.
    """
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]: 1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i + 1) * 10
    return int(num * prefix[letter])
