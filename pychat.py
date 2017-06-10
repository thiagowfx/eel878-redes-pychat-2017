#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import queue
import select
import socket
import sys
import tkinter as tk

BUFFER_SIZE = 1024


class ChatServer:

    def __init__(self,
                 host,
                 port,
                 logger=logging.getLogger('server')
                 ):
        self.host = host
        self.port = port
        self.logger = logger

        self.address = (self.host, self.port)

        self.inputs = set()
        self.outputs = set()

        # dict of socket -> queue<str>
        self.msg_queues = {}

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)

        self.logger.info('starting on %s', self.address)
        self.socket.bind(self.address)

        self.socket.listen(5)

        self.inputs.add(self.socket)

        while self.inputs:
            rlist, wlist, _ = select.select(self.inputs,
                                            self.outputs,
                                            [])

            for s in rlist:
                if s is self.socket:
                    client_socket, client_address = s.accept()
                    self.logger.info('accepting from %s', client_address)

                    client_socket.setblocking(0)

                    self.inputs.add(client_socket)
                    self.msg_queues[client_socket] = queue.Queue()

                else:
                    buf = s.recv(BUFFER_SIZE)
                    if len(buf) > 0:
                        self.logger.info('received from %s: %s', s.getpeername(), buf)
                        self.broadcast_msg_async(buf, s)

            for s in wlist:
                msg_queue = self.msg_queues[s]

                if not msg_queue.empty():
                    msg = msg_queue.get()
                    self.logger.info('sending to %s: %s', s.getpeername(), msg)
                    s.send(msg)

                    if msg_queue.empty():
                        self.outputs.remove(s)

        return 0

    def broadcast_msg_async(self, msg, sender):
        for s, msg_queue in self.msg_queues.items():
            if s is not sender:
                msg_queue.put(msg)
                self.outputs.add(s)


class ChatClient:
    def __init__(self,
                 host,
                 port,
                 logger=logging.getLogger('client')
                 ):
        self.host = host
        self.port = port
        self.logger = logger

        self.address = (self.host, self.port)

        self.inputs = set()
        self.outputs = set()

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.logger.info('connecting to %s', self.address)
        self.socket.connect(self.address)

        self.inputs.add(self.socket)

        while self.inputs:
            rlist, wlist, _ = select.select(self.inputs,
                                            self.outputs,
                                            [])

            for s in rlist:
                buf = s.recv(BUFFER_SIZE)
                if len(buf) > 0:
                    self.logger.info('received from %s: %s', s.getpeername(), buf)


class ChatGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.parent.title("PyChat")

        self.label = tk.Label(parent, text="Label")
        self.label.pack()


def set_up_logging():
    logging.basicConfig(filename='pychat.log',
                        filemode='a',
                        level=logging.INFO
                        )
    logging.getLogger().addHandler(logging.StreamHandler())


def set_up_argparse():
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", help="the socket host", type=str)
    parser.add_argument("--port", help="the socket port", type=int)
    parser.add_argument("--mode", help="client or server", type=str)

    return parser.parse_args()

if __name__ == '__main__':
    set_up_logging()
    args = set_up_argparse()

    port = args.port if args.port else 9000
    host = args.host if args.host else ''
    mode = args.mode

    if mode == 'client':
        root = tk.Tk()
        ChatGUI(root).pack(side="top", fill="both", expand=True)
        root.mainloop()
        sys.exit(ChatClient(host=host, port=port).start())
    elif mode == 'server':
        sys.exit(ChatServer(host=host, port=port).start())
    else:
        print("error: mode must be either client or server")
        sys.exit(1)


# References:
#  - https://docs.python.org/3/howto/argparse.html
#  - https://docs.python.org/3/howto/logging.html
#  - https://docs.python.org/3/howto/sockets.html
#  - https://www.gta.ufrj.br/~menezes/eel878/
