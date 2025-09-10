from flask import Flask, render_template, redirect, url_for
import paho.mqtt.client as mqtt
import ssl
import threading
import json

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

def on_connect(client, userdata, flags, rc):
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
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    client.tls_set_context(context)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# Hilo para MQTT
mqtt_thread = threading.Thread(target=mqtt_subscribe)
mqtt_thread.daemon = True
mqtt_thread.start()

# Cliente MQTT global en Flask
mqtt_pub_client = mqtt.Client()
mqtt_pub_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
mqtt_pub_client.tls_set_context(context)
mqtt_pub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_pub_client.loop_start()   # 🔑 importante

def publish_mqtt(message):
    mqtt_pub_client.publish(MQTT_TOPIC_LED, message)
    print(f"📤 Mensaje publicado: {message}")

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

if __name__ == "__main__":
    app.run(debug=True)