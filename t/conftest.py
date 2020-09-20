# coding: utf-8
# pylint: disable=redefined-outer-name

import logging
from collections import namedtuple
import re
import pytest
from jzmq import StupidNode
import t.tarch

log = logging.getLogger(__name__)


@pytest.fixture
def always_true():
    return True


@pytest.fixture(scope="session")
def tarch_desc():
    return t.tarch.read_node_description()


@pytest.fixture(scope="function")
def tarch(tarch_desc):
    Nodes = namedtuple("Nodes", sorted(tarch_desc))

    log.info("created tarch nodes")
    nodes = Nodes(*t.tarch.generate_nodes(tarch_desc))

    yield nodes

    log.info("destroying tarch nodes")
    for node in nodes:
        node.closekill()
