class SocketTCP:
    TIMEOUT = 0.5   
    MAX_DATA_SIZE = 16 # Máximo de datos por segmento, 16 bytes
    HEADER_SIZE = 7 # 3 flags de 1 byte + SEQ de 4 bytes.
    MESSAGE_SIZE = HEADER_SIZE + MAX_DATA_SIZE

    def __init__(self):
        # Estas direcciones pueden corresponder al cliente o al servidor,
        # dependiendo de quién esté utilizando el socket.
        self.my_address = None # (IP, PUERTO)
        self.remote_address = None # (IP, PUERTO)

        self.seq = None 

        self.handshake = False 

    @staticmethod
    def create_segment(syn: bool = False, ack: bool = False, fin: bool = False, seq=0, data: bytes = b'') -> bytes:
        header = bytes([int(syn), int(ack), int(fin)]) # 3 bytes en total, siendo un byte por cada uno syn, ack, fin
        header += seq.to_bytes(4, 'big') # 4 bytes -> orden en big little
        return header + bytes(data[:SocketTCP.MAX_DATA_SIZE]) # header 7 bytes, data entre 0 a 16 bytes. En el caso que se pase de los 16bytes, ignora el resto

    @staticmethod
    def parse_segment(segment: bytes) -> dict:
        return {
            'syn': bool(segment[0]),
            'ack': bool(segment[1]),
            'fin': bool(segment[2]),
            'seq': int.from_bytes(segment[3:SocketTCP.HEADER_SIZE], 'big'), # 4 bytes
            'data': segment[SocketTCP.HEADER_SIZE:SocketTCP.MESSAGE_SIZE], # MAX 16 bytes. En el caso que se pase de los 16bytes, ignora el resto
        }