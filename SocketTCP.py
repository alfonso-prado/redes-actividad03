import socket
import random
import time
import os

class SocketTCP:
    TIMEOUT = 0.5 
    MAX_DATA_SIZE = 16 # Máximo de datos por segmento, 16 bytes
    HEADER_SIZE = 7 # 3 flags de 1 byte + SEQ de 4 bytes.
    SEGMENT_SIZE = HEADER_SIZE + MAX_DATA_SIZE

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.TIMEOUT)

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
        self.debug = False

    # Server
    def bind(self, address):
        self.role = 'server'
        self.socket.bind(address)
        self.my_address = self.socket.getsockname()

    # Client
    def connect(self, address):
        self.role = 'client'
        self._clear_log()
        self.remote_address = address

        x = random.randint(0, 100)

        while True:       
            # TX: SYN, seq=x
            syn = { 'syn':True, 'seq': x }
            self._tx(address, syn)

            try:
                # RX: SYN+ACK, seq=x+1
                while True:
                    syn_ack, receive_address = self._rx(get_address=True) # Recibimos nueva address para comunicación con el servidor
                    if SocketTCP._match_flags(syn_ack, syn=True, ack=True) and syn_ack['seq'] == (x + 1) and not syn_ack['data']:
                        self.remote_address = receive_address                    
                        break
            except socket.timeout:
                self._log(f"RX: TIMEOUT")
                continue

            # TX: ACK, SEQ=x+2
            ack = { 'ack':True, 'seq': x + 2}
            self.seq = ack['seq']
            self._tx(self.remote_address, ack)
            self.conected = True
            break

    # Server
    def accept(self):
        self._clear_log()
        # RX: SYN, seq=x
        while True:
            try:
                syn, receiver_address = self._rx(get_address=True)
                if SocketTCP._match_flags(syn, syn=True) and not syn['data']:
                    break
            except socket.timeout:
                continue
        x = syn['seq']

        # crear nuevo socket para la comunicacion con el cliente, no se usa el socket principal
        new_socket = SocketTCP()
        host = self.my_address[0]
        new_socket.bind((host, 0)) # con 0 le digo al sistema que me de un puerto libre
        new_socket.remote_address = receiver_address # guardamos la direccion del cliente en el nuevo socket
        new_socket.debug = self.debug

        # Crea segmento SYN+ACK, seq=x+1
        syn_ack = {
            'syn':True, 
            'ack':True, 
            'seq': x + 1
        }

        while True:
            # TX: SYN+ACK, seq=x+1
            new_socket._tx(receiver_address, syn_ack)

            try:
                while True:
                    segment = new_socket._rx()
                    # RX: ACK, seq=x+2
                    if SocketTCP._match_flags(segment, ack = True) and segment['seq'] == (x + 2) and not segment['data'] :
                        new_socket.conected = True
                        new_socket.seq = segment['seq']
                        return new_socket, new_socket.my_address
                    # Caso de borde si se pierde ACK
                    elif new_socket._match_flags(segment) and segment['seq'] == (x + 2) and segment['data']:
                        new_socket.seq = segment['seq']
                        message_length = new_socket._receive_message_length(segment)
                        new_socket.remaining_bytes = message_length 
                        new_socket.conected = True
                        return new_socket, new_socket.my_address
            except socket.timeout:
                self._log(f"RX: TIMEOUT")
                continue

    # Client
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
                    self._log(f"RX: TIMEOUT")
                    continue  # Si hay timeout se reenvia el paquete anterior

    # Server
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
                self._log(f"RX: TIMEOUT")
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

    def close(self):
        z = self.seq

        # TX: FIN, seq=z
        fin = {
            'fin': True,
            'seq': z
        }
        self._tx(self.remote_address, fin)
        
        n_timeout = 0
        while n_timeout < 3:
            try:
                # RX: ACK, seq=z+1
                segment = self._rx()

                if (self._match_flags(segment, ack=True, fin=True) and segment['seq'] == z + 1 and not segment['data']):
                    for i in range(3):
                        # TX: ACK, seq=z+2
                        ack = {
                            'ack': True,
                            'seq': z + 2
                        }
                        self._tx(self.remote_address, ack)
                        if i < 2:
                            time.sleep(self.TIMEOUT)
                    break
            except socket.timeout:
                self._log(f"RX: TIMEOUT")
                n_timeout += 1
                
                if n_timeout < 3:
                    # TX: FIN, seq=z
                    self._tx(self.remote_address, fin)

        self.conected = False
        self.socket.close()

    def recv_close(self):
        z = self.seq

        waiting_ack = False
        n_timeout = 0
        while n_timeout < 3:
            try:
                segment = self._rx()

                # RX: FIN, seq=z
                if (self._match_flags(segment, fin=True) and segment['seq'] == z and not segment['data']):
                    waiting_ack = True
                    # TX: FIN+ACK, seq=z+1
                    fin_ack = {
                        'ack': True,
                        'fin': True,
                        'seq': z + 1
                    }
                    self._tx(self.remote_address, fin_ack)
               # RX: ACK, seq=z+2
                elif (waiting_ack and self._match_flags(segment, ack=True) and segment['seq'] == z + 2 and not segment['data']):   
                    break
                # puede pasar el caso que se perdio el ultimo ACK de recv()
                # esto sucede porque el cliente puede retransmitir un segmento (DATA)
                # mientras esperamos FIN
                # RX: seq=y, length=len(data)
                elif (self._match_flags(segment) and segment['seq'] < z and segment['data']):
                    # TX: ACK, seq=y + len(data)
                    ack = {
                        'ack': True,
                        'seq': z
                    }
                    self._tx(self.remote_address, ack)

            except socket.timeout:
                self._log(f"RX: TIMEOUT")
                if waiting_ack:
                    n_timeout += 1
                    
        self.conected = False
        self.socket.close()

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
                self._log(f"RX: TIMEOUT")
                continue # Se repite todo el proceso de nuevo
                # Si no llega el ACK (timeout) entonce envia de 
                # nuevo el segmento y espera por que llegue el ACK
                # correcto

    # Server
    def _receive_message_length(self, segment=None) -> int:
        while True:
            try:
                # RX: seq=y, data=message_length 
                if segment is None:
                    segment = self._rx()

                # Si segment['seq'] < self.seq  -> no almacenar nada, solo reenviar ACK. 
                # Caso de segmento duplicado
                if self._match_flags(segment) and segment['seq'] < self.seq:
                    # TX: Reenviar el último ACK
                    ack = {
                        'ack': True,
                        'seq': self.seq
                    }
                    self._tx(self.remote_address, ack)
                    segment = None
                    continue

                # Si segment['seq'] == self.seq -> recibe segmento esperado.
                # Caso de segmento que estamos esperando
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

                # Si el segmento no es el esperado,
                # esperamos uno nuevo
                segment = None
            except socket.timeout:
                self._log(f"RX: TIMEOUT")
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

            flags_enabled = {
                "SYN": sd['syn'],
                "ACK": sd['ack'],
                "FIN": sd['fin']
            }
            flags = "+".join(name for name, enabled in flags_enabled.items() if enabled) 
            if not flags and sd['data']:
                flags = f"DATA"
            elif not flags:
                flags = f"NO FLAGS"
        
            self._log(f"TX: {flags:<12} seq={sd['seq']:<11} bytes={len(sd['data'])}")

    def _log_rx(self, segment_dict: bytes):
        if self.debug:
            sd = segment_dict

            flags_enabled = {
                "SYN": sd['syn'],
                "ACK": sd['ack'],
                "FIN": sd['fin']
            }
            flags = "+".join(name for name, enabled in flags_enabled.items() if enabled) 
            if not flags and sd['data']:
                flags = f"DATA"
            elif not flags:
                flags = f"NO FLAGS"
        
            self._log(f"RX: {flags:<12} seq={sd['seq']:<11} bytes={len(sd['data'])}")

    def _clear_log(self):
        filename = f"log_{self.role}.txt"

        if self.debug:
            open(filename, 'w').close()
        elif os.path.exists(filename):
            os.remove(filename)