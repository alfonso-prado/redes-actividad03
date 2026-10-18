# Actividad 3 - SocketTCP con Stop & Wait

Implementación de sockets orientados a conexión sobre UDP, utilizando Stop & Wait para manejar la transmisión de datos y las pérdidas de segmentos.

## Ejecución de scripts

La versión final del proyecto cuenta con tres casos de prueba. En cada caso, ejecutar primero el servidor y luego el cliente en otra terminal.

### 1. Prueba general

Servidor:

```bash
python3 server.py > test_recibido.txt
```

Cliente:

```bash
python3 client.py localhost 8000 < test.txt
```

El archivo recibido se guarda en `test_recibido.txt`.

### 2. Test del paso 5

Usamos los códigos del cliente y servidor entregados al final del enunciado, en la sección «Material e indicaciones para la actividad».

Servidor:

```bash
python3 test_server.py
```

Cliente:

```bash
python3 test_client.py
```

### 3. Prueba de recepción parcial mediante `recv(buff_size)`

Corresponde a la Prueba 2 de la sección «Pruebas» del informe. Enviamos un mensaje de 28 bytes y hacemos dos llamadas a `recv(14)` para comprobar que se recibe completo sin perder datos.

Servidor:

```bash
python3 test2_server.py
```

Cliente:

```bash
python3 test2_client.py
```

## Simulación de pérdidas con Netem

Para simular un 20 % de pérdida de segmentos en cualquiera de las pruebas, ejecutar antes:

```bash
sudo tc qdisc replace dev lo root netem loss 20%
```

Al terminar, desactivar la configuración:

```bash
sudo tc qdisc del dev lo root
```

## Modo debug

Para activar el registro de eventos, establecer `debug = True` en las instancias de `SocketTCP` antes de llamar a `connect()` o `accept()`.

Los registros se guardan en `log_client.txt` y `log_server.txt`, donde se pueden revisar los segmentos enviados, recibidos y los timeouts. Los archivos se limpian al iniciar una nueva ejecución con debug activado.