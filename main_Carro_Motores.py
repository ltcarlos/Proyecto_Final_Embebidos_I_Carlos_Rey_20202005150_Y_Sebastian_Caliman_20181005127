# receptor_uart_pico.py ─ MicroPython 1.22+ ─
from machine import UART, Pin
from motor_controller import MotorController
from robot_arm_controller import BrazoRobotico

# ── UART entre Picos ──
# Pico‑A GP16  ───►  Pico‑B GP17   (RX)
UART_ID   = 0
BAUDRATE  = 115_200
TX_PIN_NO = 0      # no lo usamos, pero hay que declararlo
RX_PIN_NO = 1

uart = UART(
    UART_ID,
    baudrate      = BAUDRATE,
    tx            = Pin(TX_PIN_NO),
    rx            = Pin(RX_PIN_NO),
    timeout       = 50,     # ms que espera para un byte nuevo
    timeout_char  = 5       # ms que espera entre caracteres
)

mc    = MotorController()
brazo = BrazoRobotico()

def ejecutar_linea(linea: str):
    if linea.startswith("MOVE:"):
        cmd = linea[5:]
        if   cmd == "W": mc.mover_adelante(5)
        elif cmd == "S": mc.mover_atras(5)
        elif cmd == "A": mc.girar_izquierda(30)
        elif cmd == "D": mc.girar_derecha(30)
        else: print("⚠️ MOVE?", linea)

    elif linea.startswith("ARM:"):
        try:
            b, h, c = map(float, linea[4:].split(","))
            brazo.mover_brazo([b, h, c], tiempo_segundos=0.2)
        except ValueError:
            print("⚠️ ARM mal formado:", linea)

    else:
        print("⚠️ Desconocido:", linea)

print(f"✅ UART{UART_ID} @ {BAUDRATE} bps (RX=GP{RX_PIN_NO}) – esperando…")

while True:
    raw = uart.readline()          # bloquea hasta '\n' o timeout
    if not raw:                    # timeout vacío → sigue
        continue
    try:
        ejecutar_linea(raw.decode().strip())
    except Exception as e:
        print("⚠️ Error:", e, raw)

