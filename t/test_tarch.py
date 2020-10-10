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
    assert tuple(sorted(tarch_desc)) == tarch_names

    for k in tarch_names:
        for item in tarch_desc[k].endpoints:
            assert item in tarch_names


def test_tarch_construction(tarch, tarch_names):
    for node in tarch:
        assert isinstance(node, Node)

    assert len(tarch_names) == len(tarch)
    for k, node in zip(tarch_names, tarch):
        assert node is getattr(tarch, k)


class PollWrapper:
    def __init__(self, tarch):
        self.tarch = tarch

    def __enter__(self):
        for node in self.tarch:
            node.received_messages = list()
        return self.do_poll

    def do_poll(self):
        loops = 0
        did_something = True
        while did_something:
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
