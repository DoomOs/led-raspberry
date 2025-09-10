from flask import Flask, render_template, redirect, url_for
import paho.mqtt.client as mqtt
import ssl
import threading
import json
import os

app = Flask(__name__)

# Configuración MQTT HiveMQ
MQTT_BROKER = "b185a6463a5644f4bce2ebf37879b755.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC_LED = "raspberry/led/control"
MQTT_TOPIC_DATA = "raspberry/max30102"
MQTT_USERNAME = "useer"       # <- tus credenciales HiveMQ
MQTT_PASSWORD = "User1234"    # <- tus credenciales HiveMQ

# Estado LED (para toggle) y datos del sensor
led_state = False
sensor_data = {"heart_rate": "N/A", "timestamp": None, "led_state": None}

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Conectado a MQTT desde Flask")
        client.subscribe(MQTT_TOPIC_DATA)
    else:
        print(f"❌ Error conectando MQTT Flask: {rc}")

def on_message(client, userdata, msg):
    global sensor_data
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        sensor_data = data  # guardar última lectura
        print("📩 Datos recibidos:", sensor_data)
    except Exception as e:
        print("❌ Error procesando mensaje:", e)

def mqtt_subscribe():
    """Hilo en segundo plano para escuchar datos del sensor"""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    client.tls_set_context(context)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ Error en hilo MQTT subscribe: {e}")

# Cliente MQTT global para publicar
mqtt_pub_client = None

def init_mqtt_publisher():
    """Inicializar cliente MQTT para publicar"""
    global mqtt_pub_client
    try:
        mqtt_pub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqtt_pub_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        mqtt_pub_client.tls_set_context(context)
        mqtt_pub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_pub_client.loop_start()   # 🔑 importante
        print("✅ Cliente MQTT publisher inicializado")
    except Exception as e:
        print(f"❌ Error inicializando MQTT publisher: {e}")

def publish_mqtt(message):
    """Publicar mensaje MQTT para el LED"""
    if mqtt_pub_client:
        try:
            result = mqtt_pub_client.publish(MQTT_TOPIC_LED, message)
            print(f"📤 Mensaje publicado: {message} (rc: {result.rc})")
        except Exception as e:
            print(f"❌ Error publicando mensaje: {e}")
    else:
        print("❌ Cliente MQTT publisher no inicializado")

@app.route("/")
def index():
    return render_template("index.html", led_state=led_state, sensor_data=sensor_data)

@app.route("/toggle")
def toggle_led():
    global led_state
    led_state = not led_state
    message = "on" if led_state else "off"
    publish_mqtt(message)
    return redirect(url_for("index"))

# Inicializar MQTT publisher
init_mqtt_publisher()

# Hilo para MQTT subscriber
mqtt_thread = threading.Thread(target=mqtt_subscribe)
mqtt_thread.daemon = True
mqtt_thread.start()

if __name__ == "__main__":
    # Configuración para Render.com
    port = int(os.environ.get("PORT", 5000))  # Render define PORT
    app.run(host="0.0.0.0", port=port, debug=False)