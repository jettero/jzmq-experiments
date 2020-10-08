#!/usr/bin/env python
# coding: utf-8

import time
import logging
import pytest
from jzmq import Node

TEST_REPETITIONS = 10
MSG_WAIT_MS = 1
PUBLISH_WAIT_S = 0.1

def test_tarch_desc(tarch_names, tarch_desc):
    assert tarch_names == tuple("A B C D E".split())
    assert tuple(sorted(tarch_desc)) == tarch_names

    for k in tarch_names:
        assert len(tarch_desc[k].endpoints) == 1 if k == "E" else 2
        for item in tarch_desc[k].endpoints:
            assert item in tarch_names


def test_tarch_construction(tarch, tarch_names):
    for item in tarch:
        assert isinstance(item, Node)

    assert len(tarch_names) == len(tarch)
    for k, item in zip(tarch_names, tarch):
        assert item is getattr(tarch, k)


def do_poll(log, tarch, tag, wait):
    log.info("%s poll(%d)", tag, wait)

    for node in tarch:
        node.received_messages = list()

    for node in tarch:
        res = [str(x) for x in node.poll(MSG_WAIT_MS)]
        if res:
            log.info("%s received %d msg(s)", node, len(res))
            node.received_messages += res


@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_tarch_E_to_net(tarch, loop):
    test_msg = f"test_tarch_msgs-{loop}"

    log = logging.getLogger(f"{__name__}:E2")

    log.info("publishing %s from %s", test_msg, tarch.E)
    tarch.E.publish_message(test_msg)
    time.sleep(PUBLISH_WAIT_S)

    received_test_message = [test_msg]
    did_not_receive = list()

    do_poll(log, tarch, "first", MSG_WAIT_MS)

    assert tarch.A.received_messages == did_not_receive
    assert tarch.B.received_messages == did_not_receive
    assert tarch.C.received_messages == received_test_message
    assert tarch.D.received_messages == received_test_message
    assert tarch.E.received_messages == did_not_receive

    do_poll(log, tarch, "second", MSG_WAIT_MS)

    assert tarch.A.received_messages == received_test_message
    assert tarch.B.received_messages == received_test_message
    assert tarch.C.received_messages == did_not_receive
    assert tarch.D.received_messages == did_not_receive
    assert tarch.E.received_messages == did_not_receive

    do_poll(log, tarch, "third", MSG_WAIT_MS)

    assert tarch.A.received_messages == did_not_receive
    assert tarch.B.received_messages == did_not_receive
    assert tarch.C.received_messages == did_not_receive
    assert tarch.D.received_messages == did_not_receive
    assert tarch.E.received_messages == did_not_receive


@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_tarch_B_to_net(tarch, loop):
    test_msg = f"test_tarch_msgs-{loop}"

    log = logging.getLogger(f"{__name__}:B2")

    log.info("publishing %s from %s", test_msg, tarch.B)
    tarch.B.publish_message(test_msg)
    time.sleep(PUBLISH_WAIT_S)

    received_test_message = [test_msg]
    did_not_receive = list()

    do_poll(log, tarch, "first", MSG_WAIT_MS)

    assert tarch.A.received_messages == received_test_message
    assert tarch.B.received_messages == did_not_receive
    assert tarch.C.received_messages == received_test_message
    assert tarch.D.received_messages == received_test_message
    assert tarch.E.received_messages == received_test_message

    do_poll(log, tarch, "second", MSG_WAIT_MS)

    assert tarch.A.received_messages == did_not_receive
    assert tarch.B.received_messages == did_not_receive
    assert tarch.C.received_messages == did_not_receive
    assert tarch.D.received_messages == did_not_receive
    assert tarch.E.received_messages == did_not_receive

    do_poll(log, tarch, "third", MSG_WAIT_MS)

    assert tarch.A.received_messages == did_not_receive
    assert tarch.B.received_messages == did_not_receive
    assert tarch.C.received_messages == did_not_receive
    assert tarch.D.received_messages == did_not_receive
    assert tarch.E.received_messages == did_not_receive

@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_linear0(linear0, loop):
    test_msg = f"test_tarch_msgs-{loop}"
    received_test_message = [test_msg]
    did_not_receive = list()
    log = logging.getLogger(f"{__name__}:lin0")

    linear0.A.publish_message(test_msg)
    time.sleep(PUBLISH_WAIT_S)

    do_poll(log, linear0, "first", MSG_WAIT_MS)

    assert linear0.A.received_messages == did_not_receive
    assert linear0.B.received_messages == received_test_message
    assert linear0.C.received_messages == received_test_message
    assert linear0.D.received_messages == received_test_message
    assert linear0.E.received_messages == received_test_message
