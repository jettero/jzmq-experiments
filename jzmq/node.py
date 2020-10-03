# coding: utf-8

import os
import sys, signal
import re
import logging
import time
from threading import Thread
from socket import gethostname

import zmq
from zmq.auth.thread import ThreadAuthenticator

from .msg import TaggedMessage
from .util import zmq_socket_type_name
from .endpoint import Endpoint

DEFAULT_KEYRING = os.path.expanduser(os.path.join("~", ".config", "jzmq", "keyring"))

log = logging.getLogger(__name__)

def scrub_identity_name_for_certfile(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode()
    return re.sub(r"[^\w\d_-]+", "_", x)

class StupidNode:
    pubkey = privkey = auth = None
    channel = ""  # subscription filter or something (I think)

    PORTS = 4  # as we add or remove ports, make sure this is the number of ports a StupidNode uses

    def __init__(self, endpoint="*", identity=None, keyring=DEFAULT_KEYRING):
        self.keyring = keyring
        self.endpoint = (
            endpoint if isinstance(endpoint, Endpoint) else Endpoint(endpoint)
        )
        self.identity = identity or f"{gethostname()}-{self.endpoint.pub}"
        self.log = logging.getLogger(f"SN({self.identity})")

        self.log.debug("begin node setup / creating context")

        self.ctx = zmq.Context()
        self.cleartext_ctx = zmq.Context()

        self.start_auth()

        self.log.debug("creating sockets")

        self.pub = self.mk_socket(zmq.PUB)
        self.pull = self.mk_socket(zmq.PULL)
        self.router = self.mk_socket(zmq.ROUTER)
        self.rep = self.mk_socket(zmq.REP, enable_curve=False)

        self.sub = list()
        self.push = list()

        self.log.debug("binding sockets")

        self.bind(self.pub)
        self.bind(self.pull)
        self.bind(self.router)
        self.bind(self.rep, enable_curve=False)

        self.log.debug("registering polling")

        self.poller = zmq.Poller()
        self.poller.register(self.pull, zmq.POLLIN)

        self.log.debug("configuring interrupt signal")
        signal.signal(signal.SIGINT, self.interrupt)

        self.log.debug("configuring WAI Reply Thread")
        self._wai_thread = Thread(target=self.wai_reply_machine)
        self._wai_continue = True
        self._wai_thread.start()

        self.log.debug("node setup complete")

    def wai_reply_machine(self):
        while self._wai_continue:
            if self.rep.poll(200):
                self.log.debug("wai polled, trying to recv")
                msg = self.rep.recv()
                ttype = zmq_socket_type_name(self.rep)
                self.log.debug('receved "%s" over %s socket', msg, ttype)
                msg = [self.identity.encode(), self.pubkey]
                self.log.debug('sending "%s" as reply over %s socket', msg, ttype)
                self.rep.send_multipart(msg)
        self.log.debug("wai thread seems finished, loop broken")

    def start_auth(self):
        self.log.debug("starting auth thread")
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
        self.log.debug("loading node key-pair")
        self.pubkey, self.privkey = zmq.auth.load_certificate(self.secret_key_filename)

    def load_or_create_key(self):
        try:
            self.load_key()
        except IOError as e:
            self.log.debug("error loading key: %s", e)
            self.log.debug("creating node key-pair")
            os.makedirs(self.keyring, mode=0o0700, exist_ok=True)
            zmq.auth.create_certificates(self.keyring, self.key_basename)
            self.load_key()

    def publish_message(self, msg):
        self.log.info("publishing message: %s", msg)
        if not isinstance(msg, TaggedMessage):
            msg = TaggedMessage(msg)
        self.pub.send_multipart(msg.encode())

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
            self.log.debug(
                "create %s socket in crypto context", zmq_socket_type_name(stype)
            )
        else:
            socket = self.cleartext_ctx.socket(stype)
            self.log.debug(
                "create %s socket in cleartext context", zmq_socket_type_name(stype)
            )

        socket.linger = 1
        socket.identity = self.identity.encode()
        socket.reconnect_ivl = 1000
        socket.reconnect_ivl_max = 10000

        if enable_curve:
            socket.curve_secretkey = self.privkey
            socket.curve_publickey = self.pubkey

        return socket

    def sub_receive(self, socket):
        return TaggedMessage(*socket.recv_multipart())

    def sub_workflow(self, socket):
        log.debug('start sub_workflow')
        msg = self.sub_receive(socket)
        msg = self.sub_react(msg)
        log.debug('end sub_workflow')
        return msg

    def pull_workflow(self, socket):
        log.debug('start pull_workflow')
        msg = self.pull_receive()
        msg = self.pull_react(msg)
        log.debug('end pull_workflow')
        return msg

    def sub_react(self, msg):
        self.log.info(f"default sub-reaction to message: %s", msg)
        return msg

    def pull_react(self, msg):
        self.log.info(f"default pull-reaction to message: %s", msg)
        return msg

    def poll(self, timeo=500):
        items = dict(self.poller.poll(timeo))
        ret = list()
        for item in items:
            if items[item] != zmq.POLLIN:
                continue
            if item in self.sub:
                res = self.sub_workflow(item)
            elif item is self.pull:
                res = self.pull_workflow()
            else:
                log.error('no workflow defined for socket of type %s', zmq_socket_type_name(item))
            if res is not None:
                ret.append(res)
        return ret

    def interrupt(self, signo, eframe):  # pylint: disable=unused-argument
        print(" kaboom")
        self.closekill()
        sys.exit(0)

    def closekill(self):
        for i in ("auth", "ctx"):
            if not hasattr(self, i):
                self.log.debug(
                    "already closekilled, skipping extra closekill invocation"
                )
                return

        self.log.debug("closekilling")

        try:
            self.log.debug("trying to stop auth thread")
            self.auth.stop()
            self.log.debug("auth thread seems to have stopped")
            del self.auth
        except AttributeError:
            self.log.debug("there does not seem to be an auth thread to stop")

        if self._wai_thread and self._wai_thread.is_alive():
            self.log.debug("WAI Thread seems to be alive, trying to join")
            self._wai_continue = False
            self._wai_thread.join()
            self.log.debug("WAI Thread seems to jave joined us.")
            del self._wai_thread

        self.log.debug("destroying cleartext context")
        self.cleartext_ctx.destroy(1)
        del self.cleartext_ctx

        self.log.debug("destroying crypto context")
        self.ctx.destroy(1)
        del self.ctx

    def __del__(self):
        log.debug("%s is being deleted", self)
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
        self.log.debug("sending cleartext request: %s", msg)
        req.send(msg)
        self.log.debug("waiting for reply")
        res = req.recv_multipart()
        self.log.debug("received reply: %s", res)
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
            self.log.debug(
                "%s does not exist yet, trying to learn certificate", epubk_pname
            )
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
        self.log.debug("loading certificate %s", epubk_pname)
        ret, _ = zmq.auth.load_certificate(epubk_pname)
        return ret

    def connect_to_endpoints(self, *endpoints):
        self.log.debug("connecting remote endpoints")
        for item in endpoints:
            self.connect_to_endpoint(item)
        self.log.debug("remote endpoints connected")
        return self

    def _create_connected_socket(self, endpoint, stype, pubkey, preconnect=None):
        self.log.debug(
            "creating %s socket to endpoint=%s", zmq_socket_type_name(stype), endpoint
        )
        s = self.mk_socket(stype)
        s.curve_serverkey = pubkey
        if callable(preconnect):
            preconnect(s)
        s.connect(endpoint.format(stype))
        return s

    def connect_to_endpoint(self, endpoint):
        if not isinstance(endpoint, Endpoint):
            endpoint = Endpoint(endpoint)

        self.log.debug("learning or loading endpoint=%s pubkey", endpoint)
        epk = self.learn_or_load_endpoint_pubkey(endpoint)

        sos = lambda s: s.setsockopt_string(zmq.SUBSCRIBE, self.channel)
        sub = self._create_connected_socket(endpoint, zmq.SUB, epk, sos)
        self.poller.register(sub, zmq.POLLIN)
        self.sub.append(sub)

        psh = self._create_connected_socket(endpoint, zmq.PUSH, epk)
        self.push.append(psh)

        return self

    def __repr__(self):
        return f"StupidNode({self.identity})"


class RelayNode(StupidNode):
    def __init__(self, *a, dup_time=10, **kw):
        super().__init__(*a, **kw)
        self.recent = set()
        self.dup_time = dup_time

    def _cleanup_recent(self):
        old = time.time() - self.dup_time
        self.recent = set( x for x in self.recent if x.time > old )

    def sub_react(self, msg):
        self._cleanup_recent()
        if msg.tag in self.recent:
            log.debug("%s is too old to react to", repr(msg))
            return False
        log.debug("relaying %s to subscribers", repr(msg))
        self.publish_message(msg)
        self.recent.add(msg.tag)
        return msg

    pull_react = sub_react
