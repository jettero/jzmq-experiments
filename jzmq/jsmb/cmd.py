#!/usr/bin/env python
# coding: utf-8

import sys
import click
import zmq
from .node import StupidNode

to_send = list()
def read_a_line(socket):
    line = socket.readline().rstrip()
    to_send.append(line)

@click.command()
@click.option('-v', '--verbose', 'verbosity', count=True)
@click.option('-l', '--local-address', 'laddr', default='*', show_default=True)
@click.option('-r', '--remote-address', 'raddr', multiple=True, default=list())
def chat(laddr, raddr, verbosity):

    sn = StupidNode(laddr).connect_to_endpoints(*raddr)
    sn.poller.register(sys.stdin, zmq.POLLIN)
    sn.set_callback(sys.stdin, read_a_line)

    while True:
        # poll() returns a list of return values from the callbacks
        _ = sn.poll( 50 if to_send else 500 ) # we ignore it for now

        if to_send:
            sn.publish_message( to_send.pop(0) )
