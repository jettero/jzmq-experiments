#!/usr/bin/env python
# coding: utf-8
# pylint: disable=redefined-outer-name

import pytest
from jzmq.msg import TaggedMessage, Tag, StupidMessage, RoutedMessage


def test_no_prefix():
    msg = StupidMessage("supz")
    emsg = msg.encode()
    assert emsg == (b"supz",)
    assert repr(msg) == "StupidMessage('supz',)"


def test_tags():
    t1 = Tag("t1")
    t2 = Tag("t2")
    t3 = Tag("t1", time=t1.time)

    assert t1 != t2
    assert t1 == t3
    assert t1.time > 0
    assert t2.time >= t1.time


@pytest.fixture
def m0():
    return TaggedMessage("m0")


@pytest.fixture
def m1():
    return TaggedMessage("<m1-sender:3.14159>", "m1")


@pytest.fixture
def m0d(m0):
    return TaggedMessage(*m0.encode())


def test_m0(m0):
    assert str(m0) == "m0"
    assert m0.msg == "m0"
    assert m0.name == "unknown"
    assert m0.time > 0


def test_m1(m1):
    assert str(m1) == "m1"
    assert m1.msg == "m1"
    assert m1.name == "m1-sender"
    assert m1.time == 3.14159


def test_m0d(m0, m0d):
    assert m0 == m0d
    assert m0.name == m0d.name
    assert m0.time == m0d.time


def test_rm():
    dest0 = "to-thing"
    parts = ("msg_part0", "msg_part1")
    rm0 = RoutedMessage(dest0, *parts)
    assert rm0.to == (dest0,)
    assert rm0.tag not in parts
    assert tuple(rm0) == parts

    rm1 = RoutedMessage.decode(rm0.encode())
    assert rm0.to == rm1.to
    assert rm0.tag == rm1.tag
    assert tuple(rm0) == tuple(rm1)
