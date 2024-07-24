
/*MASTER NODE THAT RECEIVES INFORMATION FROM THE TINYML SENSOR VIA ESPNOW PROTOCOL.*/

#include <esp_now.h>
#include <WiFi.h>
#include <CRC32.h>

unsigned long uartdelay = 5000;  
unsigned long time_now1 = 4000000000, time_now2 = 4000000000, time_now3 = 4000000000, time_serial = 0;
int id1, batNodo1, id2, batNodo2, id3, batNodo3;
int idx = 1, batnodo = 88;
double inference = 3, temperature = 4;
double sensNodo1=1, sensNodo2=3, sensNodo3=4, sensNododos3=5, sensNododos2=3, sensNododos1=2; 
boolean NuevoDatN1 = false, NuevoDatN2 = false, NuevoDatN3 = false, DatoNuevo = false;
boolean inicioUART = true;
int temperaturas = 70;
int inferencias = 5; 
int bateriap = 100;
int identificador = 1;
// Structure example to receive data
// Must match the sender structure
typedef struct struct_message {
  int id;
  int bat;
  int sens;
  int sens2;
}struct_message;

// Create a struct_message called myData
struct_message myData;

// Create a structure to hold the readings from each board
struct_message board1;
struct_message board2;
struct_message board3;
struct_message board4;
struct_message board5;
struct_message board6;
struct_message board7;


// Create an array with all the structures
struct_message boardsStruct[7] = {board1, board2, board3, board4, board5, board6, board7};

// callback function that will be executed when data is received
void OnDataRecv(const uint8_t * mac_addr, const uint8_t *incomingData, int len) {
  char macStr[18];
 // Serial.print("Packet received from: ");
  snprintf(macStr, sizeof(macStr), "%02x:%02x:%02x:%02x:%02x:%02x",
           mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
 // Serial.println(macStr);
  memcpy(&myData, incomingData, sizeof(myData));
 // Serial.printf("Board ID %u: %u bytes\n", myData.id, len);
// Update the structures with the new incoming data
  boardsStruct[myData.id-1].id = myData.id;
  boardsStruct[myData.id-1].bat = myData.bat;
  boardsStruct[myData.id-1].sens = myData.sens;
  boardsStruct[myData.id-1].sens2 = myData.sens2;
  DatoNuevo = true;
}

uint32_t calculateCRC32(const uint8_t* data, size_t length) {
  CRC32 crc;
  crc.update(data, length);
  return crc.finalize();
}

 
void setup() {
  //Initialize Serial Monitor
  Serial.begin(115200);
  //Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  //Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
  //  Serial.println("Error initializing ESP-NOW");
    return;
  }
  // Once ESPNow is successfully Init, we will register for recv CB to
  // get recv packer info
  esp_now_register_recv_cb(OnDataRecv);
  //Every time we start, it asks the other sensors for the current status of the doors.
  //****************************************************************************************
}

void loop() {
  if ((unsigned long)(millis() - time_serial) > uartdelay) {
    // Calculate the CRC32 of your data
    uint8_t dataBuffer[50]; // Ajusta el tamaño del búfer según tus necesidades
    int dataLength = snprintf((char*)dataBuffer, sizeof(dataBuffer), "AA:%d:%d:%d:%d:", myData.id, myData.bat, myData.sens, myData.sens2);
    uint32_t calculatedCRC = calculateCRC32(dataBuffer, dataLength);

    // Print the data and CRC in hexadecimal format
    Serial.print("AA:");
    Serial.print(myData.id);
    Serial.print(":");
    Serial.print(myData.bat);
    Serial.print(":");
    Serial.print(myData.sens);
    Serial.print(":");
    Serial.print(myData.sens2);
    Serial.print(":");
    Serial.print(calculatedCRC, HEX); // Send the CRC value in hexadecimal format
    Serial.println(":");
    time_serial = millis();
    DatoNuevo = false;
  }
}


