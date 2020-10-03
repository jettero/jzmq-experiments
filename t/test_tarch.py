#!/usr/bin/env python
# coding: utf-8

import logging
from jzmq import Node

log = logging.getLogger(__name__)


def test_tarch_desc(tarch_names, tarch_desc):
    assert tarch_names == tuple("A B C D".split())
    assert tuple(sorted(tarch_desc)) == tarch_names

    for k in tarch_names:
        assert len(tarch_desc[k].endpoints) == 2
        for item in tarch_desc[k].endpoints:
            assert item in tarch_names


def test_tarch_construction(tarch, tarch_names):
    for item in tarch:
        assert isinstance(item, Node)

    assert len(tarch_names) == len(tarch)
    for k,item in zip(tarch_names, tarch):
        assert item is getattr(tarch, k)


def test_tarch_msgs_AB(tarch):
    test_msg = "test_tarch_msgs"

    tarch.B.publish_message(test_msg)

    for item in tarch:
        item.received_messages = item.poll(50)

    expected_res = [test_msg]
    assert [str(x) for x in tarch.A.received_messages ] == expected_res
    assert [str(x) for x in tarch.B.received_messages ] == list()
    assert [str(x) for x in tarch.C.received_messages ] == expected_res
    assert [str(x) for x in tarch.D.received_messages ] == expected_res
