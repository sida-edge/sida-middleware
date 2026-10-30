/**
 * Module       : hdei : InterEdge 
 * Name         : EdgexFoundrySendData.ino
 * Description  : In this file we have called the localhost for 
 * Edgex Foundry Send Data function to store the temperature data in the cloud.
 * We read the temperature data from the temperature sensor using the ESP32 controller.
 * The ReadSensorData() method reads the temperature from the sensor. This method is used 
 * from the SOSInsertObservation.ino.
 * The edgeXFoundrySendData() method calls the Send Data function
 * of the Edgex Foundry.
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

 /** 
 * This variable specifies the URL for the local 
 * EdgeX Foundry web application service. 
 * Accessing localhost via Wokwi requires a membership, and 
 * the URL must use "host.wokwi.internal" instead of "localhost".
 */
const String EFSDurl = "http://host.wokwi.internal:49986/api/v1/resource/Temp_sensor_data/temperature";

String EFSDStringData = "11"; // variable to replace data for multiple sensor data insert

int EFSDhttpResponseCode; // response code
String EFSDpayload; // response string from the server

/**
* The edgeXFoundrySendData method initiates a connection to a WiFi network 
* and sends a POST request to an EdgeX Foundry server to transmit data. 
* It constructs an HTTP POST request with sensor data, sends the request 
* to the server, and retrieves the server's response. 
* The method ensures successful transmission by repeating the process within a loop
* to record response latency for our experiment.
*/
void edgeXFoundrySendData() {
  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password

  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
    delay(1500);
    Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) { // check if connected to Wi-Fi

    HTTPClient EFSDhttp;
    EFSDhttp.begin(EFSDurl);
    
    for(int i = 0; i < 1; i++){    
      // Send HTTP POST request
    
      EFSDStringData = String(ReadSensorData());
      EFSDhttpResponseCode = EFSDhttp.POST(EFSDStringData); // http post
      if (EFSDhttpResponseCode > 0) { // success response
        Serial.print("HTTP ");
        Serial.println(EFSDhttpResponseCode);
        EFSDpayload = EFSDhttp.getString();
        Serial.println();
        Serial.println(EFSDpayload);
      }
      else { // error response
        Serial.print("Error code: ");
        Serial.println(EFSDhttpResponseCode);
        Serial.println(":-(");
      }
    }
  }
}