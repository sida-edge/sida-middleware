/**
 * Module       : hdei : InterEdge 
 * Name         : EdgexFoundryReadData.ino
 * Description  : In this file we have called the localhost for 
 * EdgeX Foundry Read Data function to 
 * retrive the previously store temperature data from the cloud.
 * The edgeXFoundryReadData() method calls the Read Data function
 * of the EdgeX Foundry.
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
const String EFRDurl = "http://host.wokwi.internal:48080/api/v1/event/device/Temp_sensor_data/1";

int EFRDhttpResponseCode; // response code

/**
* The edgeXFoundryReadData method initiates a connection to a WiFi network and 
* sends a GET request to an EdgeX Foundry server to retrieve data. 
* It constructs and sends the HTTP GET request, retrieves the server's response, 
* and prints the HTTP response code and payload to the serial monitor. 
* This method does continuous data retrieval by connecting to the WiFi network and 
* making repeated requests to record response latency for our experiment.
*/
void edgeXFoundryReadData() {

  WiFi.begin(ssid, password); // begin Wi-Fi with ssid and password

  Serial.print("Connecting to WiFi");
  /*while (WiFi.status() != WL_CONNECTED) {
    delay(1500);
    Serial.print(".");
  }*/

  if(WiFi.status() == WL_CONNECTED) { // check if connected to Wi-Fi

    HTTPClient EFRDhttp;
    EFRDhttp.begin(EFRDurl);
    
    EFRDhttpResponseCode = EFRDhttp.GET(); // HTTP GET request
    if (EFRDhttpResponseCode > 0) { // success response
      Serial.print("HTTP ");
      Serial.println(EFRDhttpResponseCode);
      String EFRDpayload = EFRDhttp.getString();
      Serial.println();
      Serial.println(EFRDpayload);
    }
    else { // error response
      Serial.print("Error code: ");
      Serial.println(EFRDhttpResponseCode);
      Serial.println(":-(");
    }
  } 
}