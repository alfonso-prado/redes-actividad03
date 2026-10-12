import socket
import random

class SocketTCP:
    TIMEOUT = 1 
    MAX_DATA_SIZE = 16 # Máximo de datos por segmento, 16 bytes
    HEADER_SIZE = 7 # 3 flags de 1 byte + SEQ de 4 bytes.
    SEGMENT_SIZE = HEADER_SIZE + MAX_DATA_SIZE

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Estas direcciones pueden corresponder al cliente o al servidor,
        # dependiendo de quién esté utilizando el socket.
        self.my_address = None # (IP, PUERTO)
        self.remote_address = None # (IP, PUERTO)

        # Handshake
        self.conected = False
        self.seq = None

        self.remaining_bytes = None # cuandos bytes quedan pendientes de entregar por recv()
        self.recv_buffer = b'' # buffer que se han recibido pero no entregado

        # debug
        self.role = None 
        self.debug = True

    # Server
    def bind(self, address):
        self.role = 'server'
        self.socket.bind(address)
        self.my_address = self.socket.getsockname()

    # Client
    def connect(self, address):
        self.role = 'client'
        self.remote_address = address

        # TX: SYN, seq=x
        x = random.randint(0, 100)
        syn = { 'syn':True, 'seq': x }
        self._tx(address, syn)

        while True:
            # RX: SYN+ACK, seq=x+1
            syn_ack, sender_address = self._rx(get_address=True) # Recibimos nueva address para comunicación con el servidor
            if SocketTCP._match_flags(syn_ack, syn=True, ack=True) and syn_ack['seq'] == (x + 1) and not syn_ack['data']:
                self.remote_address = sender_address
                self.conected = True
                break

        # TX: ACK, SEQ=x+2
        ack = { 'ack':True, 'seq': x + 2}
        self.seq = ack['seq']
        self._tx(self.remote_address, ack)

    # Server
    def accept(self):
        # RX: SYN, seq=x
        while True:
            syn, receiver_address = self._rx(get_address=True)
            if SocketTCP._match_flags(syn, syn=True) and not syn['data']:
                break
        x = syn['seq']

        # crear nuevo socket para la comunicacion con el cliente, no se usa el socket principal
        new_socket = SocketTCP()
        host = self.my_address[0]
        new_socket.bind((host, 0)) # con 0 le digo al sistema que me de un puerto libre
        new_socket.remote_address = receiver_address # guardamos la direccion del cliente en el nuevo socket

        # TX: SYN+ACK, seq=x+1
        syn_ack = {
            'syn':True, 
            'ack':True, 
            'seq': x + 1
        }
        new_socket._tx(receiver_address, syn_ack)

        while True:
            # RX: ACK, seq=x+1
            ack = new_socket._rx()
            if SocketTCP._match_flags(ack, ack = True) and not ack['data'] and ack['seq'] == (x + 2) :
                new_socket.conected = True
                new_socket.seq = ack['seq']
                return new_socket, new_socket.remote_address

    def send(self, message: bytes):
        self._send_message_length(message)

        for i in range(0, len(message), self.MAX_DATA_SIZE):
            data = message[i:i + self.MAX_DATA_SIZE]
            segment = {
                'seq': self.seq,
                'data': data
            }

            expected_ack = self.seq + len(data)

            while True:
                # TX: seq=y, length=len(data)
                self._tx(self.remote_address, segment)
                try:
                    while True:
                        # RX: ack, seq=y, length=len(data)
                        ack = self._rx()

                        if (self._match_flags(ack, ack=True) and ack['seq'] == expected_ack and not ack['data']):
                            self.seq = expected_ack
                            break
                    break  # enviar el siguiente segmento
                except socket.timeout:
                    continue  # Si hay timeout se reenvia el paquete anterior


    def recv(self, buff_size: int) -> bytes:
        if buff_size < 0:
            raise ValueError("buff_size no puede ser negativo")

        if buff_size == 0:
            return b''
        
        # recibir tamaño archivo, solo empieza si comienza a enviar un nuevo mensaje
        if self.remaining_bytes is None:
            message_length = self._receive_message_length()
            self.remaining_bytes = message_length

        # cantidad de bytes que se tienen que devolver
        target = min(self.remaining_bytes, buff_size)

        while len(self.recv_buffer) < target:
            try:
                # RX: seq=y, length=len(data)
                segment = self._rx()

                # ignora segmentos con flags activos o sin datos
                if not self._match_flags(segment) or not segment['data']:
                    continue

                # Si segment['seq'] < self.seq  -> no almacenar nada, solo reenviar ACK. 
                # Caso de segmento duplicado
                if segment['seq'] < self.seq:
                    # TX: ACK, seq=y + len(data)
                    ack = {
                        'ack': True,
                        'seq': self.seq
                    }
                    self._tx(self.remote_address, ack)
                    continue
                # Si segment['seq'] == self.seq -> recibe segmento esperado.
                # Caso de segmento que estamos esperando
                elif segment['seq'] == self.seq:
                    data = segment['data']

                    # no debe execer los bytes faltanes del mensaje
                    if len(data) > self.remaining_bytes - len(self.recv_buffer):
                        continue

                    self.recv_buffer += data
                    self.seq += len(data)

                    # TX: ACK, seq=y + len(data)
                    ack = {
                        'ack': True,
                        'seq': self.seq
                    }
                    self._tx(self.remote_address, ack)
            except socket.timeout:
                continue

        # saca solamente los bytes requeridos
        message_received = self.recv_buffer[:target]

        # matiene los bytes que sobraron
        self.recv_buffer = self.recv_buffer[target:]

        # actualiza la cantidad pendiente a entregar
        self.remaining_bytes -= len(message_received)

        # ya se envio todo el mensaje y prepara para siguiente mensaje
        if self.remaining_bytes == 0:
            self.remaining_bytes = None

        return message_received

    # Client
    def _send_message_length(self, message: bytes):
        # Obs: El tamaño máximo teórico de un archivo en bytes que se puede enviar 
        # en esta implementación de TCP sería de 2^128 - 1, porque la parte 
        # del segmento donde van los datos es de un tamaño de 16 bytes = 16 * 8 bit = 128 bits.
        message_length = len(message).to_bytes(16, 'big') 

        segment = {
            'seq': self.seq,
            'data': message_length
        }

        expected_seq = self.seq + len(message_length)

        while True:
            # TX: seq=y, length=len(message_length)
            self._tx(self.remote_address, segment)

            try:
                while True:
                    # RX: ack, seq=y, length=len(data)
                    ack = self._rx()
                    # Revisa que es el ACK correspondiente, sino lo ignora y espera hasta que llegue el correcto o
                    # que haya timeout
                    if SocketTCP._match_flags(ack, ack = True) and ack['seq'] == expected_seq and not ack['data']:
                        self.seq = expected_seq
                        return
            except socket.timeout:
                continue # Se repite todo el proceso de nuevo
                # Si no llega el ACK (timeout) entonce envia de 
                # nuevo el segmento y espera por que llegue el ACK
                # correcto


    # Server
    def _receive_message_length(self) -> int:
        while True:
            try:
                # RX: seq=y, data=message_length 
                segment = self._rx()

                if self._match_flags(segment) and segment['seq'] == self.seq and segment['data']:
                    new_seq = segment['seq'] + len(segment['data'])

                    # TX: ACK, seq=y + len(message_length)
                    ack = {
                        'ack': True,
                        'seq': new_seq
                    }
                    self._tx(self.remote_address, ack)
                    
                    message_length = int.from_bytes(segment['data'], 'big')
                    self.seq = new_seq

                    return message_length
            except socket.timeout:
                continue
            

    def _tx(self, address, segment: dict):
        segment_byte = SocketTCP.create_segment(**segment)
        self.socket.sendto(segment_byte, address)
        self._log_tx(segment_byte)

    def _rx(self, get_address=False):
        segment_byte, address = self.socket.recvfrom(self.SEGMENT_SIZE)
        segment_dict = SocketTCP.parse_segment(segment_byte)
        self._log_rx(segment_dict)
        if get_address:
            return segment_dict, address
        return segment_dict

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
            'data': segment[SocketTCP.HEADER_SIZE:SocketTCP.SEGMENT_SIZE], # MAX 16 bytes. En el caso que se pase de los 16bytes, ignora el resto
        }

    @staticmethod
    def _match_flags(segment_dict: dict, syn=False, ack=False, fin=False) -> bool:
        return (
            segment_dict['syn'] == syn and
            segment_dict['ack'] == ack and
            segment_dict['fin'] == fin
        )

    def _log(self, text):
        if self.debug:
            filename = f"log_{self.role}.txt"

            with open(filename, 'a', encoding='utf-8') as file:
                file.write(text + '\n')

    def _log_tx(self, segment_byte: bytes):
        if self.debug:
            sd = self.parse_segment(segment_byte)

            flags = {
                "SYN": sd['syn'],
                "ACK": sd['ack'],
                "FIN": sd['fin']
            }
            flags_enabled = "+".join(name for name, enabled in flags.items() if enabled)
            if not flags_enabled:
                flags_enabled = f"NO FLAGS"
        
            self._log(f"TX: {flags_enabled:<12} seq={sd['seq']:<11} bytes={len(sd['data'])}")

    def _log_rx(self, segment_dict: bytes):
        if self.debug:
            sd = segment_dict

            flags = {
                "SYN": sd['syn'],
                "ACK": sd['ack'],
                "FIN": sd['fin']
            }
            flags_enabled = "+".join(name for name, enabled in flags.items() if enabled) 
            if not flags_enabled:
                flags_enabled = f"NO FLAGS"
        
            self._log(f"RX: {flags_enabled:<12} seq={sd['seq']:<11} bytes={len(sd['data'])}")