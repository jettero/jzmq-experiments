# wassis?

Dunno... just playing around with ØMQ for the sake of trying to figure out what
all the sockets really do or don't do or whatever. There's a lot of information
on http://zguide.zeromq.org/py:all ; it's almost just too much to deal with ...
while at the same time, it leaves me wondering REP? PUSH? DEALER? ... WTF?

# Mah Table

As I try to figure some of this out, I'm going to try to create a table of what
these sockets are and how they do or what they be... I guess.

| Type | Endpoint   | Direction | Pattern                   |
|------|------------|-----------|---------------------------|
| REQ  | REP/ROUTER | both      | send, recv, send, recv, … |
