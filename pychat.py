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
    - https://carlo-hamalainen.net/blog/2013/1/24/python-ssl-socket-echo-test-with-self-signed-certificate
"""

import argparse
import json
import logging
import pygame
import queue
import random
import select
import socket
import string
import ssl
import sys
import threading
import tkinter as tk

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

        # Constants
        self.certfile = 'server.crt'
        self.keyfile = 'server.key'

    def start(self):
        unsafe_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Wrap socket with SSL using AES256
        self.socket = ssl.wrap_socket(unsafe_socket,
            server_side = True,
            certfile = self.certfile,
            keyfile = self.keyfile,
            ssl_version=ssl.PROTOCOL_TLSv1)

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
                 gui=None
                 ):
        self.host = host
        self.port = port
        self.logger = logger
        self.gui = gui
        self.buffer_size = 1024
        self.timeout = 1

        self.address = (self.host, self.port)
        self.msg_queue = queue.Queue()

        # Constants
        self.ca_certs = 'server.crt'
        self.hostname = 'com.pychat.s2017'

    def start(self):
        unsafe_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Wrap the socket with SSL
        self.socket = ssl.wrap_socket(unsafe_socket,
            ca_certs = self.ca_certs,
            cert_reqs = ssl.CERT_REQUIRED,
            ssl_version = ssl.PROTOCOL_TLSv1)

        self.logger.info('connecting to %s', self.address)
        try:
            self.socket.connect(self.address)
            cert = self.socket.getpeercert()
            ssl.match_hostname(cert, self.hostname)
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
                        if self.gui is not None:
                            self.gui.receiveMessageAction(buf.decode())
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
    def __init__(self, root, host, port, width=650, height=420, *args, **kwargs):
        tk.Frame.__init__(self, root, *args, **kwargs)

        self.root = root
        self.width = width
        self.height = height
        self.chatClient = ChatClient(host=host, port=port, gui=self)

        # Cheat definitions
        self.cheatCommands = ['/nick', '/nickname', '/me',
            '/list_colors', '/color', '/shock', '/help']
        self.cheatSettings = {
            'nickname': 'Anônimo'
        }

        # Defining colors
        self.colors = {
            'roxo':'#770f5d',
            'verde':'#21a540',
            'preto':'black',
            'amarelo':'#df9400',
            'vermelho':'#b41435',
            'azul':'#011f8f',
            'cinza':'#666666'
        }
        self.selectedColor = random.choice(list(self.colors.keys()))

        # Generate a random tag for a user (used for name color)
        self.user_tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))

        self.root.title("Cliente PyChat")
        self.root.geometry("%sx%s" % (self.width, self.height))
        self.root.resizable(width=False, height=False)

        self.menubar = tk.Menu(self.root, tearoff=False)
        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="Arquivo")
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Sair", command=self.quitAction)
        self.root.config(menu=self.menubar)

        self.chatText = tk.Text(self.root, bg="gray", state=tk.DISABLED)
        self.chatText.tag_configure("ntext", font="Helvetica 9")
        self.chatText.place(x=6,y=6, height=300, width=550)

        self.messageText = tk.Text(self.root, bg="white")
        self.messageText.bind("<Return>", self.sendPressed)
        self.messageText.place(x=6, y=310, height=80, width=550)

        self.scrollbar = tk.Scrollbar(self.root, command=self.chatText.yview, cursor="heart")
        self.chatText['yscrollcommand'] = self.scrollbar.set
        self.scrollbar.place(x=550, y=6, height=300, width=15)

        self.sendButton = tk.Button(self.root, text="Enviar", command=self.sendButtonAction)
        self.sendButton.place(x=562, y=310, height=80,width=80)

        self.bottomLabel = tk.Label(self.root, text="Criado por Thiago Perrotta e Heitor Guimarães")
        self.bottomLabel.config(font=("Helvetica", 9))
        self.bottomLabel.place(x=6,y=390)

        self.chatClientThread = threading.Thread(target=self.chatClient.start)
        self.chatClientThread.daemon = True # terminate if the main thread (Tk GUI) terminates
        self.chatClientThread.start()

    def quitAction(self):
        sys.exit(0)

    def receiveMessageAction(self, body_str, play_notify = True):
        body = json.loads(body_str)
        self.chatText.config(state=tk.NORMAL)
        self.chatText.tag_configure(body['user_tag'], font='Helvetica 9 bold', foreground=body['color'])
        # Call nudge
        if body['msg'] == '/shock':
            self.chatText.insert(tk.END, body['nickname'] + ' ', body['user_tag'])
            self.chatText.insert(tk.END, 'chamou a atenção do grupo', 'ntext')

            # New thread to play the msn msg sound notify
            thread = threading.Thread(target = play_notify_msn, args=('msnnudge.wav',))
            thread.start()

        # Just a normal msg
        else:
            self.chatText.insert(tk.END, body['nickname'] + ': ', body['user_tag'])
            self.chatText.insert(tk.END, body['msg'], 'ntext')
            
            # New thread to play the msn msg sound notify
            if play_notify:
                thread = threading.Thread(target = play_notify_msn)
                thread.start()

        self.chatText.config(state=tk.DISABLED)
        self.chatText.see(tk.END)

    def sendButtonAction(self):
        input_msg = self.messageText.get("1.0", tk.END)
        parsed_msg = self.parseMSG(input_msg)

        # If is not a /nick, just send to server
        if parsed_msg:
            body = {
                'nickname': self.cheatSettings.get('nickname'),
                'color': self.colors[self.selectedColor],
                'msg': parsed_msg,
                'user_tag': self.user_tag
            }
            body_str = json.dumps(body)

            self.chatClient.sendMessage(body_str)
            self.receiveMessageAction(body_str, play_notify=False)

        # Clear Text box
        self.messageText.delete("1.0", tk.END)

    def sendPressed(self, event):
        self.sendButtonAction()
        return 'break'

    def parseMSG(self, text):
        response = text
        first_word = text.split(' ')[0].rstrip()

        # Check if the first word is a special command and process
        if first_word in self.cheatCommands:
            # Change the nickname of the user
            if first_word == '/nick' or first_word == '/nickname':
                response = ''
                self.cheatSettings['nickname'] = ' '.join(text.split(' ')[1:]).rstrip()

            # Use 3rd person on the message
            elif first_word == '/me':
                ntext = text.replace('/me', self.cheatSettings.get('nickname'))
                response = ntext

            # Print the list of available colors for a specific user
            elif first_word == '/list_colors':
                response = ''
                self.receiveMessageAction(json.dumps({
                    'nickname': 'pychat.bot',
                    'color': '#ffffff',
                    'msg': str(list(self.colors.keys())) + '\n',
                    'user_tag': '000ABC'
                }))

            # Change the color of a user
            elif first_word == '/color':
                response = ''
                color = text.split(' ')[1].rstrip()
                if color in self.colors.keys():
                    self.selectedColor = color
                else:
                    self.receiveMessageAction(json.dumps({
                        'nickname': 'pychat.bot',
                        'color': '#ffffff',
                        'msg': 'Invalid Color. Type /list_colors to see the full list\n',
                        'user_tag': '000ABC'
                    }))
            # Send a "Call atention" (msn nudge)
            elif first_word == '/shock':
                response = '/shock'

            # Call for help
            elif first_word == '/help':
                response = ''
                help_msg = """Lista de comandos do pychat
                 ├── /nick (ou /nickname) X :: Mudar seu nome para X
                 ├── /me [frase] :: Enviar frase na terceira pessoa (ex: /me ta com fome)
                 ├── /list_colors :: Mostrar as cores disponiveis para um nickname
                 ├── /color X :: Mudar a cor do seu nick para X
                 ├── /shock :: Chamar atenção dos usuários
                 ├── /help :: this\n"""

                self.receiveMessageAction(json.dumps({
                    'nickname': 'pychat.bot',
                    'color': '#ffffff',
                    'msg': help_msg,
                    'user_tag': '000ABC'
                }))

        # Return the response
        return response

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

def play_notify_msn(filepath='msnsound.wav'):
    pygame.init()
    pygame.mixer.init()
    sound = pygame.mixer.Sound(filepath)
    clock = pygame.time.Clock()
    sound.play()

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
