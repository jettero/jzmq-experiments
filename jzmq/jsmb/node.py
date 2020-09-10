# coding: utf-8

import os
import re
import zmq
from .endpoint import Endpoint
from .util import zmq_socket_type_name

from zmq.auth.thread import ThreadAuthenticator

DEFAULT_KEYRING = os.path.expanduser( os.path.join('~', '.config', 'jzmq', 'keyring') )

def scrub_identity_name_for_certfile(x):
    return re.sub(r'[^\w\d_-]+', '_', x)

def default_callback(socket):
    msg = socket.recv()
    print(f"{zmq_socket_type_name(socket.type)}.recv(): {msg}")


class StupidNode:
    pubkey = privkey = auth = None

    def __init__(self, endpoint="*", identity=None, keyring=DEFAULT_KEYRING):
        self.endpoint = Endpoint(endpoint)
        self.identity = identity or f"SN-{self.endpoint.pub}"
        self.channel = "" # subscription filter (I think)
        self.keyring = keyring

        self.ctx = zmq.Context()

        self.start_auth()

        self.pub = self.mk_socket(zmq.PUB)
        self.pull = self.mk_socket(zmq.PULL)
        self.router = self.mk_socket(zmq.ROUTER)

        self.sub = list()

        self.bind(self.pub)
        self.bind(self.pull)
        self.bind(self.router)

        self.poller = zmq.Poller()
        self.poller.register(self.pull, zmq.POLLIN)

        self._callbacks = dict()

    def start_auth(self):
        self.auth = ThreadAuthenticator(self.ctx)
        self.auth.start()
        self.auth.allow('127.0.0.1')
        self.auth.configure_curve(domain='*', location=self.keyring)
        self.load_or_create_key()

    @property
    def key_basename(self):
        return scrub_identity_name_for_certfile(self.identity)

    @property
    def key_filename(self):
        return os.path.join(self.keyring, self.key_basename + '.key')

    @property
    def secret_key_filename(self):
        return self.key_filename + '_secret'

    def load_key(self):
        self.pubkey, self.privkey = zmq.auth.load_certificate(self.secret_key_filename)

    def load_or_create_key(self):
        try:
            self.load_key()
        except IOError:
            os.makedirs(self.keyring, mode=0o0700, exist_ok=True)
            zmq.auth.create_certificates(self.keyring, self.key_basename)
            self.load_key()

    def publish_message(self, msg):
        if not isinstance(msg, (bytes, bytearray)):
            msg = msg.encode()
        self.pub.send(msg)

    def callback(self, socket):
        if isinstance(socket, int):
            for item in self._callbacks:
                if item.fileno() == socket:
                    socket = item
        cb = self._callbacks.get(socket, default_callback)
        return cb(socket)

    def set_callback(self, socket, callback):
        self._callbacks[socket] = callback

    def mk_socket(self, stype):
        # defaults:
        # socket.setsockopt(zmq.LINGER, -1) # infinite
        # socket.setsockopt(zmq.IDENTITY, None)
        # socket.setsockopt(zmq.TCP_KEEPALIVE, -1)
        # socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL, -1)
        # socket.setsockopt(zmq.TCP_KEEPALIVE_CNT, -1)
        # socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, -1)
        # socket.setsockopt(zmq.RECONNECT_IVL, 100)
        # socket.setsockopt(zmq.RECONNECT_IVL_MAX, 0) # 0 := always use IVL

        # the above can be accessed as attributes instead (they are case
        # insensitive, we choose lower case below so it looks like boring
        # python)

        socket = self.ctx.socket(stype)

        socket.linger = 0
        socket.identity = self.identity.encode()
        socket.reconnect_ivl = 100
        socket.reconnect_ivl_max = 5000

        socket.curve_secretkey = self.privkey
        socket.curve_publickey = self.pubkey

        return socket

    def poll(self, timeo=500):
        items = dict(self.poller.poll(timeo))
        ret = list()
        for item in items:
            if items[item] != zmq.POLLIN:
                continue
            ret.append(self.callback(item))
        return ret

    def __del__(self):
        self.auth.stop()
        self.pub.close()
        self.pull.close()
        self.router.close()
        for item in self.sub:
            item.close()

    def bind(self, socket):
        socket.curve_server = True  # must come before bind
        try:
            f = self.endpoint.format(socket.type)
            socket.bind(f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind {f}: {e}") from e

    def connect_to_endpoints(self, *endpoints):
        for item in endpoints:
            self.connect_to_endpoint(item)
        return self

    def connect_to_endpoint(self, endpoint):
        if not isinstance(endpoint, Endpoint):
            endpoint = Endpoint(endpoint)
        sub = self.mk_socket(zmq.SUB)

        # XXX: this works but not usefully. There's apparently no way to transmit the pubkey over the channel
        # ... you have to somehow know it a-priori
        server_key_fname = scrub_identity_name_for_certfile(endpoint.host) + ".key"
        server_key_pathname = os.path.join(self.keyring, server_key_fname)
        server_key, _ = zmq.auth.load_certificate(server_key_pathname)
        sub.curve_serverkey = server_key;
        # /XXX

        sub.setsockopt_string(zmq.SUBSCRIBE, self.channel)
        sub.connect(endpoint.format(zmq.SUB))
        self.poller.register(sub, zmq.POLLIN)
        self.sub.append(sub)
        return self

    def __repr__(self):
        return f"StupidNode({self.endpoint})"
