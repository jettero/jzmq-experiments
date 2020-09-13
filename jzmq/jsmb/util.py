#!/usr/bin/env python
# coding: utf-8

import re
import zmq

# NOTE: I'd really rather use a definition from zmq for this list of
# candidates...  or better yet, a built in that can translate back form
# numbers to the constant name...
#
# but the only place where this list of words occurs together (near as I
# can tell) is zmq.utils.constant_names.base_name and it has versions,
# polling directions, thread priorities and all sorts of other shit, with
# the socket type names thrown in the middle of the list.
#
# I just cut and pasted that part of the list out into this global... if
# there's a better way, please submit patch or otherwise let me know.

ZMQ_SOCKET_TYPE_NAMES = (
    "PAIR",
    "PUB",
    "SUB",
    "REQ",
    "REP",
    "DEALER",
    "ROUTER",
    "XREQ",
    "XREP",
    "PULL",
    "PUSH",
    "XPUB",
    "XSUB",
    "UPSTREAM",
    "DOWNSTREAM",
    "STREAM",
    "SERVER",
    "CLIENT",
    "RADIO",
    "DISH",
    "GATHER",
    "SCATTER",
    "DGRAM",
)


def zmq_socket_type_name(socket_type_number):
    for item in ZMQ_SOCKET_TYPE_NAMES:
        try:
            if socket_type_number == getattr(zmq, item):
                return f"zmq.{item}"
        except AttributeError:
            pass
    return "zmq.?UNKNOWN?"


class MyRE:
    h = _m = None

    @property
    def m(self):
        return self._m

    @m.setter
    def m(self, v):
        self._m = v
        self.h = None

    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def match(self, *a, **kw):
        self.m = self.pattern.match(*a, **kw)
        return self.m

    def search(self, *a, **kw):
        self.m = self.pattern.search(*a, **kw)
        self.h = None
        return self.m

    def group(self, *a, **kw):
        return self.m.group(*a, **kw)

    def groups(self, *a, **kw):
        return self.m.groups(*a, **kw)

    def groupdict(self, *a, **kw):
        return self.m.groupdict(*a, **kw)

    def __getitem__(self, name, default=None):
        if isinstance(name, int):
            return self.group(name)
        if self.h is None:
            self.h = self.groupdict()
        return self.h.get(name, default)

    def __bool__(self):
        return bool(self.m)

    def __iter__(self):
        yield from self.groups()

    def __repr__(self):
        ret = f"MyRE({self.pattern.pattern}"
        if self.m:
            ret += " MATCHED"
            g = self.groups()
            if g:
                ret += f" groups={g}"
            h = self.groupdict()
            if h:
                ret += f" named_groups={h}"
        return ret + ")"

class CallOnEachFactory(dict):
    class CallOnEach:
        def __init__(self, calltable, name):
            self.calltable = calltable
            self.name = name

        def __call__(self, *a, **kw):
            ret = dict()
            for k, v in self.calltable.items():
                ret[k] = v(*a, **kw)
            return ret

        def __repr__(self):
            return f'CallOnEach< {list(self.calltable)}.{self.name}() >'

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError as e:
            nevermind = e

        try:
            collected = dict()
            for k,v in self.items():
                ga = getattr(v, name)
                if callable(ga):
                    collected[k] = ga
                else:
                    raise nevermind
            return self.CallOnEach(collected, name)
        except AttributeError:
            raise nevermind
