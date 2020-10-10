#!/usr/bin/env python
# coding: utf-8


import jzmq.util as u

def test_increment_ports():
    p0 = (1,2,3,4)
    p1 = u.increment_ports(p0)
    assert p0 == (1,2,3,4)
    assert p1 == (5,6,7,8)
