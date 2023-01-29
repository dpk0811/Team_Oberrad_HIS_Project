# this file contains the basics of socket connection
# understanding how a connection works we can exploit
# and use it in DOS attack

# https://www.internalpointers.com/post/making-http-requests-sockets-python

# In words: give me (GET) the index page (/) through HTTP version 1.1 
# (HTTP comes in multiple versions, 1.1 is OK for our purpose) from the 
# host called www.example.com. Fields are separated by \r\n and the 
# request ends with \r\n\r\n.

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("www.rtgshop.com", 80))
sock.send(b"GET / HTTP/1.1\r\nHost:www.rtgshop.com\r\n\r\n")
response = sock.recv(4096)
sock.close()
print(response.decode())
