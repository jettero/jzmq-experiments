#!/usr/bin/env python
# coding: utf-8

from time import time as now
from jzmq.util import MyRE

TAG_RE = MyRE(r"<(.+?):(\d+|\d+\.\d+)>")


def decode_part(x):
    try:
        x = x.decode()
    except AttributeError:
        pass
    return x


class StupidMessage(list):
    def __init__(self, *parts):
        super().__init__(decode_part(x) for x in parts)

    def encode(self, *a, prefix=None, **kw):
        if prefix is None:
            prefix = tuple()
        if not isinstance(prefix, (tuple, list)):
            prefix = (prefix,)
        return tuple(x.encode(*a, **kw) for x in prefix) + tuple(
            x.encode(*a, **kw) for x in self
        )

    def __repr__(self):
        return f"StupidMessage{tuple(self)}"


class Tag:
    def __init__(self, name, time=None):
        self.name = name
        try:
            self.time = float(time)
        except TypeError:
            self.time = now()

    def __str__(self):
        return f"<{self.name}:{self.time}>"

    def encode(self, *a, **kw):
        return self.__str__().encode(*a, **kw)

    __repr__ = __str__

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name and self.time == other.time

    def __hash__(self):
        return (self.name, self.time).__hash__()


class TaggedMessage(StupidMessage):
    def __init__(self, *parts, sep=" ", name="unknown"):
        super().__init__(*parts)

        self.sep = sep

        if len(self) < 1:
            self.tag = Tag(name)
        else:
            if isinstance(self[0], Tag):
                self.tag = Tag(self[0].name, self[1].time)
            else:
                if isinstance(self[0], str) and TAG_RE.match(self[0]):
                    self.pop(0)
                    self.tag = Tag(TAG_RE.group(1), TAG_RE.group(2))
                else:
                    self.tag = Tag(name)

    def __eq__(self, other):
        if isinstance(other, TaggedMessage):
            return self.tag == other.tag and self.msg == other.msg
        return self.msg == other

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"TaggedMessage[{self.tag}]{tuple(self)}"

    def encode(self, *a, **kw):
        return super().encode(*a, prefix=self.tag, **kw)

    @property
    def msg(self):
        return self.sep.join(self)

    @property
    def time(self):
        return self.tag.time

    @property
    def name(self):
        return self.tag.name

class RoutedMessage(TaggedMessage):
    def __init__(self, to, *parts, **kw):
        super().__init__(*parts, **kw)
        self.to = to

    def encode(self, *a, **kw):
        # we want TaggedMessage's ancestor, not RoutedMessage's ancestor
        return super(TaggedMessage, self).encode(*a, prefix=(self.to, self.tag), **kw)

    def __repr__(self):
        return f"RoutedMessage[{self.tag}]{tuple(self)} -> {self.to}"
