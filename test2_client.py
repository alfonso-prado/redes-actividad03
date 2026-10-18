import SocketTCP

address = ("127.0.0.1", 8000)

# CLIENT
client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.debug = True
client_socketTCP.connect(address)

print("Cliente conectado.")

# 28 bytes (2n, donde n = 14)
message = 'Mi ACK se perdio en Beauchef'.encode()
client_socketTCP.send(message)  
print("Test sent:", message)

client_socketTCP.close()