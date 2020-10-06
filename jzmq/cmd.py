#!/usr/bin/env python
# coding: utf-8

import threading
import logging
import click
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from .node import RelayNode as Node, DEFAULT_KEYRING

ALIVE = True


def jzmq_node_tasks(node):
    while ALIVE:
        msgs = node.poll(50)
        for msg in msgs:
            print(f"{msg.name}: {msg.msg}")

    node.closekill()


@click.command()
@click.option("-v", "--verbose", "verbosity", count=True)
@click.option(
    "-k", "--keyring", type=click.Path(), default=DEFAULT_KEYRING, show_default=True
)
@click.option("-i", "--identity", type=str, help="[default <hostname>-<baseport>]")
@click.option("-l", "--local-address", "laddr", default="*", show_default=True)
@click.option("-r", "--remote-address", "raddr", multiple=True, default=list())
@click.option("--vi-input/--emacs-input", "vi_mode", default=False)
def chat(
    laddr, raddr, identity, verbosity, keyring, vi_mode
):  # pylint: disable=unused-argument
    global ALIVE

    log_level = logging.ERROR
    if verbosity > 0:
        log_level = logging.INFO
        if verbosity > 1:
            log_level = logging.DEBUG
        if verbosity < 4:
            logging.getLogger("zmq.auth").propagate = False
            logging.getLogger("asyncio").propagate = False

    with patch_stdout():
        logging.basicConfig(
            level=log_level,
            datefmt="%Y-%m-%d %H:%M:%S",
            format="%(name)s [%(process)d] %(levelname)s: %(message)s",
        )

        node = Node(laddr, identity=identity, keyring=keyring).connect_to_endpoints(
            *raddr
        )
        node_thread = threading.Thread(target=jzmq_node_tasks, args=(node,))
        node_thread.start()
        identity = node.identity

        node.publish_message("* enter")

        while ALIVE:
            try:
                line = prompt(f"{identity}> ", vi_mode=vi_mode)
            except KeyboardInterrupt:
                print(f"{identity}: ^C break")
                break
            except EOFError:
                print(f"{identity}: EOF")
                break

            if line.lower().strip() in ("exit", "stop", "quit"):
                print(f"{identity}:", line, "(quitting)")
                break

            if line and line.strip():
                node.publish_message(line)

    node.publish_message("* exit")
    ALIVE = False
    node_thread.join()
