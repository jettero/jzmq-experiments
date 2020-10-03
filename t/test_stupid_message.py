#!/usr/bin/env python
# coding: utf-8

import pytest
from jzmq.msg import TaggedMessage, Tag

def test_tags():
    t1 = Tag('t1')
    t2 = Tag('t2')
    t3 = Tag('t1', time=t1.time)

    assert t1 != t2
    assert t1 == t3
    assert t1.time > 0
    assert t2.time >= t1.time

@pytest.fixture
def m0():
    return TaggedMessage('m0')

@pytest.fixture
def m1():
    return TaggedMessage('m1')

def test_tagged(m0):
    assert str(m0) == 'm0'
    assert m0.msg == 'm0'
    assert m0.name == 'unknown'
    assert m0.time > 0
