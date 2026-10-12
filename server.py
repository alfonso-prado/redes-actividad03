import SocketTCP
import sys

server = SocketTCP.SocketTCP()
server.bind(('localhost', 8000))

connection, address = server.accept()

while True:
    data = connection.recv(19)
    sys.stdout.buffer.write(data)

    if len(data) < 19:
        break

connection.recv_close()