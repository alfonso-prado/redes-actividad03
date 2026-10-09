import socket
import sys

puerto = 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", puerto))

while True:
    data, addr = sock.recvfrom(16)

    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()