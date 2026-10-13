import SocketTCP

address = ("127.0.0.1", 8000)

# CLIENT
client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(address)
print("Cliente conectado.")

# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message)
print("Test 1 sent:", message)

# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
print("Test 2 sent:", message)

# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
print("Test 3 sent:", message)

client_socketTCP.close()

