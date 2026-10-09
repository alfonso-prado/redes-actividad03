import socket
import sys

host = sys.argv[1]
puerto = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    data = sys.stdin.buffer.read(16)

    if not data:
        break

    sock.sendto(data, (host, puerto))

sock.close()