import SocketTCP

address = ("127.0.0.1", 8000)

server_socketTCP = SocketTCP.SocketTCP()
server_socketTCP.bind(address)
server_socketTCP.debug = True
connection_socketTCP, new_address = server_socketTCP.accept()

buff_size = 14

message_part_1 = connection_socketTCP.recv(buff_size)
message_part_2 = connection_socketTCP.recv(buff_size)

full_message = message_part_1 + message_part_2

print("Test received:", full_message)

if (full_message == b'Mi ACK se perdio en Beauchef'
        and len(message_part_1) == 14
        and len(message_part_2) == 14):
    print("Test: Passed")
else:
    print("Test: Failed")

connection_socketTCP.recv_close()
server_socketTCP.socket.close()