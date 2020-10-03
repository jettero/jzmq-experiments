#!/usr/bin/env python
# coding: utf-8

import re
import time

TAG_RE = re.compile('<(?P<name>.+?):(?P<time>\d+(?:\.\d+)?)>')

def decode_part(x):
    if isinstance(x, (int,float)):
        x = str(x)

    try:
        x = x.decode()
    except AttributeError:
        pass

    try:
        x = x.strip()
    except AttributeError:
        pass

    return x


class StupidMessage(list):
    def __init__(self, *parts):
        super().__init__( decode_part(x) for x in parts )

    def encode(self, *prefix):
        return tuple( x.encode() for x in prefix ) + tuple( x.encode() for x in self )

    def __repr__(self):
        return f'StupidMessage{tuple(self)}'


class TaggedMessage(StupidMessage):
    default_tag = TAG_RE.match('<unknown:0.0>').groups()

    def __init__(self, *parts, sep=' '):
        super().__init__(*parts)

        self.sep = sep

        if len(self) < 1:
            self._tag = self.default_tag
        else:
            m = TAG_RE.match(self[0])
            if m:
                self._tag = m.groups()
            else:
                self._tag = self.default_tag

        self._tag = (self._tag[0], float(self._tag[1]))

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f'TaggedMessage[{self.tag}]{tuple(self)}'

    @property
    def tag(self):
        return f'<{self.name}:{self.time}>'

    def encode(self):
        return super().encode(self.tag)

    @property
    def msg(self):
        return self.sep.join(self)

    @property
    def time(self):
        return self._tag[1]

    @property
    def name(self):
        return self._tag[0]
