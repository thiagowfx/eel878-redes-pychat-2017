import logging
import select
import socket
import sys


class ChatServer:

    def __init__(self,
                 hostname='',
                 port=8000,
                 logger=logging.getLogger('server')
                 ):
        self.hostname = hostname
        self.port = port
        self.logger = logger

        self.inputs = []
        self.outputs = []

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)

        self.logger.info('starting on %s:%d', self.hostname, self.port)
        self.socket.bind((self.hostname, self.port))

        self.socket.listen(5)

        self.inputs.append(self.socket)

        while self.inputs:
            self.logger.info('waiting for next event')
            rlist, wlist, xlist = select.select(self.inputs,
                                                self.outputs,
                                                self.inputs)



        # self.logger.info('waiting to accept client connection')
        # (client, address) = self.socket.accept()

        return 0


if __name__ == '__main__':
    logging.basicConfig(filename='pychat.log',
                        filemode='w',
                        level=logging.INFO
                        )

    # TODO(tperrotta): argument parsing

    server = ChatServer()
    sys.exit(server.start())

# References:
#  - https://docs.python.org/3/howto/sockets.html
