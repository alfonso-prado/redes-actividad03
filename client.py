import SocketTCP
import sys

host = sys.argv[1]
puerto = int(sys.argv[2])

client = SocketTCP.SocketTCP()
client.connect((host, puerto))
client.debug = True

data = sys.stdin.buffer.read()

client.send(data)

client.close()