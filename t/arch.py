#!/usr/bin/env python
# coding: utf-8

import re
import logging
from collections import namedtuple
from jzmq import Node
from jzmq.util import check_ports

log = logging.getLogger(__name__)

TEST_PORT = 5555
TARCH_NODE_COUNT = 7  # there's actually only 4 in NOTES.txt, leave some space
TEST_PORT_INCREMENT = TARCH_NODE_COUNT * Node.PORTS
FIND_PORT_MAX_TRIES = 7


def _get_port(
    start=TEST_PORT,
    increment=TEST_PORT_INCREMENT,
    count=Node.PORTS,
    max_tries=FIND_PORT_MAX_TRIES,
):
    ostart = start
    for _ in range(max_tries):
        if check_ports(start, count=count):
            return start
        start += increment
    raise Exception(
        f"unable to find a set of ports starting at {ostart}"
        "(ending near {start}) increment={increment} / count={count}"
    )


def read_node_description(file="NOTES.txt"):
    Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "port", "endpoints"))
    tmp = dict()
    c = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    port = 5555
    with open(file, "r") as fh:
        for line in fh:
            if "TEST_ARCH" in line:
                for lhs, rhs in c.findall(line):
                    for _hs in (lhs, rhs):
                        if _hs not in tmp:
                            port = _get_port(port)
                            tmp[_hs] = Ndesc(
                                f"tarch({_hs}):{port}",
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


def get_tarch(file="NOTES.txt"):
    desc = read_node_description(file=file)
    return generate_nodes(desc)
