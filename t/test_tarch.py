#!/usr/bin/env python
# coding: utf-8

import logging
import pytest
from jzmq import Node

TEST_REPETITIONS = 10
MSG_WAIT_MS = 50

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

    for item in tarch:
        item.received_messages = list()

    for item in tarch:
        res = [str(x) for x in item.poll(wait)]
        if res:
            log.info("%s received %d msg(s)", item, len(res))
            item.received_messages += res


@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_tarch_E_to_net(tarch, loop):
    test_msg = "test_tarch_msgs"

    log = logging.getLogger(f"{__name__}:E2")

    log.info("publishing %s from %s", test_msg, tarch.E)
    tarch.E.publish_message(test_msg)

    er = [test_msg]
    ir = list()

    do_poll(log, tarch, "first", MSG_WAIT_MS)

    assert tarch.A.received_messages == ir
    assert tarch.B.received_messages == ir
    assert tarch.C.received_messages == er
    assert tarch.D.received_messages == er
    assert tarch.E.received_messages == ir

    do_poll(log, tarch, "second", MSG_WAIT_MS)

    assert tarch.A.received_messages == er
    assert tarch.B.received_messages == er
    assert tarch.C.received_messages == ir
    assert tarch.D.received_messages == ir
    assert tarch.E.received_messages == ir

    do_poll(log, tarch, "third", MSG_WAIT_MS)

    assert tarch.A.received_messages == ir
    assert tarch.B.received_messages == ir
    assert tarch.C.received_messages == ir
    assert tarch.D.received_messages == ir
    assert tarch.E.received_messages == ir


@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_tarch_B_to_net(tarch, loop):
    test_msg = "test_tarch_msgs"

    log = logging.getLogger(f"{__name__}:B2")

    log.info("publishing %s from %s", test_msg, tarch.B)
    tarch.B.publish_message(test_msg)

    er = [test_msg]
    ir = list()

    do_poll(log, tarch, "first", MSG_WAIT_MS)

    assert tarch.A.received_messages == er
    assert tarch.B.received_messages == ir
    assert tarch.C.received_messages == er
    assert tarch.D.received_messages == er
    assert tarch.E.received_messages == er

    do_poll(log, tarch, "second", MSG_WAIT_MS)

    assert tarch.A.received_messages == ir
    assert tarch.B.received_messages == ir
    assert tarch.C.received_messages == ir
    assert tarch.D.received_messages == ir
    assert tarch.E.received_messages == ir

    do_poll(log, tarch, "third", MSG_WAIT_MS)

    assert tarch.A.received_messages == ir
    assert tarch.B.received_messages == ir
    assert tarch.C.received_messages == ir
    assert tarch.D.received_messages == ir
    assert tarch.E.received_messages == ir

@pytest.mark.parametrize('loop', range(TEST_REPETITIONS))
def test_linear0(linear0, loop):
    test_msg = 'hiya'
    er = [test_msg]
    ir = list()
    log = logging.getLogger(f"{__name__}:lin0")

    linear0.A.publish_message(test_msg)

    do_poll(log, linear0, "first", MSG_WAIT_MS)

    assert linear0.A.received_messages == ir
    assert linear0.B.received_messages == er
    assert linear0.C.received_messages == er
    assert linear0.D.received_messages == er
    assert linear0.E.received_messages == er
