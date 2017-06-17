#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
----------
References
----------

    - https://www.gta.ufrj.br/~menezes/eel878/
    - https://docs.python.org/3/howto/argparse.html
    - https://docs.python.org/3/howto/logging.html
    - https://docs.python.org/3/howto/sockets.html
    - http://effbot.org/tkinterbook/
    - http://www.tkdocs.com/tutorial/
"""

import argparse
import logging
import queue
import select
import socket
import sys
import tkinter as tk
import threading


class ChatServer:

    def __init__(self,
                 host,
                 port,
                 logger=logging.getLogger('server')
                 ):
        self.host = host
        self.port = port
        self.logger = logger
        self.buffer_size = 1024
        self.max_connections = 5
        self.timeout = 1

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

        self.socket.listen(self.max_connections)

        self.inputs.add(self.socket)

        while self.inputs:
            rlist, wlist, _ = select.select(self.inputs,
                                            self.outputs,
                                            [],
                                            self.timeout)

            for s in rlist:
                if s is self.socket:
                    client_socket, client_address = s.accept()
                    self.logger.info('accepting from %s', client_address)

                    client_socket.setblocking(0)

                    self.inputs.add(client_socket)
                    self.msg_queues[client_socket] = queue.Queue()

                else:
                    buf = s.recv(self.buffer_size)
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
                 logger=logging.getLogger('client'),
                 receiver=None
                 ):
        self.host = host
        self.port = port
        self.logger = logger
        self.receiver = receiver
        self.buffer_size = 1024
        self.timeout = 1

        self.address = (self.host, self.port)
        self.msg_queue = queue.Queue()

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.logger.info('connecting to %s', self.address)
        
        try:
            self.socket.connect(self.address)
        except:
            self.logger.info('could not conect to server; exiting...')
            raise SystemExit
        self.sockets = [self.socket]
        
        self.local_addr = self.socket.getsockname()
        self.remote_addr = self.socket.getpeername()
        self.logger.info('%s connected to %s', self.local_addr, self.remote_addr)

        while self.sockets:
            rlist, wlist, xlist = select.select(self.sockets,
                                                self.sockets,
                                                self.sockets,
                                                self.timeout)

            for s in xlist:
                    self.closeConnection()

            for s in rlist:
                try:
                    buf = s.recv(self.buffer_size)
                    if len(buf) > 0:
                        self.logger.info('%s received from %s: %s', s.getsockname(), s.getpeername(), buf)
                        if self.receiver is not None:
                            self.receiver.receiveMessageAction(buf)
                except Exception as e:
                    self.logger.info('%s got exception: %s', self.local_addr, e)
                    self.closeConnection()
                    
            for s in wlist:
                if not self.msg_queue.empty():
                    msg = self.msg_queue.get().encode()
                    self.logger.info('%s sending to %s: %s', s.getsockname(), s.getpeername(), msg)
                    s.send(msg)

    def sendMessage(self, msg):
       self.msg_queue.put(msg)
       
    def closeConnection(self):
        self.logger.info('%s is closing connection with %s', self.local_addr,self.remote_addr)
        self.sockets = []
        self.socket.close()


class ChatGUI(tk.Frame):
    def __init__(self, root, host, port, width=800, height=800, *args, **kwargs):
        tk.Frame.__init__(self, root, *args, **kwargs)

        self.root = root
        self.width = width
        self.height = height
        self.chatClient = ChatClient(host=host, port=port, receiver=self)
        
        self.root.title("Cliente PyChat")
        self.root.geometry("%sx%s" % (self.width, self.height))
        
        self.menubar = tk.Menu(self.root, tearoff=False)
        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="Arquivo")
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Sair", command=self.quitAction)
        self.root.config(menu=self.menubar)
        
        self.chatText = tk.Text(self.root, bg="gray", state=tk.DISABLED)
        self.chatText.pack(fill=tk.X)
        
        self.messageText = tk.Text(self.root, bg="white")
        self.messageText.bind("<Return>", self.sendPressed)
        self.messageText.pack(fill=tk.X)
        
        self.sendButton = tk.Button(self.root, text="Enviar", command=self.sendButtonAction)
        self.sendButton.pack(fill=tk.X)

        self.bottomLabel = tk.Label(self.root, text="Criado por Thiago Perrotta e Heitor Guimarães")
        self.bottomLabel.pack(fill=tk.X)
        
        self.chatClientThread = threading.Thread(target=self.chatClient.start)
        self.chatClientThread.daemon = True # terminate if the main thread (Tk GUI) terminates
        self.chatClientThread.start()
        
    def quitAction(self):
        sys.exit(0)
        
    def receiveMessageAction(self, msg):
        self.chatText.config(state=tk.NORMAL)
        self.chatText.insert(tk.END, msg.decode())
        self.chatText.config(state=tk.DISABLED)

    def sendButtonAction(self):
        self.chatClient.sendMessage(self.messageText.get("1.0", tk.END))
        self.messageText.delete("1.0", tk.END)

    def sendPressed(self, event):
        self.sendButtonAction()


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
        ChatGUI(root, host, port).pack(side="top", fill="both", expand=True)
        root.mainloop()
        
    elif mode == 'server':
        sys.exit(ChatServer(host=host, port=port).start())

    else:
        print("error: mode must be either client or server")
        sys.exit(1)