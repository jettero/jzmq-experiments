# coding: utf-8

import logging
from collections import namedtuple
import re
import pytest
from jzmq import StupidNode, Endpoint

log = logging.getLogger(__name__)


@pytest.fixture
def always_true():
    return True


@pytest.fixture(scope="session")
def tarch_desc():
    Ndesc = namedtuple("Ndesc", ("ident", "laddr", "raddr", "port", "endpoints"))
    tmp = dict()
    c = re.compile(r"\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b")
    port = 5555
    with open("NOTES.txt", "r") as fh:
        for line in fh:
            if "TEST_ARCH" in line:
                items = c.findall(line)
                for lhs, rhs in c.findall(line):
                    if lhs not in tmp:
                        tmp[lhs] = Ndesc(
                            f"tarch({lhs}):{port}",
                            f"*:{port}",
                            f"localhost:{port}",
                            port,
                            list(),
                        )
                        port += 11
                    tmp[lhs].endpoints.append(rhs)
    return tmp


def _generate_nodes(tarch_desc):
    tmp = list()

    log.info("creating tarch nodes")
    for node_name in tarch_desc:
        tn = tarch_desc[node_name]
        endpn = tuple(n for n in tn.endpoints)
        raddrs = tuple(tarch_desc[n].raddr for n in endpn)
        rids = tuple(tarch_desc[n].ident for n in endpn)
        log.info("creating %s → %s", tn.ident, ", ".join(rids))
        tmp.append((StupidNode(tn.laddr, identity=tn.ident, keyring="t/test-keyring"), raddrs))

    for node,raddrs in tmp:
        log.info("connecting %s to endpoints=%s", node, raddrs)
        node.connect_to_endpoints(*raddrs)

    return [ x for x,_ in tmp ]


@pytest.fixture(scope="function")
def tarch(tarch_desc):
    Nodes = namedtuple("Nodes", sorted(tarch_desc))

    log.info("created tarch nodes")
    nodes = Nodes(*_generate_nodes(tarch_desc))

    yield nodes

    log.info("destroying tarch nodes")
    for node in nodes:
        node.closekill()
