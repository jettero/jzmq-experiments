#!/usr/bin/env python
# coding: utf-8

import time
import threading

from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout

PROMPT = "old/prompt-toolkit-example> "
ALIVE = True


def slowly_send_spam():
    while ALIVE:
        print("from thread: spam")

        end_sleep = time.time() + 2
        while ALIVE and time.time() < end_sleep:
            time.sleep(0.1)


def go():
    global ALIVE

    hrm = threading.Thread(target=slowly_send_spam)
    hrm.start()

    with patch_stdout():
        while ALIVE:
            try:
                line = prompt(PROMPT)
            except KeyboardInterrupt:
                print("from you: ^C break")
                break
            except EOFError:
                print("from you: EOF")
                break

            if line.lower().strip() in ("exit", "stop", "quit"):
                print("from you:", line, "(quitting)")
                break

            if line and line.strip():
                print("from you:", line)

    print("exited loop, waiting for spam thread join")
    ALIVE = False
    hrm.join()


if __name__ == "__main__":
    go()
