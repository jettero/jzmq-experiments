#!/usr/bin/env python
# coding: utf-8

from jzmq.msg import TaggedMessage

def test_tagged():
    m = TaggedMessage('supz')

    assert str(m) == 'supz'
    assert m.msg == 'supz'
    assert m.name == 'unknown'
    assert m.time == 0.0
