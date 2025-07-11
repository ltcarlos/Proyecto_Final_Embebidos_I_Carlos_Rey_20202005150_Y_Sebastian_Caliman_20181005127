# Proyecto_Final_Embebidos_I_Carlos_Rey_20202005150_Y_Sebastian_Caliman_20181005127
Códigos del Carro (Código Rasberry Controla Motores y Rasberry Envía Video y Recibe Instrucciones) y Código del Cliente Para Visualizar Video

La Rasberry conectada a la camara ofrece 2 servidores web:
  uno para transmitir imagen por bytes
  otro ofrecer un menú interactivo mediante el cual recibe órdenes  y luego las pasa por UART al carro que controla los motores.

La Rasberry conectada a los motores recibe por UART las instrucciones de movimiento de motores y posiciones de brazo, y ejecuta las órdenes.

Para visualizar es necesario correr un programa de python que se conecta al servidor de la rasberry y recibe los datos de la cámara para convertirlos y mostrarlos en pantalla.
