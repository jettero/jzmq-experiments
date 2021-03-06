# coding: utf-8

import re
import zmq
from .util import MyRE
from .const import *

_slurpies = (
    MyRE(
        r"^(?:(?P<proto>.+)://)?(?P<host>[^:/]+|\[?[a-fA-F0-9:]+\]?)(?:$|:(?P<ports>.+?)$)"
    ),
)


class Endpoint:
    """Describe an endpoint

    The single argument 'description' is any of the following

    * a hostname (or a star, etc)
    * an IP address
    * an address and port pair (e.g. host:5555)
    * an address and port list (e.g., host:5555,5556,5557)
    * a whole URL (e.g., tcp://host:555), which can also have a port list

    Any specified ports drop into slots in this order:

    * PUBLISH_PORT (default 5555)
    * COLLECTOR_PORT (default 5556)
    * DIRECTED_PORT (default 5557)

    If any but not all ports are specified in the endpoint string, the next
    values in the series are incremented from the last specified.  That is,
    'host:80' implies 'host:80,81,82' and 'host:80,85' implies
    'host:80,85,86'.
    """

    host = "localhost"

    pub = DEFAULT_PUBLISH_PORT
    pull = DEFAULT_COLLECTOR_PORT
    router = DEFAULT_DIRECTED_PORT
    rep = DEFAULT_CLEARTEXT_PORT
    proto = DEFAULT_PROTO

    _port_names = ("pub", "pull", "router", "rep")
    _xlate_ntoa = {
        "pub": (zmq.PUB, zmq.SUB),
        "pull": (zmq.PULL, zmq.PUSH),
        "router": (zmq.ROUTER, zmq.DEALER),
        "rep": (zmq.REP, zmq.REQ),
    }
    _xlate_aton = dict((v, k) for k, v in _xlate_ntoa.items())

    def __init__(self, description, identity=None):
        for slurpizer in _slurpies:
            if slurpizer.match(description):

                def portz_(s):
                    if s:
                        for x in re.split(r"\D+", s):
                            try:
                                yield int(x)
                            except TypeError:
                                pass

                portz = list(portz_(slurpizer["ports"]))
                if portz:
                    while len(portz) < len(self._port_names):
                        portz.append(portz[-1] + 1)
                    for k, v in zip(self._port_names, portz):
                        setattr(self, k, v)

                self.host = slurpizer["host"]

                proto = slurpizer["proto"]
                if proto:
                    self.proto = proto
        self.identity = identity

    def __repr__(self):
        if self.identity is not None:
            return str(self.identity)
        return f"{self.host}:[pub={self.pub} pull={self.pull} router={self.router}]"

    def port(self, ptype=zmq.PUB):
        if ptype in (zmq.PUB, zmq.SUB):
            return self.pub
        if ptype in (zmq.PULL, zmq.PUSH):
            return self.pull
        if ptype in (zmq.ROUTER, zmq.DEALER):
            return self.router
        if ptype in (zmq.REP, zmq.REQ):
            return self.rep
        raise ValueError(f"unknown type: {ptype}")

    def format(self, ptype=zmq.PUB):
        return f"{self.proto}://{self.host}:{self.port(ptype=ptype)}"
