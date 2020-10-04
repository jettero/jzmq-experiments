#!/usr/bin/env python
# coding: utf-8

import sys
import logging
import click
import zmq
from .node import RelayNode as Node, DEFAULT_KEYRING


@click.command()
@click.option("-v", "--verbose", "verbosity", count=True)
@click.option(
    "-k", "--keyring", type=click.Path(), default=DEFAULT_KEYRING, show_default=True
)
@click.option("-i", "--identity", type=str, help="[default <hostname>-<baseport>]")
@click.option("-l", "--local-address", "laddr", default="*", show_default=True)
@click.option("-r", "--remote-address", "raddr", multiple=True, default=list())
def chat(laddr, raddr, identity, verbosity, keyring):  # pylint: disable=unused-argument

    log_level = logging.ERROR
    if verbosity > 0:
        log_level = logging.INFO
        if verbosity > 1:
            log_level = logging.DEBUG
        if verbosity < 4:
            logging.getLogger("zmq.auth").propagate = False

    logging.basicConfig(level=log_level)

    sn = Node(laddr, identity=identity, keyring=keyring).connect_to_endpoints(*raddr)
    sn.poller.register(sys.stdin, zmq.POLLIN)

    ssinfno = sys.stdin.fileno()
    to_send = list()

    def read_a_line(sock):
        # normally the poller hands us our fileno, not the socket, so sock=0 is
        # the expected arg for sys.stdin
        if sock in (ssinfno, sys.stdin):
            line = sys.stdin.readline().rstrip()
            to_send.append(line)

    while True:
        msgs = sn.poll(50, other_cb=read_a_line)
        for msg in msgs:
            print(f"{msg.name}: {msg.msg}")
        while to_send:
            sn.publish_message(to_send.pop(0))
