import SocketTCP
import sys

server = SocketTCP.SocketTCP()
server.bind(('localhost', 8000))
server.debug = True

connection, address = server.accept()

while True:
    data = connection.recv(19)
    sys.stdout.buffer.write(data)

    if connection.remaining_bytes is None:
        break

connection.recv_close()