#!/usr/bin/env python
# coding: utf-8

import os
import logging
import pytest
from jzmq import Node

TEST_REPETITIONS = int(os.environ.get("JZMQ_TARCH_REPEAT", 5))
MSG_WAIT_MS = int(os.environ.get("JZMQ_TARCH_MSG_WAIT", 10))

log = logging.getLogger(__name__)


def test_tarch_desc(tarch_names, tarch_desc):
    assert 0 < len(tarch_names) < 100
    assert tuple(sorted(tarch_desc.arch)) == tarch_names

    for k in tarch_names:
        for item in tarch_desc.arch[k].endpoints:
            assert item in tarch_names


def test_tarch_construction(tarch, tarch_names):
    for node in tarch:
        assert isinstance(node, Node)

    assert len(tarch_names) == len(tarch)
    for i, (k, node) in enumerate(zip(tarch_names, tarch)):
        assert isinstance(i, int)
        assert isinstance(k, str)
        assert isinstance(node, Node)
        assert node is tarch[k]
        assert node is tarch[i]
        assert getattr(tarch, k) is tarch[k]


class PollWrapper:
    def __init__(self, tarch):
        self.tarch = tarch

    def __enter__(self):
        for node in self.tarch:
            node.received_messages = list()
        return self.do_poll

    def do_poll(self, min_loops=1):
        loops = 0
        did_something = True
        while did_something or loops < min_loops:
            did_something = False
            for node in self.tarch:
                res = [str(x) for x in node.poll(MSG_WAIT_MS)]
                if res:
                    log.info("%s received %d msg(s)", node, len(res))
                    node.received_messages += res
                    did_something = True
            loops += 1
        return loops

    def __exit__(self, *exc):
        for node in self.tarch:
            del node.received_messages


@pytest.mark.skipif(os.environ.get("JZMQ_SKIP_NETWORK"), reason="network disabled")
@pytest.mark.parametrize("loop", range(TEST_REPETITIONS))
def test_publish_from_A(tarch, loop):
    test_msg = f"test_msg({loop})"
    log.info('publishing "%s" from %s', test_msg, tarch.A)

    tarch.A.publish_message(test_msg)

    with PollWrapper(tarch) as do_poll:
        log.info("polling ran for count=%d round(s)", do_poll())

        received_test_message = [test_msg]
        did_not_receive = list()

        for node in tarch:
            correct = did_not_receive if node is tarch.A else received_test_message
            assert node.received_messages == correct


def _continue_tarch_test(tarch, tarch_names, test, do_poll, min_loops=1):
    log.info("polling ran for count=%d round(s)", do_poll(min_loops=min_loops))
    log.info("we expect nodes=%s should have heard the message", test.rcpt)
    for name in tarch_names:
        if name in test.rcpt:
            log.info("%s should have heard the message", name)
            assert tarch[name].received_messages == [test.msg]
        else:
            log.info("%s should not have heard the message", name)
            assert tarch[name].received_messages == list()


@pytest.mark.skipif(os.environ.get("JZMQ_SKIP_NETWORK"), reason="network disabled")
@pytest.mark.parametrize("loop", range(TEST_REPETITIONS))
@pytest.mark.usefixtures("loop")
def test_tarch_published_msgs(tarch, tarch_names, tarch_tests):
    for test in tarch_tests:
        with PollWrapper(tarch) as do_poll:
            if test.mtype == "M":
                log.info('publishing message "%s" from %s', test.msg, test.src)
                tarch[test.src].publish_message(test.msg)
                _continue_tarch_test(tarch, tarch_names, test, do_poll)


@pytest.mark.skipif(os.environ.get("JZMQ_SKIP_NETWORK"), reason="network disabled")
@pytest.mark.parametrize("loop", range(TEST_REPETITIONS))
@pytest.mark.usefixtures("loop")
def test_tarch_routed_msgs(tarch, tarch_names, tarch_tests):
    # In the worst routed case (nodes on a stick), we have to tell each node to
    # poll() at least 2(n-1) times without expecting any message to come back:
    # we have to wait for a route and then resend the message
    min_loops = (len(tarch) - 1) * 2

    for test in tarch_tests:
        with PollWrapper(tarch) as do_poll:
            if test.mtype == "R":
                log.info(
                    'routing message "%s" from %s to %s', test.msg, test.src, test.dst
                )
                tarch[test.src].route_message(tarch[test.dst], test.msg)
                _continue_tarch_test(
                    tarch, tarch_names, test, do_poll, min_loops=min_loops
                )
