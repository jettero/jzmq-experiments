#!/usr/bin/env python
# coding: utf-8

import logging
from jzmq import Node

log = logging.getLogger(__name__)


def test_tarch_desc(tarch_names, tarch_desc):
    assert tarch_names == tuple("A B C D E".split())
    assert tuple(sorted(tarch_desc)) == tarch_names

    for k in tarch_names:
        assert len(tarch_desc[k].endpoints) == 1 if k == 'E' else 2
        for item in tarch_desc[k].endpoints:
            assert item in tarch_names


def test_tarch_construction(tarch, tarch_names):
    for item in tarch:
        assert isinstance(item, Node)

    assert len(tarch_names) == len(tarch)
    for k, item in zip(tarch_names, tarch):
        assert item is getattr(tarch, k)


def test_tarch_E_to_net(tarch):
    test_msg = "test_tarch_msgs"

    for item in tarch:
        item.received_messages = list()

    log.info('publishing %s from %s', test_msg, tarch.E)
    tarch.E.publish_message(test_msg)

    for i in range(3):
        log.info('polling (loop=%d)', i)

        for item in tarch:
            res = [ str(x) for x in item.poll(50) ]
            if res:
                log.info('%s received %d msg(s)', item, len(res))
                item.received_messages += res

    expected_res = [test_msg]

    assert tarch.A.received_messages == expected_res
    assert tarch.B.received_messages == expected_res
    assert tarch.C.received_messages == expected_res
    assert tarch.D.received_messages == expected_res
    assert tarch.E.received_messages == expected_res
