import SocketTCP
import sys

host = sys.argv[1]
puerto = int(sys.argv[2])

client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect((host, puerto))

data = sys.stdin.buffer.read()

client_socketTCP.send(data)
