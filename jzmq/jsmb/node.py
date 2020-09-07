# coding: utf-8

import zmq
from .endpoint import Endpoint

class StupidNode:
    def __init__( self, endpoint='*', *endpoints):
        self.endpoint = Endpoint(endpoint)

        ctx = zmq.Context()
        self.pub = ctx.socket(zmq.PUB)
        self.pull = ctx.socket(zmq.PULL)
        self.router = ctx.socket(zmq.ROUTER)
        self.sub = None

        self.bind( self.pub )
        self.bind( self.pull )
        self.bind( self.router )

        self.connect_to_endpoints(*endpoints)

    def __del__(self):
        self.pub.close()
        self.pull.close()
        self.router.close()

    def bind(self, socket):
        try:
            f = self.endpoint.format(socket.type)
            socket.bind(f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind {f}: {e}") from e

    def connect_to_endpoints(self, *endpoints):
        for item in endpoints:
            self.connect_to_endpoint(item)

    def connect_to_endpoint(self, endpoint):
        if not isinstance(endpoint, Endpoint):
            endpoint = Endpoint.slurp(endpoint)
        self.sub.connect(endpoint.format(zmq.SUB))

    def __repr__(self):
        return f"StupidNode({self.endpoint})"
