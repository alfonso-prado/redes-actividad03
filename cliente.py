import socket
import sys
from SocketTCP import SocketTCP

host = sys.argv[1]
puerto = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 0

while True:
    data = sys.stdin.buffer.read(16)

    if not data:
        break

    segment = SocketTCP.create_segment(seq=seq, data=data)

    sock.sendto(segment, (host, puerto))

    seq += len(data)

sock.close()