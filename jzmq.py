#!/usr/bin/env python
# encoding: utf-8

import argparse
import logging
import zmq

log = logging.getLogger('jzmq')


def main(args):
    ctx = zmq.Context()

    log.debug('creating pub socket and binding to tcp://%s', args.local)

    pub = ctx.socket(zmq.PUB)
    pub.bind(f'tcp://{args.local}')

    subs = list()

    for remote in args.remote:
        log.debug('creating sub socket and connecting tcp://%s', remote)
        sub = ctx.socket(zmq.SUB)
        sub.connect(f'tcp://{remote}')
        subs.append(sub)

    # TODO: in order to actually do anything, we'll need a select/poll or multi-thread setup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(  # description='this program',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('remote', type=str, nargs='*', default=['localhost:5555'])
    parser.add_argument('--local', type=str, default='*:5555')

    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    logging_args = dict(level=logging.DEBUG if args.verbose else logging.ERROR)
    logging.basicConfig(**logging_args)

    try:
        main(args)
    except KeyboardInterrupt:
        pass
