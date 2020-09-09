#!/usr/bin/env python
# coding: utf-8

import os
import sys
import click
import zmq.auth

THIS_DIR = os.path.realpath( os.path.dirname(__file__) )

@click.command()
@click.argument('names', type=str, nargs=-1)
def main(names):
    for name in names:
        fname = name + '.key'
        if not os.path.isfile(fname):
            zmq.auth.create_certificates(THIS_DIR, name)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.extend(('sn1', 'sn2'))
    main()
