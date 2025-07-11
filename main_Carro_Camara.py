# camara_control_uart.py  –– MicroPython 1.22+  (Pico W)

import gc, time, uasyncio as aio, network, socket
from machine import Pin, PWM, UART, I2C
from ov7670_wrapper import *

# ───────────────────────── LED de estado ─────────────────────────
led = Pin("LED", Pin.OUT)                # LED interno

def led_blink(times=3, period_ms=150):
    """Destella el LED 'times' veces."""
    for _ in range(times):
        led.on();  time.sleep_ms(period_ms)
        led.off(); time.sleep_ms(period_ms)

# ───────────────────────── Config Wi‑Fi ─────────────────────────
SSID, PASSWORD = "Carlos's Galaxy A32 5G", "enyo4261"
IP, MASK      = "192.168.197.208", "255.255.255.0"
GW, DNS       = "192.168.1.39",   "8.8.8.8"

def wifi_up():
    """Conecta (o reconecta) y NO retorna hasta que haya Wi‑Fi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.ifconfig((IP, MASK, GW, DNS))

    if wlan.isconnected():
        return

    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        led.toggle()               # parpadeo 1 Hz mientras busca
        time.sleep(1)
        if wlan.status() in (
            network.STAT_IDLE, network.STAT_NO_AP_FOUND,
            network.STAT_CONNECT_FAIL, network.STAT_WRONG_PASSWORD
        ):
            wlan.disconnect()
            wlan.connect(SSID, PASSWORD)   # reintento

    led.off()
    print("✅ Wi‑Fi:", wlan.ifconfig())
    led_blink(2, 100)              # confirmación doble destello

# ───────────────────────── UART hacia receptor ──────────────────
uart = UART(0, 115_200, tx=Pin(12), rx=Pin(13))

def tx_uart(msg: str):
    uart.write(msg + "\n")         # cada línea termina en \n
    print("UART>", msg)

# ───────────────────────── Cámara OV7670 ────────────────────────
MCLK=9; PCLK=8; D0=0; VSYNC=11; HREF=10; RST=19; SHDN=18; SDA=20; SCL=21
PWM(Pin(MCLK)).freq(40_000_000)    # 40 MHz para MCLK

i2c  = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=400_000)
cam  = OV7670Wrapper(i2c, MCLK, PCLK, D0, VSYNC, HREF, RST, SHDN)
cam.wrapper_configure_rgb()
cam.wrapper_configure_base()
W, H = cam.wrapper_configure_size(OV7670_WRAPPER_SIZE_DIV8)
i2c.writeto_mem(0x21, 0x13, b'\xE7')   # auto‑exposición / balance blanco
cam.wrapper_configure_test_pattern(OV7670_WRAPPER_TEST_PATTERN_NONE)
frame = bytearray(W * H * 2)           # buffer RGB565

# ──────────────────── Página web de control ─────────────────────
WEB_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>Control Carro y Brazo - Pico W</title>
  <style>
    body { background: #111; color: #eee; text-align: center; }
    button { width: 60px; height: 60px; margin: 5px; }
    input[type=range] { width: 200px; }
  </style>
</head>
<body>
  <h2>Control del Carro</h2>
  <div>
    <button onclick="sendCommand('W')">W</button><br>
    <button onclick="sendCommand('A')">A</button>
    <button onclick="sendCommand('S')">S</button>
    <button onclick="sendCommand('D')">D</button>
  </div>

  <h2>Control Brazo</h2>
  <div>
    Base: <input id="base" type="range" min="0" max="180" value="90"><br>
    Hombro: <input id="hombro" type="range" min="0" max="90" value="45"><br>
    Codo: <input id="codo" type="range" min="0" max="180" value="90"><br>
    <button onclick="sendArm()">Enviar</button>
  </div>

  <script>
    let base = 90;    // ángulo inicial base
    let hombro = 45;  // ángulo inicial hombro
    let codo = 90;    // ángulo inicial codo

    document.addEventListener('keydown', function(e) {
      let key = e.key;
      console.log('Tecla:', key);

      // Control carro: WASD
      if (key === 'w' || key === 'W') sendCommand('W');
      else if (key === 'a' || key === 'A') sendCommand('A');
      else if (key === 's' || key === 'S') sendCommand('S');
      else if (key === 'd' || key === 'D') sendCommand('D');

      // Brazo: base (4,6), hombro (8,5), codo (7,9)
      else if (key === '4') {
        base = Math.max(0, base - 5);
        document.getElementById('base').value = base;
        sendArm();
      }
      else if (key === '6') {
        base = Math.min(180, base + 5);
        document.getElementById('base').value = base;
        sendArm();
      }
      else if (key === '8') {
        hombro = Math.min(90, hombro + 5);
        document.getElementById('hombro').value = hombro;
        sendArm();
      }
      else if (key === '5') {
        hombro = Math.max(0, hombro - 5);
        document.getElementById('hombro').value = hombro;
        sendArm();
      }
      else if (key === '7') {
        codo = Math.max(0, codo - 5);
        document.getElementById('codo').value = codo;
        sendArm();
      }
      else if (key === '9') {
        codo = Math.min(180, codo + 5);
        document.getElementById('codo').value = codo;
        sendArm();
      }
    });

    function sendCommand(cmd) {
      fetch(`/move?cmd=${cmd}`);
    }

    function sendArm() {
      fetch(`/arm?b=${base}&h=${hombro}&c=${codo}`);
    }
  </script>

</body>
</html>
"""

# ─────────────────────── Servidor HTTP ─────────────────────────
async def http_client(reader, writer):
    req_line = (await reader.readline()).decode()
    if not req_line:
        return
    path = req_line.split(' ')[1]
    while await reader.readline() != b'\r\n':   # descarta cabeceras
        pass

    if path.startswith("/move"):
        cmd = path.split("cmd=")[-1]
        tx_uart(f"MOVE:{cmd}")
        body = b"OK"

    elif path.startswith("/arm"):
        try:
            qs = path.split('?', 1)[1]
            p  = {kv.split('=')[0]: kv.split('=')[1] for kv in qs.split('&')}
            tx_uart(f"ARM:{p['b']},{p['h']},{p['c']}")
            body = b"OK"
        except:
            body = b"ERR"

    else:
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n")
        writer.write(WEB_PAGE)
        await writer.drain(); await writer.aclose(); return

    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type:text/plain\r\n\r\n")
    writer.write(body)
    await writer.drain(); await writer.aclose()

# ─────────────────── Streaming de vídeo ────────────────────────
async def video_stream(reader, writer):
    print("📺 stream conectado")
    try:
        while True:
            cam.capture(frame)
            size = len(frame)
            writer.write(b'FR'+size.to_bytes(2,'big')+frame)
            await writer.drain()
            await aio.sleep_ms(20)         # ~50 fps máx
    except:
        print("❌ stream cerrado")
    await writer.aclose()

# ───────────────── Vigilante de Wi‑Fi ──────────────────────────
async def wifi_watchdog():
    while True:
        if not network.WLAN(network.STA_IF).isconnected():
            print("❌ Wi‑Fi perdida… reconectando")
            wifi_up()                       # bloquea hasta reconectar
        await aio.sleep(10)

# ───────────────────────── Programa principal ──────────────────
async def main():
    led.off()
    wifi_up()                               # se queda en bucle hasta éxito
    aio.create_task(wifi_watchdog())        # supervisa cortes futuros

    await aio.start_server(http_client, "0.0.0.0", 80)
    print("🌐 HTTP listo en http://%s" % IP)

    await aio.start_server(video_stream, "0.0.0.0", 12345)
    print("📡 Vídeo en tcp://%s:12345" % IP)

    led.on()                                # LED fijo = listo para usar
    while True:
        await aio.sleep(3600)

aio.run(main())