#!/usr/bin/env python
# coding: utf-8

import re
import zmq
from .nicknames import NicknamesMixin
from .util import MyRE

DEFAULT_PUBLISH_PORT = 5555
DEFAULT_COLLECTOR_PORT = 5556
DEFAULT_DIRECTED_PORT = 5557

DEFAULT_PROTO = "tcp"

_slurpies = (MyRE(r"(?P<host>[^:]+|\[?[a-fA-F0-9:]+\]?)(?:$|:(?P<ports>.+?)$)"),)


class Endpoint(NicknamesMixin):
    host = "localhost"

    pub = 5555
    pull = 5556
    router = 5557
    proto = DEFAULT_PROTO

    _nicknames = {
        "pub": "publish",
        "sub": ("subscriber", "subscribe"),
        "pull": ("collector", "collect", "col"),
        "router": ("directed", "director", "dir"),
    }

    def __init__(
        self,
        host,
        publish_port=DEFAULT_PUBLISH_PORT,
        collector_port=DEFAULT_COLLECTOR_PORT,
        directed_port=DEFAULT_DIRECTED_PORT,
        proto=DEFAULT_PROTO,
    ):

        self.host = host
        self.pub = publish_port
        self.pull = collector_port
        self.router = directed_port
        self.proto = proto

    def __repr__(self):
        return f"{self.host}:[pub={self.pub} pull={self.pull} router={self.router}]"

    def port(self, ptype=zmq.PUB):
        if ptype == zmq.PUB:
            return self.pub
        if ptype == zmq.PULL:
            return self.pull
        if ptype == zmq.ROUTER:
            return self.router
        raise ValueError(f"unknown type: {ptype}")

    def format(self, ptype=zmq.PUB):
        return f"{self.proto}://{self.host}:{self.port(ptype=ptype)}"

    @classmethod
    def slurp(cls, description):
        for slurpizer in _slurpies:
            if slurpizer.match(description):

                def _portz(s):
                    if s:
                        for x in re.split(r"\D+", s):
                            try:
                                yield int(x)
                            except TypeError:
                                pass

                portz = list(_portz(slurpizer["ports"]))
                if portz:
                    while len(portz) < 3:
                        portz.append(portz[-1] + 1)
                    pub, pull, router = portz[0:3]
                else:
                    pub = DEFAULT_PUBLISH_PORT
                    pull = DEFAULT_COLLECTOR_PORT
                    router = DEFAULT_DIRECTED_PORT
                return cls(slurpizer["host"], pub, pull, router)
