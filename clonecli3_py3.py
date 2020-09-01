#!/usr/bin/env python
# coding=utf-8

"""
Clone client Model Three
Author: Min RK <benjaminrk@gmail.com
"""

import random
import time
import zmq
from kvmsg import KVMsg


def main():

    # Prepare our context and subscriber
    ctx = zmq.Context()
    snapshot = ctx.socket(zmq.DEALER)
    snapshot.linger = 0
    snapshot.connect("tcp://localhost:5556")
    subscriber = ctx.socket(zmq.SUB)
    subscriber.linger = 0
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    subscriber.connect("tcp://localhost:5557")
    publisher = ctx.socket(zmq.PUSH)
    publisher.linger = 0
    publisher.connect("tcp://localhost:5558")

    random.seed(time.time())
    kvmap = {}

    # Get state snapshot
    sequence = 0
    snapshot.send_string("ICANHAZ?")
    while True:
        try:
            kvmsg = KVMsg.recv(snapshot)
        except:
            return  # Interrupted

        if kvmsg.key == b"KTHXBAI":
            sequence = kvmsg.sequence
            print(f"S: Received snapshot {sequence} {kvmap}")
            break  # Done
        kvmsg.store(kvmap)

    poller = zmq.Poller()
    poller.register(subscriber, zmq.POLLIN)

    alarm = time.time() + 1.0
    while True:
        tickless = 1000 * max(0, alarm - time.time())
        try:
            items = dict(poller.poll(tickless))
        except:
            break  # Interrupted

        if subscriber in items:
            kvmsg = KVMsg.recv(subscriber)

            # Discard out-of-sequence kvmsgs, incl. heartbeats
            if kvmsg.sequence > sequence:
                sequence = kvmsg.sequence
                kvmsg.store(kvmap)
                print(f"U: received {sequence} {kvmap}")

        # If we timed-out, generate a random kvmsg
        if time.time() >= alarm:
            kvmsg = KVMsg(0)
            kvmsg.key = ("%d" % random.randint(1, 10000)).encode()
            kvmsg.body = ("%d" % random.randint(1, 1000000)).encode()
            kvmsg.send(publisher)
            kvmsg.store(kvmap)
            alarm = time.time() + 1.0

    print(f"E: Interrupted\nE: {sequence} messages handled")


if __name__ == "__main__":
    main()
