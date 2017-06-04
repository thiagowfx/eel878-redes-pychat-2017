#!/usr/bin/env python3

import argparse
import logging
import select
import socket
import sys


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

        self.inputs = []
        self.outputs = []

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)

        self.logger.info('starting on %s', self.address)
        self.socket.bind(self.address)

        self.socket.listen(5)

        self.inputs.append(self.socket)

        while self.inputs:
            rlist, wlist, _ = select.select(self.inputs,
                                                self.outputs,
                                                [])

            for s in rlist:
                if s is self.socket:
                    client_socket, client_address = s.accept()
                    self.logger.info('accepting from %s', client_address)

                    client_socket.setblocking(0)
                    self.inputs.append(client_socket)

                else:
                    # TODO: receive from client
                    pass

            for s in wlist:
                # TODO: write to client
                pass

        return 0


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

        self.inputs = []
        self.outputs = []

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.logger.info('connecting to %s', self.address)
        self.socket.connect(self.address)

        self.inputs.append(self.socket)

        while self.inputs:
            rlist, wlist, _ = select.select(self.inputs,
                                            self.outputs,
                                            [])

            for s in rlist:
                pass


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
    parser.add_argument("mode", help="client or server", type=str)

    return parser.parse_args()

if __name__ == '__main__':
    set_up_logging()
    args = set_up_argparse()

    port = args.port if args.port else 9000
    host = args.host if args.port else ''
    mode = args.mode

    if mode == 'client':
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
