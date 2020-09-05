# coding: utf-8

import zmq
from .endpoint import (
    Endpoint,
    DEFAULT_PUBLISH_PORT,
    DEFAULT_COLLECTOR_PORT,
    DEFAULT_DIRECTED_PORT,
)
from .nicknames import NicknamesMixin


class StupidNode(NicknamesMixin):
    _nicknames = {
        "pub": "publish",
        "sub": ("subscriber", "subscribe"),
        "pull": ("collector", "collect", "col"),
        "router": ("directed", "director", "dir"),
    }

    def __init__(
        self,
        *endpoints,
        publish_port=DEFAULT_PUBLISH_PORT,
        collector_port=DEFAULT_COLLECTOR_PORT,
        directed_port=DEFAULT_DIRECTED_PORT,
    ):

        self.endpoint = Endpoint(
            "*",
            publish_port=publish_port,
            collector_port=collector_port,
            directed_port=directed_port,
        )

        ctx = zmq.Context()
        self.pub = ctx.socket(zmq.PUB)
        self.pull = ctx.socket(zmq.PULL)
        self.router = ctx.socket(zmq.ROUTER)
        self.sub = None

        try:
            pub_f = self.endpoint.format(zmq.PUB)
            self.pub.bind(pub_f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind to pub url {pub_f}: {e}") from e

        try:
            pull_f = self.endpoint.format(zmq.PULL)
            self.pull.bind(pull_f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind to pull url {pull_f}: {e}") from e

        try:
            router_f = self.endpoint.format(zmq.ROUTER)
            self.router.bind(router_f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind to router url {router_f}: {e}") from e

        self.connect_to_endpoints(*endpoints)

    def connect_to_endpoints(self, *endpoints):
        for item in endpoints:
            self.connect_to_endpoint(item)

    def connect_to_endpoint(self, endpoint):
        if not isinstance(endpoint, Endpoint):
            endpoint = Endpoint.slurp(endpoint)
        self.sub.connect(endpoint.format(zmq.SUB))

    def __repr__(self):
        return f"StupidNode({self.endpoint})"
