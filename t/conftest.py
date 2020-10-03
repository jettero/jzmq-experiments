# coding: utf-8
# pylint: disable=redefined-outer-name

import time
import logging
from collections import namedtuple
import pytest
import t.arch

log = logging.getLogger(__name__)


@pytest.fixture
def always_true():
    return True


@pytest.fixture(scope="session")
def tarch_desc():
    return t.arch.read_node_description()


@pytest.fixture(scope="function")
def tarch(tarch_desc, tarch_names):
    Nodes = namedtuple("Nodes", tarch_names)

    log.info("created tarch nodes")
    nodes = Nodes(*t.arch.generate_nodes(tarch_desc))

    time.sleep(1)  # give everything a sec to connect
    yield nodes

    log.info("destroying tarch nodes")
    for node in nodes:
        node.closekill()

@pytest.fixture(scope='session')
def tarch_names(tarch_desc):
    return tuple(sorted(tarch_desc))


def pytest_addoption(parser):
    """ in order to disable (eg) zmq.auth when using debug loglevel:

        pytest --log-disable zmq.auth --log-cli-level debug t/
    """
    parser.addoption(
        "--log-disable", action="append", default=[], help="disable specific loggers"
    )


def pytest_configure(config):
    for name in config.getoption("--log-disable", default=[]):
        logger = logging.getLogger(name)
        logger.propagate = False
