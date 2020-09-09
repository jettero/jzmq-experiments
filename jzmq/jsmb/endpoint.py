# coding: utf-8

import re
import zmq
from .util import MyRE

DEFAULT_PUBLISH_PORT = 5555
DEFAULT_COLLECTOR_PORT = 5556
DEFAULT_DIRECTED_PORT = 5557

DEFAULT_PROTO = "tcp"

DEFAULT_PORTS = (DEFAULT_PUBLISH_PORT, DEFAULT_COLLECTOR_PORT, DEFAULT_DIRECTED_PORT)
DEFAULT_PORT_STRING = ",".join([str(x) for x in DEFAULT_PORTS])

DEFAULT_ENDPOINT = f"{DEFAULT_PROTO}://*:{DEFAULT_PORT_STRING}"

_slurpies = (
    MyRE(
        r"^(?:(?P<proto>.+)://)?(?P<host>[^:/]+|\[?[a-fA-F0-9:]+\]?)(?:$|:(?P<ports>.+?)$)"
    ),
)


class Endpoint:
    """ Eescribe an endpoint

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
    proto = DEFAULT_PROTO

    def __init__(self, description):
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
                    self.pub = portz[0]
                    self.pull = portz[1]
                    self.router = portz[2]

                self.host = slurpizer["host"]

                proto = slurpizer["proto"]
                if proto:
                    self.proto = proto

    def __repr__(self):
        return f"{self.host}:[pub={self.pub} pull={self.pull} router={self.router}]"

    def port(self, ptype=zmq.PUB):
        if ptype in (zmq.PUB, zmq.SUB):
            return self.pub
        if ptype in (zmq.PULL, zmq.PUSH):
            return self.pull
        if ptype in (zmq.ROUTER, zmq.DEALER):
            return self.router
        raise ValueError(f"unknown type: {ptype}")

    def format(self, ptype=zmq.PUB):
        return f"{self.proto}://{self.host}:{self.port(ptype=ptype)}"
