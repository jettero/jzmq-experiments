#!/usr/bin/env python
# coding: utf-8

import logging
from jzmq import StupidNode

log = logging.getLogger(__name__)


def test_tarch_desc(tarch_desc):
    the_names = ("A", "B", "C", "D")

    assert tuple(sorted(tarch_desc)) == the_names

    for k in the_names:
        assert len(tarch_desc[k].endpoints) == 2
        for item in tarch_desc[k].endpoints:
            assert item in the_names


def test_tarch_construction(tarch):
    for item in tarch:
        assert isinstance(item, StupidNode)


def test_tarch_msgs_AB(tarch):
    test_msg = "test_tarch_msgs"

    for _ in range(5):
        tarch.B.poll(50)
        tarch.A.poll(50)

    tarch.B.publish_message(test_msg)

    for _ in range(5):
        tarch.B.poll(50)
        tarch.A.poll(50)

    assert tarch.B.received_messages == list()
    assert tarch.A.received_messages == [test_msg]
