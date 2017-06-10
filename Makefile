MAIN = ./pychat.py

all:
	$(MAIN) --help

client:
	$(MAIN) --mode=client

server:
	$(MAIN) --mode=server

clean:
	$(RM) *.log *.pyc

.PHONY: all clean
