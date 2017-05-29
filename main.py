import logging
import socket
import sys


class ChatServer:

    logger = logging.getLogger('server')

    def __init__(self,
                 hostname='',
                 port=8000,
                 ):
        self.hostname = hostname
        self.port = port

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        logger.info('Starting on %s:%d', self.hostname, self.port)
        self.socket.bind((self.hostname, self.port))

        self.socket.listen(5)

        logging.getLogger('server').info('Waiting to accept client connection...')
        # (client, address) = self.socket.accept()

        return 0


if __name__ == '__main__':
    logging.basicConfig(filename='main.log',
                        filemode='w',
                        format='%(levelname)s:%(asctime)s:%(name)s:%(module)s.%(funcName)s:%(message)s',
                        level=logging.INFO
                        )

    server = ChatServer()
    sys.exit(server.start())

# References:
#  - https://docs.python.org/3/howto/sockets.html
