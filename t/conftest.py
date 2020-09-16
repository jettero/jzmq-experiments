# coding: utf-8

from collections import namedtuple
import re
import pytest
from jzmq import StupidNode, Endpoint

@pytest.fixture
def always_true():
    return True

@pytest.fixture(scope='session')
def tarch_desc():
    Ndesc = namedtuple('Ndesc', ('port', 'endpoints'))
    tmp = dict()
    c = re.compile(r'\b(?P<lhs>[A-Z])\s*→\s*(?P<rhs>[A-Z])\b')
    port = 5555
    with open('NOTES.txt', 'r') as fh:
        for line in fh:
            if 'TEST_ARCH' in line:
                items = c.findall(line)
                for lhs,rhs in c.findall(line):
                    if lhs not in tmp:
                        tmp[lhs] = Ndesc(port, list())
                        port += 11
                    tmp[lhs].endpoints.append(rhs)
    return tmp

@pytest.fixture(scope='function')
def tarch(tarch_desc):
    names = tuple(sorted(tarch_desc))
    Nodes = namedtuple('Nodes', names)
    result = Nodes( StupidNode(f'*:{tarch_desc[x].port}') for x in names )

    for x in names:
        n = getattr(result, x)
        for e in tarch_desc[x].endpoints:
            n.connect_to_endpoint(f'localhost:{tarch_desc[e].port}')

    return result
