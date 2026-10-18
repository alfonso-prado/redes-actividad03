import SocketTCP
import sys

host = sys.argv[1]
puerto = int(sys.argv[2])

client = SocketTCP.SocketTCP()
client.debug = True
client.connect((host, puerto))

data = sys.stdin.buffer.read()

client.send(data)

client.close()