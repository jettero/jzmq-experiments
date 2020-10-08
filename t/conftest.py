# coding: utf-8
# pylint: disable=redefined-outer-name

import os
import time
import logging
from glob import glob
from collections import namedtuple
import zmq
import jzmq
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

    time.sleep(0.1)  # give everything an instant to connect
    yield nodes

    log.info("destroying tarch nodes")
    for node in nodes:
        node.closekill()


@pytest.fixture(scope="session")
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

def _create_tarch_fixture(file):
    base = os.path.basename(file)
    name = base[:-4]
    arch_desc = t.arch.read_node_description(file=file)
    node_names = tuple(sorted(arch_desc))
    def loader():
        nodes = t.arch.generate_nodes(arch_desc)
        ret = namedtuple(name.capitalize(), node_names)(*nodes)
        yield ret
        for item in ret:
            item.closekill()
    log.debug('creating fixture %s from %s', name, file)
    globals()[name] = pytest.fixture(scope='function', name=name)(loader)

log.debug('looking for tarch resources')
for item in glob('t/resource/tarch/*.txt'):
    log.debug('found tarch descriptor file %s', item)
    _create_tarch_fixture(item)


######################### PROFILING
# To enable this, simply set JZMQ_PROFILE=1 in your environment
#
# Although, the profiling will fail if you do not have the following installed:
#   0. pstats, cProfile (should just come with python3)
#   1. gprof2dot (pip install gprof2dot)
#   2. dot (likely to be part of your system graphviz install)
#

prof_filenames = set()
tests_dir = os.path.dirname(os.path.realpath(__file__))
output_dir = os.path.join(tests_dir, 'output')
jzmq_dir = os.path.dirname(jzmq.__file__)
zmq_dir = os.path.dirname(zmq.__file__)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if os.environ.get('JZMQ_PROFILE'):
        import cProfile
        filename, lineno, funcname = item.location # item.name is just the function name
        profile_name = filename.split('/')[-1][:-3]
        profile_name += '-' + funcname + '.pstats'
        prof_filename = os.path.join(output_dir, profile_name)
        prof_filenames.add(prof_filename)
        try:
            os.makedirs(output_dir)
        except OSError:
            pass
        prof = cProfile.Profile(builtins=False)
        prof.enable()

    yield

    if os.environ.get('JZMQ_PROFILE'):
        prof.disable()
        prof.dump_stats(prof_filename)
        prof_filenames.add(prof_filename)

def pytest_sessionfinish(session, exitstatus):
    if os.environ.get('JZMQ_PROFILE'):
        import pstats
        import subprocess
        # lifted from hubblestack tests/unittests/conftest
        # which was itself lifted from pytest-profiling
        if prof_filenames:
            combined = None
            for pfname in prof_filenames:
                if not os.path.isfile(pfname):
                    continue
                if combined is None:
                    combined = pstats.Stats(pfname)
                else:
                    combined.add(pfname)

            if combined:
                cfilename = os.path.join(output_dir, 'combined.pstats')
                csvg      = os.path.join(output_dir, 'combined.svg')
                combined.dump_stats(cfilename)

                gp_cmd = [ 'gprof2dot', '-f', 'pstats',
                    '-p', tests_dir, '-p', zmq_dir, '-p', jzmq_dir,
                    cfilename ]

                gp = subprocess.Popen(gp_cmd, stdout=subprocess.PIPE)
                dp = subprocess.Popen(['dot', '-Tsvg', '-o', csvg], stdin=gp.stdout)
                dp.communicate()

    pcmf = os.environ.get('JZMQ_PROFILE_CHOWN_USER')
    if pcmf:
        p = subprocess.Popen(['chown', '-R', pcmf, sources_dir])
        p.communicate()
        print('\nchowned back files to {}'.format(pcmf))
