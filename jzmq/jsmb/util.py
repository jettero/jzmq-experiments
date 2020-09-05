#!/usr/bin/env python
# coding: utf-8

import re


class MyRE:
    h = _m = None

    @property
    def m(self):
        return self._m

    @m.setter
    def m(self, v):
        self._m = v
        self.h = None

    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def match(self, *a, **kw):
        self.m = self.pattern.match(*a, **kw)
        return self.m

    def search(self, *a, **kw):
        self.m = self.pattern.search(*a, **kw)
        self.h = None
        return self.m

    def group(self, *a, **kw):
        return self.m.group(*a, **kw)

    def groups(self, *a, **kw):
        return self.m.groups(*a, **kw)

    def groupdict(self, *a, **kw):
        return self.m.groupdict(*a, **kw)

    def __getitem__(self, name, default=None):
        if isinstance(name, int):
            return self.group(name)
        if self.h is None:
            self.h = self.groupdict()
        return self.h.get(name, default)

    def __bool__(self):
        return bool(self.m)

    def __iter__(self):
        yield from self.groups()

    def __repr__(self):
        ret = f"MyRE({self.pattern.pattern}"
        if self.m:
            ret += " MATCHED"
            g = self.groups()
            if g:
                ret += f" groups={g}"
            h = self.groupdict()
            if h:
                ret += f" named_groups={h}"
        return ret + ")"
