#!/usr/bin/env python
# coding: utf-8

from hypothesis import given
from hypothesis.strategies import integers, tuples
from jzmq.util import increment_ports as incp

PINT = integers(2 ** 0, 2 ** 16)


def test_incp_unaltered_input():
    p0 = (1, 2, 3, 4)
    p1 = incp(p0)
    assert p0 == (1, 2, 3, 4)
    assert p1 == (5, 6, 7, 8)


def test_incp_manually():
    # increment_ports isn't perfect, but it should basically follow these rules
    #   0. every result port is greater than the max in the given ports
    #   1. the linear distance between ports should be constant on eatch increment
    #      (ie,  given two ports (a,b) and two result ports (d,e) => (e-d)==(b-a))
    assert incp((1, 2, 5, 6)) == (7, 8, 11, 12)
    assert incp((1, 2, 9, 4)) == (10, 11, 18, 13)


# in fact, let's test the above properly


@given(tuples(PINT, PINT, PINT, PINT))
def test_increment_randomly(p0):
    p1 = incp(p0)

    for item in p0:
        assert item not in p1

    d0 = tuple((y - x) for x, y in zip(p0, p0[1:]))
    d1 = tuple((y - x) for x, y in zip(p1, p1[1:]))

    assert d0 == d1
