# coding: utf-8

import zmq
from .nicknames import NicknamesMixin

class StupidNode(NicknamesMixin):
    _nicknames = {
        "pub": ("publish",),
        "pull": ("collector", "collect", "col"),
        "router": ("directed", "director", "dir"),
    }

    def __init__(self, publish_port=5555, collector_port=5556, directed_port=5557):
        ctx = zmq.Context()
        self.pub = ctx.socket(zmq.PUB)
        self.pull = ctx.socket(zmq.PULL)
        self.router = ctx.socket(zmq.ROUTER)
