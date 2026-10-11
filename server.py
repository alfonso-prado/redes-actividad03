import socket
import sys
from SocketTCP import SocketTCP

puerto = 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", puerto))

while True:
    message, addr = sock.recvfrom(SocketTCP.MESSAGE_SIZE)

    segment = SocketTCP.parse_segment(message)

    data = segment['data']

    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()