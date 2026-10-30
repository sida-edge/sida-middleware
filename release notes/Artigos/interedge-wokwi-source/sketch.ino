/**
 * Module       : hdei : InterEdge 
 * Name         : sketch.ino
 * Description  : This is the main file where we have the setup function. 
 * To accurately calculate the ROM, RAM usage, and response latency, we extracted code 
 * from here and implemented each functionality into separate projects. This approach allowed 
 * for precise measurements of ROM and RAM usage, as well as response latency 
 * for each individual functionality. 
 * See the description of the class on top of the class
 * declaration and the description of the methods on top of
 * each method
 * Project      : InterEdge - Hierarchical Decentralized Edge Interoperability
 *
 * @author : Tanzima Azad <tanzima.azad@griffithuni.edu.au>, GU
 *         Creation     : Version: 1.0  Date: May 03, 2024
 *         Language     : C++
 *         copyright    : (c) 2024 Griffith University
 *         ----------------------------------------------------------------------------
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <Arduino.h>
#include "hdei.h"

const char* ssid = "Wokwi-GUEST";  // SSID to connect to Wi-Fi
const char* password = ""; // Password to connect to Wi-Fi

unsigned long starttime; // take note of start time
unsigned long endtime; // take note of end time
unsigned long duration; // duration of the event in ms


/**
 * The main setup method for the ESP32 controller invokes all the functions from the 
 * other .ino files to execute each functionality. As the simulator supports only one 
 * controller per project, we maintain a single setup function for each project. 
 * Running our EspSolution does not require any changes or additional memberships. 
 * However, to run our UnoSolution, the ESP32 controller must be replaced with an Uno controller. 
 * For the other three open standards, their codes need to be deployed on a localhost server. 
 * Additionally, to execute the code on the simulator and interact with the localhost, 
 * a membership from Wokwi is necessary.
 *
 * For simplicity, we have placed the code in the setup function for now. 
 * In a real-life scenario, the code would be placed in the loop method to ensure continuous execution.
 */
void setup() {
  Serial.begin(115200);
  
  // *** Our ESP32 Solution ***
  starttime = millis(); // take note of start time

  // This method is called from the OurESP32Solution.ino
  // file. It uses our solution to read temperature from 
  // the temperature sensor using the ESP32 controller.
  Esp32ControllerProgram();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("Our Solution (ESP32) Duration(ms): ");
  Serial.println(duration);

  // *** Our Arduino Uno R3 Solution ***
  starttime = millis(); // take note of start time

  // This method is called from the OurUnoSolution.ino
  // file. It uses our solution to read temperature from 
  // the temperature sensor using Arduino Uno controller.
  UnoControllerProgram();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("Our Solution (Uno) Duration(ms): ");
  Serial.println(duration);

  // *** SOS INSERT OBSERVATION ***
  starttime = millis(); // take note of start time

  // This method is called from the SOSInsertObservation.ino
  // file. It reads the temperature data and uses the code in the localhost
  // to store the temperature data in the cloud using the ESP32 controller.
  sosInsertObservation();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("SOS Insert Observation Duration(ms): ");
  Serial.println(duration);


  // *** SOS GET OBSERVATION ***
  starttime = millis(); // take note of start time

  // This method is called from the SOSGetObservation.ino
  // file. It uses the code in the localhost to read the temperature data 
  // previously stored from the cloud using the ESP32 controller.
  sosGetObservation();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("SOS Get Observation Duration(ms): ");
  Serial.println(duration);


  // *** Sensor Things Create OBSERVATION ***
  starttime = millis(); // take note of start time

  // This method is called from the SensorThingsCreateObservation.ino
  // file. It reads the temperature data and uses the code in the localhost
  // to store the temperature data in the cloud using the ESP32 controller.
  sensorThingsCreateObservation();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("Sensor Things Create Observation Duration(ms): ");
  Serial.println(duration);

  // *** Sensor Things Read OBSERVATION ***
  starttime = millis(); // take note of start time

  // This method is called from the SensorThingsObservation.ino
  // file. It uses the code in the localhost to read the temperature data 
  // previously stored from the cloud using the ESP32 controller.
  sensorthingsReadObservation();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("Sensor Things Read Observation Duration(ms): ");
  Serial.println(duration);


  // *** EdgeX Foundry Send Data ***
  starttime = millis(); // take note of start time

  // This method is called from the EdgexFoundrySendData.ino
  // file. It reads the temperature data and uses the code in the localhost
  // to store the temperature data in the cloud using the ESP32 controller.
  edgeXFoundrySendData();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("EdgeX Foundry Send Data Duration(ms): ");
  Serial.println(duration);

   // *** EdgeX Foundry Read Data ***
  starttime = millis(); // take note of start time

  // This method is called from the EdgexFoundryReadData.ino
  // file. It uses the code in the localhost to read the temperature data 
  // previously stored from the cloud using the ESP32 controller.
  edgeXFoundryReadData();

  endtime = millis(); // take note of end time
  duration = endtime - starttime; // duration of the event in ms
  Serial.print("EdgeX Foundry Read Data Duration(ms): ");
  Serial.println(duration);  
}

void loop() {
  
}