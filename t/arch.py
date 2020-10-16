#!/usr/bin/env python
# coding: utf-8

import re
import logging
from collections import namedtuple
from jzmq import Node
from jzmq.util import get_ports, increment_ports, DEFAULT_PORTS

log = logging.getLogger(__name__)
ports = DEFAULT_PORTS

TarchDesc = namedtuple("TarchDesc", ("arch", "tests"))
Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "endpoints"))


class Tdesc(namedtuple("Tdesc", ("mtype", "tag", "src", "rcpt"))):
    @property
    def msg(self):
        return self.tag

    @property
    def dst(self):
        if self.mtype != "R":
            raise TypeError("not a route")
        if len(self.rcpt) != 1:
            raise ValueError("routes must have exactly one destination")
        return self.rcpt[0]


def read_tarch_description(file="NOTES.txt"):
    global ports

    node_map = dict()
    test_list = list()
    node_connection_re = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    test_description_re = re.compile(
        r"(?P<mtype>MSG|ROUTE)(?:<(?P<tag>[^<>]*?)>)?"
        r"\((?P<src>\w+?)"
        r":(?P<rcpt>[\w,]+?)\)"
    )
    rsplit_re = re.compile(r"\s*,\s*")
    all_test = False
    lineno = 0
    with open(file, "r") as fh:
        for line in fh:
            lineno += 1
            if lineno == 1 and line.startswith("#!test-arch"):
                all_test = True
                continue
            if all_test or "TEST_ARCH" in line:
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
                for mtype, tag, src, rcpt in test_description_re.findall(line):
                    if not tag:
                        tag = "message"
                    rcpt = rsplit_re.split(rcpt)
                    mtype = mtype[0]
                    test_list.append(Tdesc(mtype[0], tag, src, rcpt))
    for node in node_map.values():
        log.debug(
            "[read desc] found node %s with endpoints %s",
            node.ident.split(":")[0],
            node.endpoints,
        )
    for test in test_list:
        log.debug("[read desc] found test %s", test)

    return TarchDesc(node_map, test_list)


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

    class Tarch(namedtuple("Tarch", tuple(tarch_desc))):
        def __getitem__(self, idx):
            if isinstance(idx, str):
                return getattr(self, idx)
            return super().__getitem__(idx)

    return Tarch(*(x for x, _ in tmp))
