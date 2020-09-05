# coding: utf-8
# pylint: disable=attribute-defined-outside-init,no-member


from jzmq.jsmb.nicknames import NicknamesMixin


def test_nicknames():
    class DumbThing(NicknamesMixin):
        _nicknames = {"test1": ("nick1", "nick2"), "test2": ("nack1", "nack2")}
        test1 = "test1"
        test2 = "test2"

    dt1 = DumbThing()
    assert dt1.test1 == "test1"
    assert dt1.nick1 == "test1"
    assert dt1.nick2 == "test1"

    assert dt1.test2 == "test2"
    assert dt1.nack1 == "test2"
    assert dt1.nack2 == "test2"

    dt1.test1 = "test3"

    assert dt1.test1 == "test3"
    assert dt1.nick1 == "test3"
    assert dt1.nick2 == "test3"

    assert dt1.test2 == "test2"
    assert dt1.nack1 == "test2"
    assert dt1.nack2 == "test2"

    dt1.nick2 = "test4"

    assert dt1.test1 == "test4"
    assert dt1.nick1 == "test4"
    assert dt1.nick2 == "test4"

    assert dt1.test2 == "test2"
    assert dt1.nack1 == "test2"
    assert dt1.nack2 == "test2"
