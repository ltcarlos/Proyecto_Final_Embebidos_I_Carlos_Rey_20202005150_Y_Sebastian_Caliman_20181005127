import socket
import cv2
import numpy as np

WIDTH = 80
HEIGHT = 60
IP_DEL_PICO_W = "192.168.197.208"

def rgb565_to_bgr888(data):
    arr = np.frombuffer(data, dtype=np.uint8).reshape((HEIGHT, WIDTH, 2))
    r = ((arr[:, :, 0] & 0xF8) >> 3) << 3
    g = (((arr[:, :, 0] & 0x07) << 3) | ((arr[:, :, 1] & 0xE0) >> 5)) << 2
    b = (arr[:, :, 1] & 0x1F) << 3
    return cv2.merge((b, g, r))

def recv_exact(sock, size):
    buf = b''
    while len(buf) < size:
        part = sock.recv(size - len(buf))
        if not part:
            raise ConnectionError("Conexión perdida")
        buf += part
    return buf

sock = socket.socket()
sock.connect((IP_DEL_PICO_W, 12345))

try:
    while True:
        marker = recv_exact(sock, 2)
        if marker != b'FR':
            print("❌ Encabezado incorrecto, resync...")
            continue

        size_bytes = recv_exact(sock, 2)
        frame_size = int.from_bytes(size_bytes, 'big')
        buf = recv_exact(sock, frame_size)

        frame = rgb565_to_bgr888(buf)
        frame = cv2.resize(frame, (WIDTH * 4, HEIGHT * 4), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("OV7670 Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    sock.close()
    cv2.destroyAllWindows()
