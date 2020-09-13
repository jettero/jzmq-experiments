# coding: utf-8

import os
import sys, signal
import re
import logging
from socket import gethostname

import zmq
from zmq.auth.thread import ThreadAuthenticator

from .util import zmq_socket_type_name, CallOnEachFactory
from .endpoint import Endpoint

DEFAULT_KEYRING = os.path.expanduser(os.path.join("~", ".config", "jzmq", "keyring"))

log = logging.getLogger(__name__)


def scrub_identity_name_for_certfile(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode()
    return re.sub(r"[^\w\d_-]+", "_", x)


def default_callback(socket):
    msg = socket.recv()
    print(f"{zmq_socket_type_name(socket.type)}.recv(): {msg}")

class StupidNode:
    pubkey = privkey = auth = None

    def __init__(self, endpoint="*", identity=None, keyring=DEFAULT_KEYRING):
        log.debug("begin node setup")

        self.endpoint = Endpoint(endpoint)
        self.identity = identity or f"{gethostname()}-{self.endpoint.pub}"
        self.channel = ""  # subscription filter (I think)
        self.keyring = keyring

        log.debug("creating context; identity=%s", self.identity)

        self.ctx = zmq.Context()
        self.cleartext_ctx = zmq.Context()

        self.start_auth()

        log.debug("creating sockets")

        self.pub = self.mk_socket(zmq.PUB)
        self.pull = self.mk_socket(zmq.PULL)
        self.router = self.mk_socket(zmq.ROUTER)
        self.rep = self.mk_socket(zmq.REP, enable_curve=False)

        self.sub = CallOnEachFactory()
        self.push = CallOnEachFactory()

        log.debug("binding sockets")

        self.bind(self.pub)
        self.bind(self.pull)
        self.bind(self.router)
        self.bind(self.rep, enable_curve=False)

        log.debug("registering polling")

        self.poller = zmq.Poller()
        self.poller.register(self.pull, zmq.POLLIN)
        self.poller.register(self.rep, zmq.POLLIN)

        self._callbacks = dict()

        log.debug("registering WAI reply machine")

        self.set_callback(self.rep, self.wai_reply_machine)

        log.debug("configuring interrupt signal")
        signal.signal(signal.SIGINT, self.interrupt)

        log.debug("node setup complete")

    def wai_reply_machine(self, socket):
        msg = socket.recv()
        ttype = zmq_socket_type_name(socket.type)
        log.debug('receved "%s" over %s socket', msg, ttype)
        msg = [self.identity.encode(), self.pubkey]
        log.debug('sending "%s" as reply over %s socket', msg, ttype)
        socket.send_multipart(msg)

    def start_auth(self):
        log.debug("starting auth thread")
        self.auth = ThreadAuthenticator(self.ctx)
        self.auth.start()
        self.auth.allow("127.0.0.1")
        self.auth.configure_curve(domain="*", location=self.keyring)
        self.load_or_create_key()

    @property
    def key_basename(self):
        return scrub_identity_name_for_certfile(self.identity)

    @property
    def key_filename(self):
        return os.path.join(self.keyring, self.key_basename + ".key")

    @property
    def secret_key_filename(self):
        return self.key_filename + "_secret"

    def load_key(self):
        log.debug("loading node key-pair")
        self.pubkey, self.privkey = zmq.auth.load_certificate(self.secret_key_filename)

    def load_or_create_key(self):
        try:
            self.load_key()
        except IOError as e:
            log.debug("error loading key: %s", e)
            log.debug("creating node key-pair")
            os.makedirs(self.keyring, mode=0o0700, exist_ok=True)
            zmq.auth.create_certificates(self.keyring, self.key_basename)
            self.load_key()

    def publish_message(self, msg):
        if not isinstance(msg, (bytes, bytearray)):
            msg = msg.encode()
        log.debug("publishing message: %s", msg)
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

    def mk_socket(self, stype, enable_curve=True):
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

        if enable_curve:
            socket = self.ctx.socket(stype)
            log.debug("create %s socket in crypto context", zmq_socket_type_name(stype))
        else:
            socket = self.cleartext_ctx.socket(stype)
            log.debug(
                "create %s socket in cleartext context", zmq_socket_type_name(stype)
            )

        socket.linger = 1
        socket.identity = self.identity.encode()
        socket.reconnect_ivl = 100
        socket.reconnect_ivl_max = 5000

        if enable_curve:
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

    def interrupt(self, signo, eframe):  # pylint: disable=unused-argument
        print(" kaboom")
        self.closekill()
        sys.exit(0)

    def closekill(self):
        try:
            log.debug("trying to stop auth thread")
            self.auth.stop()
            log.debug("auth thread seems to have stopped")
        except AttributeError:
            log.debug("there does not seem to be an auth thread to stop")

        log.debug("destroying cleartext context")
        self.cleartext_ctx.destroy(1)

        log.debug("destroying crypto context")
        self.ctx.destroy(1)

    def __del__(self):
        self.closekill()

    def bind(self, socket, enable_curve=True):
        if enable_curve:
            socket.curve_server = True  # must come before bind
        try:
            f = self.endpoint.format(socket.type)
            socket.bind(f)
        except zmq.ZMQError as e:
            raise zmq.ZMQError(f"unable to bind {f}: {e}") from e

    def cleartext_request(self, endpoint, msg):
        req = self.mk_socket(zmq.REQ, enable_curve=False)
        req.connect(endpoint.format(zmq.REQ))
        if not isinstance(msg, (bytes, bytearray)):
            msg = msg.encode()
        log.debug("sending cleartext request: %s", msg)
        req.send(msg)
        log.debug("waiting for reply")
        res = req.recv_multipart()
        log.debug("received reply: %s", res)
        if len(res) == 2:
            return res
        req.close()
        return None, None

    def pubkey_pathname(self, node_id):
        if isinstance(node_id, Endpoint):
            node_id = Endpoint.host
        fname = scrub_identity_name_for_certfile(node_id) + ".key"
        pname = os.path.join(self.keyring, fname)
        return pname

    def learn_or_load_endpoint_pubkey(self, endpoint):
        epubk_pname = self.pubkey_pathname(endpoint)
        if not os.path.isfile(epubk_pname):
            log.debug("%s does not exist yet, trying to learn certificate", epubk_pname)
            node_id, public_key = self.cleartext_request(endpoint, "who are you?")
            if node_id:
                epubk_pname = self.pubkey_pathname(node_id)
                if not os.path.isfile(epubk_pname):
                    with open(epubk_pname, "wb") as fh:
                        fh.write(b"# generated via rep/req pubkey transfer\n\n")
                        fh.write(b"metadata\n")
                        # NOTE: in zmq/auth/certs.py's _write_key_file,
                        # metadata should be key-value pairs; roughly like the
                        # following (although with their particular py2/py3
                        # nerosis edited out):
                        #
                        # f.write('metadata\n')
                        #     for k,v in metadata.items():
                        #         f.write(f"    {k} = {v}\n")
                        fh.write(b"curve\n")
                        fh.write(b'    public-key = "')
                        fh.write(public_key)
                        fh.write(b'"')
        log.debug("loading certificate %s", epubk_pname)
        ret, _ = zmq.auth.load_certificate(epubk_pname)
        return ret

    def connect_to_endpoints(self, *endpoints):
        log.debug("connecting remote endpoints")
        for item in endpoints:
            self.connect_to_endpoint(item)
        log.debug("remote endpoints connected")
        return self

    def _connect_socket(self, endpoint, stype, pubkey, preconnect=None):
        log.debug("creating %s socket to endpoint=%s", zmq_socket_type_name(stype), endpoint)
        s = self.mk_socket(stype)
        s.curve_serverkey = pubkey
        if callable(preconnect):
            preconnect(s)
        s.connect(endpoint.format(zmq.SUB))

    def connect_to_endpoint(self, endpoint):
        if not isinstance(endpoint, Endpoint):
            endpoint = Endpoint(endpoint)

        log.debug("learning or loading endpoint=%s pubkey", endpoint)
        epk = self.learn_or_load_endpoint_pubkey(endpoint)

        sos = lambda s: s.setsockopt_string(zmq.SUBSCRIBE, self.channel)
        sub = self._connect_socket(endpoint, zmq.SUB, epk, sos)
        self.poller.register(sub, zmq.POLLIN)
        self.sub[endpoint] = sub

        psh = self._connect_socket(endpoint, zmq.PUSH, epk)
        self.push[endpoint] = psh

        return self

    def __repr__(self):
        return f"StupidNode({self.endpoint})"
