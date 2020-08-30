# wassis?

Dunno... just playing around with ØMQ for the sake of trying to figure out what
all the sockets really do or don't do or whatever. There's a lot of information
on http://zguide.zeromq.org/py:all ; it's almost just too much to deal with ...
while at the same time, it leaves me wondering REP? PUSH? DEALER? ... WTF?

# Mah Table

As I try to figure some of this out, I'm going to try to create a table of what
these sockets are and how they do or what they be... I guess.

| Type   | Endpoint            | Direction | Pattern                   | out         | in          | mute  |
|--------|---------------------|-----------|---------------------------|-------------|-------------|-------|
| REQ    | REP, ROUTER         | both      | send, recv, send, recv, … | round-robin | last peer   | block |
| REP    | REQ, DEALER         | both      | recv, send, recv, send, … | fair-robin  | last peer   | n/a   |
| DEALER | ROUTER, REP, DEALER | both      | unrestricted              | round-robin | fair-queued | block |
| ROUTER | DEALER, REQ, ROUTER | both      | unrestricted              | ???         | fair-queued | drop  |
| PUB    | SUB, XSUB           | uni       | send-only                 | fan out     | n/a         | drop  |
| SUB    | PUB, XPUB           | uni       | recv-only                 | n/a         | fair-queued | n/a   |
| XPUB   | SUB, XSUB           | uni       | send / recv-subscription  | fan out     | n/a         | drop  |
| XSUB   | PUB, XPUB           | uni       | recv / send-subscription  | n/a         | fair-queued | drop  |
| PUSH   | PULL                | uni       | send-only                 | round-robin | n/a         | block |
| PULL   | PUSH                | uni       | recv-only                 | n/a         | fair-queued | block |

# skipped

I'm leaving out PAIR, SERVER/CLIENT, and RADIO/DISH. PAIR is for inproc multi-threaded
communication and I don't much care about it. The rest are still in draft.

# EARLS

All my EARLS are Python-centric where possible.

* https://zeromq.org/get-started/
* https://pyzmq.readthedocs.io/en/latest/
* http://zguide.zeromq.org/py:all
