#!/usr/bin/env python
# encoding: utf-8

import argparse
import zmq

def main(**args):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser( # description='this program',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    try: main(**args.__dict__)
    except KeyboardInterrupt: pass
