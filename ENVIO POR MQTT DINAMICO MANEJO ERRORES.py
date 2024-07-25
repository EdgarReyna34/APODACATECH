#%%%%%%%%%%%%%%%%%%%GATEWAY QUE ENVIO DINAMICO A UBIDOTS PROTOCOLO MQTT%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#%%%%%%%%%%%%%%%%%%%%%%%%%%-----Declaracion de bibliotecas------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
from __future__ import print_function
import serial.tools.list_ports
import serial
import paho.mqtt.client as mqttClient
import time
import json
import random
import binascii
import time

#%%%%%%%%%%%%%%%%%%%%%%%%%%---------------Global variables-----------------------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
connected = False  # Stores the connection status
BROKER_ENDPOINT = "industrial.api.ubidots.com"
PORT = 1883
MQTT_USERNAME = "BBFF-9KgO8GzbaRne04jStWGrBXNcYrETCA"  # Put here your TOKEN
MQTT_PASSWORD = "abc"
TOPIC = "/v1.6/devices/"
DEVICE_LABEL = "gateway-pi"
VARIABLE_LABEL_1 = "id-nodo1"
VARIABLE_LABEL_2 = "bat-nodo1"
VARIABLE_LABEL_3 = "motor1-inference"
VARIABLE_LABEL_4 = "motor1-temperature"
VARIABLE_LABEL_5 = "id-nodo2"
VARIABLE_LABEL_6 = "bat-nodo2"
VARIABLE_LABEL_7 = "motor2-inference"
VARIABLE_LABEL_8 = "motor2-temperature"
VARIABLE_LABEL_9 = "id-nodo3"
VARIABLE_LABEL_10 = "bat-nodo3"
VARIABLE_LABEL_11 = "motor3-inference"
VARIABLE_LABEL_12 = "motor3-temperature"

ser = None
list_data = []

battery = ""
idnode = ""
infer = ""
temp = ""
# Define un tamaño máximo para el buffer
MAX_BUFFER_SIZE = 3  # Puedes ajustar esto según tus necesidades
# Define un intervalo de tiempo (en segundos) para el envío
TIME_INTERVAL = 15  # Puedes ajustar esto según tus necesidades

buffer_data = []  # Almacena los paquetes de datos

#La creación del cliente MQTT se realiza una vez en el código para garantizar que haya una única instancia del cliente MQTT
#que se puede usar en diferentes partes del programa.
mqtt_client = mqttClient.Client()

#%%%%%%%%%%%%%%%%%%%%%%%%%%-----------Variables comunicion UART-----------------------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def get_ports():
    ports = serial.tools.list_ports.comports()
    return ports
#Busca el puerto llamado USB-SERIAL CH340
def findUSB(portsFound):
    commPort = None
    for port in portsFound:
        strPort = str(port)
        if 'USB' in strPort:
            splitPort = strPort.split(' ')
            commPort = splitPort[0]
    return commPort
#%%%%%%%%%%%%%%%%%%%%%%%%%------COMUNICACION Nodo Maestro CAN y python via UART -------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def check_serial_connection():
    global ser, list_data

    if ser is None or not ser.is_open:
        reconnect_serial()  # Intenta reconectar si la conexión está perdida
        list_data = []  # Reinicia list_data si se intenta reconectar

def VectoresUART():
    print("ENTRAMOS A VECTORES UART")
    global list_data, ser

    check_serial_connection()  # Verifica y restablece la conexión USB si es necesario

    if ser is None:
        return

    try:
        #ser.flushInput()
        # Configura un temporizador de espera de 1 segundo
        ser.timeout = 1.0
        ser_bytes = ser.readline()
        decoded_values = ser_bytes.decode("utf-8")
        list_data = decoded_values.split(':')
        print("Salimos de vectores UART")

    except serial.SerialException:
        print("Error al leer datos del puerto serial. Reconectando...")
        reconnect_serial()
        list_data = []  # Reinicia list_data si se intenta reconectar


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def VariablesData() :
    print("ENTRAMOS A VARIABLES DATA")
    global list_data   
    global battery
    global idnode
    global infer
    global temp
    
    if len(list_data) != 7:  # Asumiendo que esperas 6 elementos en list_data
        print("Datos UART incompletos o de mas.")
        return

# save data in dif variables list
# list data 0 lleva el valor AA
    idnode = list_data[1]
    battery = list_data[2]
    infer = list_data[3]
    temp = list_data[4]
    received_crc = int(list_data[5], 16)  # Convierte el valor de CRC hexadecimal a entero 
    
    # Verifica la integridad de los datos
    data_packet = f'AA:{idnode}:{battery}:{infer}:{temp}:'
    calculated_crc = binascii.crc32(data_packet.encode()) & 0xFFFFFFFF

    if received_crc == calculated_crc:
        print("Datos válidos recibidos por UART.")
        # Después de procesar los datos correctamente enviamos bit en alto de ack
        print("enviamos bit en alto de ack")
        ack_message = "1"  # Define tu mensaje de ACK
        ser.write(ack_message.encode())  # Envía el ACK de vuelta al dispositivo emisor
        # Puedes procesar los datos aquí
        data_packet = (idnode, battery, infer, temp)  # Almacena los datos en un paquete
        buffer_data.append(data_packet)
    else:
        print("Advertencia: los datos recibidos por UART son inválidos.")
    print(list_data)

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#%%%%%%%%%%%%%%%%%%%%%%%"""Envía todos los datos almacenados en buffer_data a MQTT"""
def send_data_to_mqtt():
    global buffer_data

    if not buffer_data:
        print("INFO No hay datos para enviar.")
        return

    mqtt_data = {}  # Crea un diccionario para almacenar los datos que se enviarán

    for data_packet in buffer_data:
        sensor_id = data_packet[0]

        if sensor_id in sensor_mappings:
            sensor_variables = sensor_mappings[sensor_id]
            for i, variable_label in enumerate(sensor_variables):
                mqtt_data[variable_label] = data_packet[i]
        else:
            print(f"[INFO] Sensor ID {sensor_id} no se encuentra en el diccionario. Los datos no se enviarán.")

    if mqtt_data:
        payload = json.dumps(mqtt_data)
        topic = "{}{}".format(TOPIC, DEVICE_LABEL)

        if not connected:
            connect(mqtt_client, MQTT_USERNAME, MQTT_PASSWORD, BROKER_ENDPOINT, PORT)

        print("[INFO] Intentando publicar payload:")
        print(payload)
        publish(mqtt_client, topic, payload)

    buffer_data.clear()  # Limpia completamente el buffer después de enviar


# Mapeo de sensores a etiquetas de variables
sensor_mappings = {
    "1": [VARIABLE_LABEL_1, VARIABLE_LABEL_2, VARIABLE_LABEL_3, VARIABLE_LABEL_4],
    "2": [VARIABLE_LABEL_5, VARIABLE_LABEL_6, VARIABLE_LABEL_7, VARIABLE_LABEL_8],
    "3": [VARIABLE_LABEL_9, VARIABLE_LABEL_10, VARIABLE_LABEL_11, VARIABLE_LABEL_12],
# Agrega más sensores y sus etiquetas de variables aquí
}

#%%%%%%%%%%%%%%%%%%%%%%%%%%%------all MQTT----------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#Functions to process incoming and outgoing streaming

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[INFO] Connected to broker")
        global connected  # Use global variable
        connected = True  # Signal connection

    else:
        print("[INFO] Error, connection failed")


def on_publish(client, userdata, result):
    print("[INFO] Published!")


def connect(mqtt_client, mqtt_username, mqtt_password, broker_endpoint, port):
    global connected

    if not connected:
        mqtt_client.username_pw_set(mqtt_username, password=mqtt_password)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_publish = on_publish
        mqtt_client.connect(broker_endpoint, port=port)
        mqtt_client.loop_start()

        attempts = 0

        while not connected and attempts < 5:  # Waits for connection
            print("[INFO] Attempting to connect...")
            time.sleep(1)
            attempts += 1

    if not connected:
        print("[ERROR] Could not connect to broker")
        return False

    return True


def publish(mqtt_client, topic, payload):
    try:
        mqtt_client.publish(topic, payload)
    except Exception as e:
        print("[ERROR] There was an error, details: \n{}".format(e))



#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%------buscando puerto serial de forma automatica -------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
foundPorts = get_ports()
connectPort = findUSB(foundPorts)

if connectPort:  # Esta condición será False si connectPort es None.
    ser = serial.Serial(connectPort, baudrate=115200)
    print('Connected to ' + connectPort)
else:
    print('USB uart Connection Issue!')
    #exit()  # Esto terminará el programa. Si no quieres terminarlo, puedes manejarlo de otra manera.

def reconnect_serial():
    global ser
    if ser:
        try:
            ser.close()
        except serial.SerialException:
            pass

    ser = None
    print("Conexión USB perdida. Intentando reconectar...")
    foundPorts = get_ports()
    connectPort = findUSB(foundPorts)
    
    if connectPort:
        ser = serial.Serial(connectPort, baudrate=115200)
        print('Conectado a ' + connectPort)
    else:
        print('¡Problema de conexión USB!')

            


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%----Porgrama principal---%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

last_send_time = time.time()

while True:
    print('inicio')
    try:
        VectoresUART()
        
        VariablesData()

        current_time = time.time()
        
        # Si se ha alcanzado el tamaño máximo del buffer o ha transcurrido el intervalo de tiempo y tenemos datos en bffer data, envía los datos
        if len(buffer_data) >= MAX_BUFFER_SIZE or ((current_time - last_send_time) >= TIME_INTERVAL and buffer_data):
            send_data_to_mqtt()
            last_send_time = current_time

    except serial.SerialException as e:
        print("ERROR")
        pass  # Captura y omite los errores de comunicación
    # Agregar un tiempo de espera de 1 segundo
    time.sleep(1)