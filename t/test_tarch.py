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


def test_tarch_msgs(tarch):
    test_msg = "test_tarch_msgs"
    tarch.A.publish_message(test_msg)
    for node in tarch:
        node.poll()
    for node in tarch:
        if node == tarch.A:
            continue
        assert node.received_messages == [test_msg]
