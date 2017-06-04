server: start_server

client: start_client

start_server:
	./pychat.py server

start_client:
	./pychat.py client

clean:
	$(RM) *.log

.PHONY: clean
