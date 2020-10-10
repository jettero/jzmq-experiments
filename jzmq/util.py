#!/usr/bin/env python
# coding: utf-8

import re
import os
import time
import logging
import socket
import zmq

from .const import *

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

log = logging.getLogger(__name__)


def zmq_socket_type_name(socket_type_number):
    if isinstance(socket_type_number, zmq.Socket):
        socket_type_number = socket_type_number.type
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


def check_ports(
    ports=DEFAULT_PORTS,
    bind_addr4="127.0.0.1",
    bind_addr6="::1",
    refuse_after=5,
    sleep_after_check=os.environ.get('JZMQ_PORT_CHECK_SLEEP'),
    proto=DEFAULT_PROTO,
    check_inet4=not os.environ.get('JZMQ_SKIP_INET4_PORT_CHECKS'),
    check_inet6=not os.environ.get('JZMQ_SKIP_INET6_PORT_CHECKS'),
):
    try:
        sleep_after_check = float(sleep_after_check)
    except:
        sleep_after_check = 0

    if proto.lower() == "udp":
        proto = socket.SOCK_DGRAM
    elif proto.lower() == "tcp":
        proto = socket.SOCK_STREAM

    if not isinstance(proto, socket.SocketKind):  # pylint: disable=no-member
        raise TypeError(
            "try proto='udp'/proto='tcp' or a socket.SocketKind (eg socket.SOCK_STREAM)"
        )

    for p in ports:
        try:
            if check_inet4:
                sock = socket.socket(socket.AF_INET, proto)
                sock.bind((bind_addr4, p))
                sock.listen(refuse_after)
                sock.close()
            if check_inet6:
                sock = socket.socket(socket.AF_INET6, proto)
                sock.bind((bind_addr6, p))
                sock.listen(refuse_after)
                sock.close()
        except socket.error as e:
            log.info(
                "portrange %d-%d seems to be in use (or something) at %d: %s",
                ports[0],
                ports[-1],
                p,
                e,
            )
            return False
        finally:
            if sleep_after_check > 0:
                # this happens whether we return False (except:above) or True (below)
                log.info('sleeping for %s seconds to free up checked ports', sleep_after_check)
                time.sleep(sleep_after_check)
    return True


def increment_ports(ports):
    """ try to increment the given ports in such a way that they keep the same inter-spacing """

    def weird():
        m = max(ports)
        for i in (1,) + tuple(y - x for x, y in zip(ports, ports[1:])):
            m = m + i
            yield m

    return tuple(weird())


def get_ports(ports=DEFAULT_PORTS, proto=DEFAULT_PROTO, max_tries=10):
    oports = ports
    for _ in range(max_tries):
        if check_ports(ports, proto=proto):
            return ports
        ports = increment_ports(ports)
    raise Exception(
        f"unable to find a set of ports starting at {oports} (ending near {ports})"
    )
