#!/usr/bin/env python
# coding: utf-8

import sys
import logging
import click
import zmq
from .node import StupidNode, DEFAULT_KEYRING

to_send = list()


def read_a_line(socket):
    line = socket.readline().rstrip()
    to_send.append(line)


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

    logging.basicConfig(level=log_level)

    sn = StupidNode(laddr, identity=identity, keyring=keyring).connect_to_endpoints(
        *raddr
    )
    sn.poller.register(sys.stdin, zmq.POLLIN)
    sn.set_callback(sys.stdin, read_a_line)

    while True:
        # poll() returns a list of return values from the callbacks
        _ = sn.poll(50 if to_send else 500)  # we ignore it for now

        if to_send:
            sn.publish_message(to_send.pop(0))
