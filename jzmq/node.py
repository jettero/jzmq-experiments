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

from .msg import TaggedMessage, StupidMessage
from .util import zmq_socket_type_name
from .endpoint import Endpoint

DEFAULT_KEYRING = os.path.expanduser(os.path.join("~", ".config", "jzmq", "keyring"))


def scrub_identity_name_for_certfile(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode()
    return re.sub(r"[^\w\d_-]+", "_", x)


class StupidNode:
    pubkey = privkey = None
    channel = ""  # subscription filter or something (I think)
    PORTS = 4  # as we add or remove ports, make sure this is the number of ports a StupidNode uses

    def __init__(self, endpoint="*", identity=None, keyring=DEFAULT_KEYRING):
        self.keyring = keyring
        self.endpoint = (
            endpoint if isinstance(endpoint, Endpoint) else Endpoint(endpoint)
        )
        self.endpoints = list()
        self.identity = identity or f"{gethostname()}-{self.endpoint.pub}"
        self.log = logging.getLogger(f"{self.identity}")

        self.log.debug("begin node setup / creating context")

        self.ctx = zmq.Context()
        self.cleartext_ctx = zmq.Context()

        self.start_auth()

        self.log.debug("creating sockets")

        self.pub = self.mk_socket(zmq.PUB)
        self.router = self.mk_socket(zmq.ROUTER)
        self.rep = self.mk_socket(zmq.REP, enable_curve=False)

        self.sub = list()
        self.dealer = list()

        self.log.debug("binding sockets")

        self.bind(self.pub)
        self.bind(self.router)
        self.bind(self.rep, enable_curve=False)

        self.log.debug("registering polling")

        self.poller = zmq.Poller()
        self.poller.register(self.router, zmq.POLLIN)

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
                self.log.debug('received "%s" over %s socket', msg, ttype)
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

    def preprocess_message(self, msg):
        if not isinstance(msg, TaggedMessage):
            msg = TaggedMessage(msg, name=self.identity)
        rmsg = repr(msg)
        emsg = msg.encode()
        return msg, rmsg, emsg

    def route_message(self, to, msg):
        msg, rmsg, emsg = self.preprocess_message(msg)
        self.log.debug("routing message %s to %s", rmsg, to)
        emsg = StupidMessage(to).encode() + emsg
        self.router.send_multipart(emsg)

    def publish_message(self, msg, no_deal=False, no_deal_to=None):
        msg, rmsg, emsg = self.preprocess_message(msg)
        self.local_workflow(msg)
        self.log.debug("publishing message %s", rmsg)
        self.pub.send_multipart(emsg)
        if no_deal:
            return
        if no_deal_to is None:
            ok_send = lambda x: True
        elif callable(no_deal_to):
            ok_send = no_deal_to
        elif isinstance(no_deal_to, zmq.Socket):
            npt_i = self.dealer.index(no_deal_to)
            ok_send = lambda x: x != npt_i
        elif isinstance(no_deal_to, int):
            ok_send = lambda x: x != no_deal_to
        elif isinstance(no_deal_to, (list, tuple)):
            ok_send = lambda x: x not in no_deal_to
        for i, sock in enumerate(self.dealer):
            if ok_send(i):
                self.log.debug("dealing message %s to %s", rmsg, self.endpoints[i])
                sock.send_multipart(emsg)
            else:
                self.log.debug("not sending %s to %s", rmsg, self.endpoints[i])

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

    def local_workflow(self, msg):
        msg = self.local_react(msg)
        if msg:
            msg = self.all_react(msg)
        return msg

    def sub_workflow(self, socket):
        idx = self.sub.index(socket)
        enp = self.endpoints[idx]
        self.log.debug("start sub_workflow (idx=%d -> endpoint=%s)", idx, enp)
        msg = self.sub_receive(socket, idx)
        for react in (self.nonlocal_react, self.all_react):
            if msg:
                msg = react(msg, idx=idx)
        self.log.debug("end sub_workflow")
        return msg

    def router_workflow(self):
        self.log.debug("start router_workflow")
        msg = self.router_receive()
        for react in (self.nonlocal_react, self.all_react):
            if not msg:
                break
            msg = react(msg)
        self.log.debug("end router_workflow")
        return msg

    def dealer_workflow(self, socket):
        idx = self.dealer.index(socket)
        enp = self.endpoints[idx]
        self.log.debug("start deal_workflow (idx=%d -> endpoint=%s)", idx, enp)
        msg = self.dealer_receive(socket, idx)
        for react in (self.nonlocal_react, self.all_react):
            if not msg:
                break
            msg = react(msg, idx=idx)
        self.log.debug("end deal_workflow")
        return msg

    def sub_receive(self, socket, idx):  # pylint: disable=unused-argument
        return TaggedMessage(*socket.recv_multipart())

    def dealer_receive(self, socket, idx):  # pylint: disable=unused-argument
        return TaggedMessage(*socket.recv_multipart())

    def router_receive(self):
        _, *msg = self.router.recv_multipart()
        # we ignore the source ID (in '_') and just believe the msg.tag.name ... it's
        # roughly the same thing anyway
        return TaggedMessage(*msg)

    def all_react(self, msg, idx=None):  # pylint: disable=unused-argument
        return msg

    def nonlocal_react(self, msg, idx=None):  # pylint: disable=unused-argument
        return msg

    def local_react(self, msg):
        return msg

    def poll(self, timeo=500, other_cb=None):
        """Check to see if there's any incoming messages. If anything seems ready to receive,
        invoke the related workflow or invoke other_cb (if given) on the socket item.
        """
        items = dict(self.poller.poll(timeo))
        ret = list()
        for item in items:
            if items[item] != zmq.POLLIN:
                continue
            if item in self.sub:
                res = self.sub_workflow(item)
            elif item in self.dealer:
                res = self.dealer_workflow(item)
            elif item is self.router:
                res = self.router_workflow()
            elif callable(other_cb):
                res = other_cb(item)
            else:
                res = None
                if False and isinstance(item, zmq.Socket):
                    self.log.error(
                        "no workflow defined for socket of type %s -- received: %s",
                        zmq_socket_type_name(item),
                        item.recv_multipart(),
                    )
                else:
                    self.log.error(
                        "no workflow defined for socket of type %s -- regarding as fatal",
                        zmq_socket_type_name(item),
                    )
                    # note: this normally doesn't trigger an exit... thanks threading
                    raise Exception("unhandled poll item")
            if isinstance(res, TaggedMessage):
                ret.append(res)
        return ret

    def interrupt(self, signo, eframe):  # pylint: disable=unused-argument
        print(" kaboom")
        self.closekill()
        sys.exit(0)

    def closekill(self):
        if hasattr(self, 'auth') and self.auth is not None:
            if self.auth.is_alive():
                self.log.debug("trying to stop auth thread")
                self.auth.stop()
                self.log.debug("auth thread seems to have stopped")
            del self.auth

        if hasattr(self, '_wai_thread'):
            if self._wai_thread.is_alive():
                self.log.debug("WAI Thread seems to be alive, trying to join")
                self._wai_continue = False
                self._wai_thread.join()
                self.log.debug("WAI Thread seems to jave joined us.")
            del self._wai_thread

        if hasattr(self, 'cleartext_ctx'):
            self.log.debug("destroying cleartext context")
            self.cleartext_ctx.destroy(1)
            del self.cleartext_ctx

        if hasattr(self, 'ctx'):
            self.log.debug("destroying crypto context")
            self.ctx.destroy(1)
            del self.ctx

    def __del__(self):
        self.log.debug("%s is being deleted", self)
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
                endpoint.identity = node_id.decode()
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

        deal = self._create_connected_socket(endpoint, zmq.DEALER, epk)
        self.poller.register(deal, zmq.POLLIN)
        self.dealer.append(deal)

        self.endpoints.append(endpoint)

        return self

    def __repr__(self):
        return f"{self.__class__.__name__}({self.identity})"


class RelayNode(StupidNode):
    def __init__(self, *a, dup_time=10, **kw):
        super().__init__(*a, **kw)
        self.recent = set()
        self.dup_time = dup_time

    def cleanup_recent(self):
        old = time.time() - self.dup_time
        self.recent = set(x for x in self.recent if x.time > old)

    def is_repeat(self, msg):
        self.cleanup_recent()
        if msg.tag in self.recent:
            self.log.debug("%r may be a repeat, not (re)broadcasting", msg)
            return True
        self.log.debug("marking having seen %s, check_msg ok though", msg.tag)
        self.recent.add(msg.tag)
        return False

    def local_react(self, msg):
        msg = super().local_react(msg)
        self.recent.add(msg.tag)
        return msg

    def nonlocal_react(self, msg, idx=None):
        if self.is_repeat(msg):
            return False
        self.publish_message(msg, no_deal_to=idx)
        return msg
