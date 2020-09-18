#!/usr/bin/env python
# coding: utf-8

from jzmq import StupidNode


def test_tarch_desc(tarch_desc):
    the_names = ('A','B','C','D')

    assert tuple(sorted(tarch_desc)) == the_names

    for k in the_names:
        assert len(tarch_desc[k].endpoints) == 2
        for item in tarch_desc[k].endpoints:
            assert item in the_names

def test_tarch_construction(tarch):
    for item in tarch:
        assert isinstance(item, StupidNode)
