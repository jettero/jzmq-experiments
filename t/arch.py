#!/usr/bin/env python
# coding: utf-8

import re
import logging
from collections import namedtuple
from jzmq import Node
from jzmq.util import get_ports, increment_ports, DEFAULT_PORTS

log = logging.getLogger(__name__)


def read_node_description(file="NOTES.txt"):
    Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "endpoints"))
    tmp = dict()
    c = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    ports = DEFAULT_PORTS
    with open(file, "r") as fh:
        for line in fh:
            if "TEST_ARCH" in line:
                for lhs, rhs in c.findall(line):
                    for _hs in (lhs, rhs):
                        if _hs not in tmp:
                            ports = get_ports(increment_ports(ports))
                            pstring = ",".join(str(x) for x in ports)
                            tmp[_hs] = Ndesc(
                                f"tarch({_hs}):{pstring}",
                                f"*:{pstring}",
                                f"localhost:{pstring}",
                                list(),
                            )
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
