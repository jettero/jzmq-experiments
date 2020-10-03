#!/usr/bin/env python
# coding: utf-8

import re
import logging
import socket
from collections import namedtuple
from jzmq import Node

log = logging.getLogger(__name__)

TEST_PORT = 5555
TARCH_NODE_COUNT = 7  # there's actually only 4 in NOTES.txt, leave some space
TEST_PORT_INCREMENT = TARCH_NODE_COUNT * Node.PORTS
FIND_PORT_MAX_TRIES = 7


def _check_ports(port, count=Node.PORTS):
    prange = (port, port + Node.PORTS)
    for _ in range(port, port + count):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", port))
            sock.listen(5)
            sock.close()
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.bind(("::1", port))
            sock.listen(5)
            sock.close()
        except socket.error as e:
            log.info(
                "portrange %d-%d seems to be in use (or something) at %d: %s",
                prange[0],
                prange[1],
                port,
                e,
            )
            return False
    return True


def _get_port(
    start=TEST_PORT,
    increment=TEST_PORT_INCREMENT,
    count=Node.PORTS,
    max_tries=FIND_PORT_MAX_TRIES,
):
    ostart = start
    for _ in range(max_tries):
        if _check_ports(start, count=count):
            return start
        start += increment
    raise Exception(
        f"unable to find a set of ports starting at {ostart}"
        "(ending near {start}) increment={increment} / count={count}"
    )


def read_node_description():
    Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "port", "endpoints"))
    tmp = dict()
    c = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    port = 5555
    with open("NOTES.txt", "r") as fh:
        port = _get_port(port)
        for line in fh:
            if "TEST_ARCH" in line:
                for lhs, rhs in c.findall(line):
                    if lhs not in tmp:
                        port = _get_port(port)
                        tmp[lhs] = Ndesc(
                            f"tarch({lhs}):{port}",
                            f"*:{port}",
                            f"localhost:{port}",
                            port,
                            list(),
                        )
                        port += 10
                    tmp[lhs].endpoints.append(rhs)
    return tmp


def generate_nodes(tarch_desc):
    tmp = list()

    log.info("creating tarch nodes")
    for node_name in tarch_desc:
        tn = tarch_desc[node_name]
        endpn = tuple(n for n in tn.endpoints)
        raddrs = tuple(tarch_desc[n].raddr for n in endpn)
        rids = tuple(tarch_desc[n].ident for n in endpn)
        log.info("creating %s → %s", tn.ident, ", ".join(rids))
        rn = Node(tn.laddr, identity=tn.ident, keyring="t/test-keyring")
        tmp.append((rn, raddrs))

    for node, raddrs in tmp:
        log.info("connecting %s to endpoints=%s", node, raddrs)
        node.connect_to_endpoints(*raddrs)

    return [x for x, _ in tmp]


def get_tarch():
    desc = read_node_description()
    return generate_nodes(desc)
