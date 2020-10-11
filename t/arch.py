#!/usr/bin/env python
# coding: utf-8

import re
import logging
from collections import namedtuple
from jzmq import Node
from jzmq.util import get_ports, increment_ports, DEFAULT_PORTS

log = logging.getLogger(__name__)
ports = DEFAULT_PORTS


def read_tarch_description(file="NOTES.txt"):
    global ports
    Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "endpoints"))
    Tdesc = namedtuple("Tdesc", ("msg", "source", "recipients"))
    node_map = dict()
    test_list = list()
    node_connection_re = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    test_description_re = re.compile(
        r"MSG(?:<(?P<msg_tag>[^<>]*?)>)?\((?P<source>[^:]+?):(?P<recipients>.+?)\)"
    )
    rsplit_re = re.compile(r"\s*,\s*")
    with open(file, "r") as fh:
        for line in fh:
            if "TEST_ARCH" in line:
                for lhs, rhs in node_connection_re.findall(line):
                    for _hs in (lhs, rhs):
                        if _hs not in node_map:
                            ports = get_ports(increment_ports(ports))
                            pstring = ",".join(str(x) for x in ports)
                            node_map[_hs] = Ndesc(
                                f"tarch({_hs}):{pstring}",
                                f"*:{pstring}",
                                f"localhost:{pstring}",
                                list(),
                            )
                    node_map[lhs].endpoints.append(rhs)
                for msg, source, recipients in test_description_re.findall(line):
                    if not msg:
                        msg = "message"
                    recipients = rsplit_re.split(recipients)
                    test_list.append(Tdesc(msg, source, recipients))
    return node_map, test_list


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
    tarch_desc, test_desc = read_tarch_description(file=file)
    return generate_nodes(tarch_desc), test_desc
