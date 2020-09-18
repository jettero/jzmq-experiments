# coding: utf-8
# pylint: disable=redefined-outer-name

import logging
from collections import namedtuple
import re
import socket
import pytest
from jzmq import StupidNode

log = logging.getLogger(__name__)

TEST_PORT = 5555
TARCH_NODE_COUNT = 7  # there's actually only 4 in NOTES.txt, leave some space
TEST_PORT_INCREMENT = TARCH_NODE_COUNT * StupidNode.PORTS
FIND_PORT_MAX_TRIES = 7


@pytest.fixture
def always_true():
    return True


def _check_ports(port, count=StupidNode.PORTS):
    prange = (port, port + StupidNode.PORTS)
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
    count=StupidNode.PORTS,
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


@pytest.fixture(scope="session")
def tarch_desc():
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


def _generate_nodes(tarch_desc):
    tmp = list()

    log.info("creating tarch nodes")
    for node_name in tarch_desc:
        tn = tarch_desc[node_name]
        endpn = tuple(n for n in tn.endpoints)
        raddrs = tuple(tarch_desc[n].raddr for n in endpn)
        rids = tuple(tarch_desc[n].ident for n in endpn)
        log.info("creating %s → %s", tn.ident, ", ".join(rids))
        tmp.append(
            (StupidNode(tn.laddr, identity=tn.ident, keyring="t/test-keyring"), raddrs)
        )

    for node, raddrs in tmp:
        log.info("connecting %s to endpoints=%s", node, raddrs)
        node.connect_to_endpoints(*raddrs)

    return [x for x, _ in tmp]


@pytest.fixture(scope="function")
def tarch(tarch_desc):
    Nodes = namedtuple("Nodes", sorted(tarch_desc))

    log.info("created tarch nodes")
    nodes = Nodes(*_generate_nodes(tarch_desc))

    yield nodes

    log.info("destroying tarch nodes")
    for node in nodes:
        node.closekill()
