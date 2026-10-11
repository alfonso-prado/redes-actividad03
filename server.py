import SocketTCP

server_socketTCP = SocketTCP.SocketTCP()
server_socketTCP.bind(('localhost', 8000))
connection_socketTCP, new_address = server_socketTCP.accept()
