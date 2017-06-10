MAIN = ./pychat.py

all:
	$(MAIN) --help

client:
	$(MAIN) client

server:
	$(MAIN) server

clean:
	$(RM) *.log *.pyc

.PHONY: all clean
